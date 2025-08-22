// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "./IdentityLib.sol";

interface IStakeManager {
    function slash(
        address offender,
        address employer,
        uint256 amount,
        uint256 burnPctOverride,
        uint256 jobId
    ) external;
    function validatorStakes(address user) external view returns (uint256);
    function minStakeValidator() external view returns (uint256);
}

interface IReputationEngine {
    function onValidate(address user, bool success) external;
    function isBlacklisted(address user) external view returns (bool);
}

interface IJobRegistry {
    function validationComplete(uint256 jobId, bool result) external;
}

interface IValidationModule {
    function validate(uint256 jobId, bytes calldata data) external returns (bool);
    function validationResult(uint256 jobId) external view returns (bool);
    function getWinningValidators(uint256 jobId) external view returns (address[] memory);
}

contract ValidationModule is Ownable, IValidationModule {
    struct Vote {
        bytes32 commit;
        bool revealed;
        bool vote;
        uint64 commitTime;
        uint64 revealTime;
    }

    struct Round {
        uint64 commitEnd;
        uint64 revealEnd;
        address[] validators;
        bool tallied;
        bool result;
        mapping(address => Vote) votes;
    }

    uint256 public commitWindow;
    uint256 public revealWindow;
    uint256 public validatorsPerJob;
    uint256 public selectionSeed;
    uint256 public slashPercentage; // basis points

    bytes32 public clubRootNode;
    bytes32 public validatorMerkleRoot;

    mapping(address => bool) public additionalValidators;
    address[] public validatorPool;
    mapping(address => string) private validatorSubdomains;
    mapping(address => bytes32[]) private validatorProofs;

    IStakeManager public stakeManager;
    IReputationEngine public reputationEngine;
    IJobRegistry public jobRegistry;

    mapping(uint256 => Round) private rounds;

    event ValidatorSelected(uint256 indexed jobId, address indexed validator);
    event VoteCommitted(uint256 indexed jobId, address indexed validator);
    event VoteRevealed(uint256 indexed jobId, address indexed validator, bool vote);
    event Tallied(uint256 indexed jobId, bool result);
    event ParametersUpdated();
    event RootNodeUpdated(bytes32 newRootNode);
    event MerkleRootUpdated(bytes32 newMerkleRoot);

    constructor(address _stakeManager, address _reputation, address _jobRegistry) Ownable(msg.sender) {
        stakeManager = IStakeManager(_stakeManager);
        reputationEngine = IReputationEngine(_reputation);
        jobRegistry = IJobRegistry(_jobRegistry);
    }

    function validate(uint256 jobId, bytes calldata) external override returns (bool) {
        Round storage r = rounds[jobId];
        require(r.commitEnd == 0, "exists");
        r.commitEnd = uint64(block.timestamp + commitWindow);
        r.revealEnd = uint64(block.timestamp + commitWindow + revealWindow);
        _selectValidators(jobId);
        return true;
    }

    function _selectValidators(uint256 jobId) internal {
        Round storage r = rounds[jobId];
        uint256 count = validatorsPerJob;
        require(count > 0, "no validators");
        uint256 poolLen = validatorPool.length;
        address[] memory candidates = new address[](poolLen);
        uint256 candidateCount;

        for (uint256 i = 0; i < poolLen; i++) {
            address candidate = validatorPool[i];
            if (reputationEngine.isBlacklisted(candidate)) continue;
            bytes32[] storage storedProof = validatorProofs[candidate];
            bytes32[] memory proof = new bytes32[](storedProof.length);
            for (uint256 p = 0; p < storedProof.length; p++) {
                proof[p] = storedProof[p];
            }
            if (
                !IdentityLib.verify(
                    candidate,
                    validatorSubdomains[candidate],
                    proof,
                    clubRootNode,
                    validatorMerkleRoot
                )
            ) continue;
            if (stakeManager.validatorStakes(candidate) < stakeManager.minStakeValidator()) continue;
            candidates[candidateCount++] = candidate;
        }

        for (uint256 i = 0; i < candidateCount; i++) {
            for (uint256 j = i + 1; j < candidateCount; j++) {
                if (
                    stakeManager.validatorStakes(candidates[j]) >
                    stakeManager.validatorStakes(candidates[i])
                ) {
                    address tmp = candidates[i];
                    candidates[i] = candidates[j];
                    candidates[j] = tmp;
                }
            }
        }

        uint256 attempts;
        while (r.validators.length < count && attempts < candidateCount * 10) {
            address candidate = candidates[
                uint256(
                    keccak256(
                        abi.encode(blockhash(block.number - 1 - attempts), selectionSeed, jobId, attempts)
                    )
                ) % candidateCount
            ];
            attempts++;
            bool exists;
            for (uint256 i = 0; i < r.validators.length; i++) {
                if (r.validators[i] == candidate) {
                    exists = true;
                    break;
                }
            }
            if (exists) continue;
            r.validators.push(candidate);
            emit ValidatorSelected(jobId, candidate);
        }
        require(r.validators.length == count, "insufficient validators");
    }

    function commitVote(
        uint256 jobId,
        bytes32 commitHash,
        string calldata subdomain,
        bytes32[] calldata proof
    ) external {
        Round storage r = rounds[jobId];
        require(block.timestamp <= r.commitEnd, "commit over");
        require(isValidator(jobId, msg.sender), "not validator");
        require(
            additionalValidators[msg.sender] ||
                IdentityLib.verify(msg.sender, subdomain, proof, clubRootNode, validatorMerkleRoot),
            "identity"
        );
        require(!reputationEngine.isBlacklisted(msg.sender), "blacklisted");
        Vote storage v = r.votes[msg.sender];
        require(v.commit == bytes32(0), "committed");
        v.commit = commitHash;
        v.commitTime = uint64(block.timestamp);
        emit VoteCommitted(jobId, msg.sender);
    }

    function revealVote(
        uint256 jobId,
        bool vote,
        bytes32 salt,
        string calldata subdomain,
        bytes32[] calldata proof
    ) external {
        Round storage r = rounds[jobId];
        require(block.timestamp > r.commitEnd && block.timestamp <= r.revealEnd, "not reveal phase");
        require(
            additionalValidators[msg.sender] ||
                IdentityLib.verify(msg.sender, subdomain, proof, clubRootNode, validatorMerkleRoot),
            "identity"
        );
        require(!reputationEngine.isBlacklisted(msg.sender), "blacklisted");
        Vote storage v = r.votes[msg.sender];
        require(v.commit == keccak256(abi.encode(vote, salt)), "invalid reveal");
        require(!v.revealed, "revealed");
        v.revealed = true;
        v.vote = vote;
        v.revealTime = uint64(block.timestamp);
        emit VoteRevealed(jobId, msg.sender, vote);
    }

    function tally(uint256 jobId, uint256 reward) external {
        Round storage r = rounds[jobId];
        require(block.timestamp > r.revealEnd, "reveal not over");
        require(!r.tallied, "tallied");
        uint256 yes;
        uint256 no;
        uint256 slashAmount = (reward * slashPercentage) / 10_000;
        for (uint256 i = 0; i < r.validators.length; i++) {
            address validator = r.validators[i];
            Vote storage v = r.votes[validator];
            if (v.revealed) {
                if (v.vote) {
                    yes++;
                } else {
                    no++;
                }
            } else {
                stakeManager.slash(validator, address(0), slashAmount, 10_000, jobId);
                reputationEngine.onValidate(validator, false);
            }
        }
        r.result = yes >= no; // tie defaults to success
        r.tallied = true;
        for (uint256 i = 0; i < r.validators.length; i++) {
            address validator = r.validators[i];
            Vote storage v = r.votes[validator];
            if (v.revealed) {
                if (v.vote == r.result) {
                    reputationEngine.onValidate(validator, true);
                } else {
                    stakeManager.slash(validator, address(0), slashAmount, 10_000, jobId);
                    reputationEngine.onValidate(validator, false);
                }
            }
        }
        jobRegistry.validationComplete(jobId, r.result);
        emit Tallied(jobId, r.result);
    }

    function validationResult(uint256 jobId) external view override returns (bool) {
        Round storage r = rounds[jobId];
        require(r.tallied, "not tallied");
        return r.result;
    }

    function isValidator(uint256 jobId, address user) public view returns (bool) {
        Round storage r = rounds[jobId];
        for (uint256 i = 0; i < r.validators.length; i++) {
            if (r.validators[i] == user) {
                return true;
            }
        }
        return false;
    }

    function getValidators(uint256 jobId) external view returns (address[] memory) {
        return rounds[jobId].validators;
    }

    function getWinningValidators(uint256 jobId) external view override returns (address[] memory) {
        Round storage r = rounds[jobId];
        require(r.tallied, "not tallied");
        uint256 count;
        for (uint256 i = 0; i < r.validators.length; i++) {
            Vote storage v = r.votes[r.validators[i]];
            if (v.revealed && v.vote == r.result) {
                count++;
            }
        }
        address[] memory winners = new address[](count);
        uint256 idx;
        for (uint256 i = 0; i < r.validators.length; i++) {
            address validator = r.validators[i];
            Vote storage v = r.votes[validator];
            if (v.revealed && v.vote == r.result) {
                winners[idx++] = validator;
            }
        }
        return winners;
    }

    function setCommitWindow(uint256 window) external onlyOwner {
        commitWindow = window;
        emit ParametersUpdated();
    }

    function setRevealWindow(uint256 window) external onlyOwner {
        revealWindow = window;
        emit ParametersUpdated();
    }

    function setValidatorsPerJob(uint256 count) external onlyOwner {
        validatorsPerJob = count;
        emit ParametersUpdated();
    }

    function setSelectionSeed(uint256 seed) external onlyOwner {
        selectionSeed = seed;
        emit ParametersUpdated();
    }

    function setSlashPercentage(uint256 pct) external onlyOwner {
        slashPercentage = pct;
        emit ParametersUpdated();
    }

    /// @notice Updates the root node for validator club identities
    /// @param node ENS root node
    function setClubRootNode(bytes32 node) external onlyOwner {
        clubRootNode = node;
        emit RootNodeUpdated(node);
    }

    /// @notice Updates the validator Merkle root
    /// @param root Merkle root for validators
    function setValidatorMerkleRoot(bytes32 root) external onlyOwner {
        validatorMerkleRoot = root;
        emit MerkleRootUpdated(root);
    }

    /// @notice Adds a validator to the additional allowlist
    function addAdditionalValidator(
        address validator,
        string calldata subdomain,
        bytes32[] calldata proof
    ) external onlyOwner {
        if (!additionalValidators[validator]) {
            additionalValidators[validator] = true;
            validatorPool.push(validator);
        }
        validatorSubdomains[validator] = subdomain;
        bytes32[] storage p = validatorProofs[validator];
        delete p;
        for (uint256 i = 0; i < proof.length; i++) {
            p.push(proof[i]);
        }
    }

    /// @notice Removes a validator from the additional allowlist
    function removeAdditionalValidator(address validator) external onlyOwner {
        if (additionalValidators[validator]) {
            delete additionalValidators[validator];
            delete validatorSubdomains[validator];
            delete validatorProofs[validator];
            for (uint256 i = 0; i < validatorPool.length; i++) {
                if (validatorPool[i] == validator) {
                    validatorPool[i] = validatorPool[validatorPool.length - 1];
                    validatorPool.pop();
                    break;
                }
            }
        }
    }
}

