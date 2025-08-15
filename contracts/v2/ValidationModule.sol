// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "./IdentityLib.sol";

interface IStakeManager {
    function reward(address user, uint256 amount) external;
    function slash(address user, uint256 amount) external;
}

interface IReputationEngine {
    function onValidate(address user, bool success) external;
    function isBlacklisted(address user) external view returns (bool);
}

interface IValidationModule {
    function validate(uint256 jobId, bytes calldata data) external returns (bool);
}

contract ValidationModule is Ownable, IValidationModule {
    struct Vote {
        bytes32 commit;
        bool revealed;
        bool vote;
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
    uint256[] public validatorCountTiers;
    uint256[] public slashingPercentages; // basis points
    uint256 public selectionSeed;

    bytes32 public clubRootNode;
    bytes32 public validatorMerkleRoot;

    mapping(address => bool) public additionalValidators;

    IStakeManager public stakeManager;
    IReputationEngine public reputationEngine;

    mapping(uint256 => Round) private rounds;

    event ValidatorSelected(uint256 indexed jobId, address indexed validator);
    event VoteCommitted(uint256 indexed jobId, address indexed validator);
    event VoteRevealed(uint256 indexed jobId, address indexed validator, bool vote);
    event Tallied(uint256 indexed jobId, bool result);
    event ParametersUpdated();
    event RootNodeUpdated(bytes32 newRootNode);
    event MerkleRootUpdated(bytes32 newMerkleRoot);

    constructor(address _stakeManager, address _reputation) Ownable(msg.sender) {
        stakeManager = IStakeManager(_stakeManager);
        reputationEngine = IReputationEngine(_reputation);
    }

    function validate(uint256 jobId, bytes calldata) external override returns (bool) {
        Round storage r = rounds[jobId];
        require(r.commitEnd == 0, "exists");
        r.commitEnd = uint64(block.timestamp + commitWindow);
        r.revealEnd = uint64(block.timestamp + commitWindow + revealWindow);
        uint256 count = validatorCountTiers.length > 0 ? validatorCountTiers[0] : 0;
        r.validators = new address[](count);
        for (uint256 i = 0; i < count; i++) {
            address v = address(uint160(uint256(keccak256(abi.encode(blockhash(block.number - 1 - i), selectionSeed, jobId, i)))));
            r.validators[i] = v;
            emit ValidatorSelected(jobId, v);
        }
        return true;
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
                IdentityLib.verify(msg.sender, subdomain, proof, clubRootNode),
            "identity"
        );
        require(!reputationEngine.isBlacklisted(msg.sender), "blacklisted");
        Vote storage v = r.votes[msg.sender];
        require(v.commit == bytes32(0), "committed");
        v.commit = commitHash;
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
                IdentityLib.verify(msg.sender, subdomain, proof, clubRootNode),
            "identity"
        );
        require(!reputationEngine.isBlacklisted(msg.sender), "blacklisted");
        Vote storage v = r.votes[msg.sender];
        require(v.commit == keccak256(abi.encode(vote, salt)), "invalid reveal");
        require(!v.revealed, "revealed");
        v.revealed = true;
        v.vote = vote;
        emit VoteRevealed(jobId, msg.sender, vote);
    }

    function tally(uint256 jobId, uint256 reward) external {
        Round storage r = rounds[jobId];
        require(block.timestamp > r.revealEnd, "reveal not over");
        require(!r.tallied, "tallied");
        uint256 yes;
        uint256 no;
        uint256 slashAmount = (reward * (slashingPercentages.length > 0 ? slashingPercentages[0] : 0)) / 10_000;
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
                stakeManager.slash(validator, slashAmount);
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
                    stakeManager.reward(validator, reward);
                    reputationEngine.onValidate(validator, true);
                } else {
                    stakeManager.slash(validator, slashAmount);
                    reputationEngine.onValidate(validator, false);
                }
            }
        }
        emit Tallied(jobId, r.result);
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

    function setWindows(uint256 commitWindow_, uint256 revealWindow_) external onlyOwner {
        commitWindow = commitWindow_;
        revealWindow = revealWindow_;
        emit ParametersUpdated();
    }

    function setValidatorCountTiers(uint256[] calldata counts) external onlyOwner {
        validatorCountTiers = counts;
        emit ParametersUpdated();
    }

    function setSlashingPercentages(uint256[] calldata pcts) external onlyOwner {
        slashingPercentages = pcts;
        emit ParametersUpdated();
    }

    function setSelectionSeed(uint256 seed) external onlyOwner {
        selectionSeed = seed;
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
    function addAdditionalValidator(address validator) external onlyOwner {
        additionalValidators[validator] = true;
    }

    /// @notice Removes a validator from the additional allowlist
    function removeAdditionalValidator(address validator) external onlyOwner {
        delete additionalValidators[validator];
    }
}

