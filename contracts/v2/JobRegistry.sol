// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "./IdentityLib.sol";

interface IValidationModule {
    function validate(uint256 jobId, bytes calldata data) external returns (bool);
    function validationResult(uint256 jobId) external view returns (bool);
    function getWinningValidators(uint256 jobId) external view returns (address[] memory);
}

interface IStakeManager {
    function lock(uint256 jobId, address employer, uint256 amount) external;
    function release(
        uint256 jobId,
        address recipient,
        address[] calldata validators,
        uint256 validatorPct
    ) external;
}

interface IReputationEngine {
    function onApply(address user, uint256 reward, uint256 duration) external;
    function onFinalize(address user, uint256 reward, uint256 duration, bool success) external;
    function isBlacklisted(address user) external view returns (bool);
    function reputationOf(address user) external view returns (uint256);
    function meetsThreshold(address user) external view returns (bool);
}

interface IDisputeModule {
    function onFinalize(uint256 jobId) external;
    function dispute(uint256 jobId) external;
}

interface ICertificateNFT {
    function mint(address to, uint256 jobId) external;
}

interface ITaxPolicy {
    function isAcknowledged(address user) external view returns (bool);
}

contract JobRegistry is Ownable {
    enum Status {
        None,
        Created,
        Applied,
        Submitted,
        Finalized
    }

    struct Job {
        address client;      // 20 bytes
        uint96 reward;       // 12 bytes (fits with client in one slot)
        address worker;      // 20 bytes
        uint40 createdAt;    // 5 bytes
        uint40 deadline;     // 5 bytes
        Status status;       // 1 byte
    }

    uint256 public nextJobId;
    mapping(uint256 => Job) public jobs;

    IValidationModule public validationModule;
    IStakeManager public stakeManager;
    IReputationEngine public reputationEngine;
    IDisputeModule public disputeModule;
    ICertificateNFT public certificateNFT;
    ITaxPolicy public taxPolicy;

    bytes32 public agentRootNode;
    bytes32 public clubRootNode;
    bytes32 public agentMerkleRoot;
    bytes32 public validatorMerkleRoot;

    mapping(address => bool) public additionalAgents;
    mapping(address => bool) public additionalValidators;

    uint96 public maxJobReward;
    uint40 public maxJobDuration;
    uint256 public validatorRewardPct;

    event JobCreated(uint256 indexed jobId, address indexed client, uint96 reward, uint40 deadline);
    event JobApplied(uint256 indexed jobId, address indexed worker);
    event JobSubmitted(uint256 indexed jobId, address indexed client, address indexed worker, bytes result);
    event JobCancelled(uint256 indexed jobId, address indexed client);
    event JobDelisted(uint256 indexed jobId, address indexed client);
    event JobDisputed(uint256 indexed jobId);
    event JobFinalized(uint256 indexed jobId, address indexed client, address indexed worker);
    event ModulesUpdated(
        address validationModule,
        address stakeManager,
        address reputationEngine,
        address disputeModule,
        address certificateNFT,
        address taxPolicy
    );
    event RootNodeUpdated(bytes32 newRootNode);
    event MerkleRootUpdated(bytes32 newMerkleRoot);

    /// @notice Updates validator reward percentage
    /// @param pct Percentage of escrow sent to validators
    function setValidatorRewardPct(uint256 pct) external onlyOwner {
        require(pct <= 100, "pct too high");
        validatorRewardPct = pct;
    }

    constructor() Ownable(msg.sender) {}

    /// @notice Sets module contract addresses
    /// @param _validation Address of validation module
    /// @param _stake Address of stake manager
    /// @param _reputation Address of reputation engine
    /// @param _dispute Address of dispute module
    /// @param _certificate Address of certificate NFT
    /// @param _tax Address of tax policy module
    function setModules(
        address _validation,
        address _stake,
        address _reputation,
        address _dispute,
        address _certificate,
        address _tax
    ) external onlyOwner {
        validationModule = IValidationModule(_validation);
        stakeManager = IStakeManager(_stake);
        reputationEngine = IReputationEngine(_reputation);
        disputeModule = IDisputeModule(_dispute);
        certificateNFT = ICertificateNFT(_certificate);
        taxPolicy = ITaxPolicy(_tax);
        emit ModulesUpdated(_validation, _stake, _reputation, _dispute, _certificate, _tax);
    }

    /// @notice Updates the root nodes for agents and clubs
    /// @param agentNode ENS root node for agents
    /// @param clubNode ENS root node for clubs
    function setRootNodes(bytes32 agentNode, bytes32 clubNode) external onlyOwner {
        agentRootNode = agentNode;
        clubRootNode = clubNode;
        emit RootNodeUpdated(agentNode);
        emit RootNodeUpdated(clubNode);
    }

    /// @notice Updates the Merkle roots for agents and validators
    /// @param agentRoot Merkle root for agents
    /// @param validatorRoot Merkle root for validators
    function setMerkleRoots(bytes32 agentRoot, bytes32 validatorRoot) external onlyOwner {
        agentMerkleRoot = agentRoot;
        validatorMerkleRoot = validatorRoot;
        emit MerkleRootUpdated(agentRoot);
        emit MerkleRootUpdated(validatorRoot);
    }

    /// @notice Adds an address to the additional agents allowlist
    /// @param agent Address to add
    function addAdditionalAgent(address agent) external onlyOwner {
        additionalAgents[agent] = true;
    }

    /// @notice Removes an address from the additional agents allowlist
    /// @param agent Address to remove
    function removeAdditionalAgent(address agent) external onlyOwner {
        delete additionalAgents[agent];
    }

    /// @notice Adds an address to the additional validators allowlist
    /// @param validator Address to add
    function addAdditionalValidator(address validator) external onlyOwner {
        additionalValidators[validator] = true;
    }

    /// @notice Removes an address from the additional validators allowlist
    /// @param validator Address to remove
    function removeAdditionalValidator(address validator) external onlyOwner {
        delete additionalValidators[validator];
    }

    /// @notice Sets the maximum job reward
    /// @param amount Maximum reward allowed per job
    function setMaxJobReward(uint96 amount) external onlyOwner {
        maxJobReward = amount;
    }

    /// @notice Sets the maximum job duration in seconds
    /// @param duration Maximum allowed duration from now
    function setMaxJobDuration(uint40 duration) external onlyOwner {
        maxJobDuration = duration;
    }

    /// @notice Creates a new job and locks client stake
    /// @param reward Payment amount locked in the stake manager
    /// @param deadline Unix timestamp for job deadline
    /// @return jobId Identifier of the created job
    function createJob(uint96 reward, uint40 deadline) external returns (uint256 jobId) {
        require(!reputationEngine.isBlacklisted(msg.sender), "blacklisted");
        require(taxPolicy.isAcknowledged(msg.sender), "tax");
        require(reward <= maxJobReward, "reward too high");
        require(deadline != 0 && deadline <= block.timestamp + maxJobDuration, "invalid deadline");
        jobId = ++nextJobId;
        stakeManager.lock(jobId, msg.sender, reward);
        jobs[jobId] = Job({
            client: msg.sender,
            reward: reward,
            worker: address(0),
            createdAt: uint40(block.timestamp),
            deadline: deadline,
            status: Status.Created
        });
        emit JobCreated(jobId, msg.sender, reward, deadline);
    }

    /// @notice Applies for an open job after identity verification
    /// @param jobId Identifier of the job
    /// @param subdomain ENS subdomain used for verification
    /// @param proof Merkle proof validating agent ownership
    function applyForJob(
        uint256 jobId,
        string calldata subdomain,
        bytes32[] calldata proof
    ) external {
        require(!reputationEngine.isBlacklisted(msg.sender), "blacklisted");
        require(taxPolicy.isAcknowledged(msg.sender), "tax");
        require(
            additionalAgents[msg.sender] ||
                IdentityLib.verify(msg.sender, subdomain, proof, agentRootNode),
            "identity"
        );
        Job storage job = jobs[jobId];
        require(job.status == Status.Created, "invalid status");
        uint256 duration = job.deadline - job.createdAt;
        reputationEngine.onApply(msg.sender, job.reward, duration);
        job.worker = msg.sender;
        job.status = Status.Applied;
        emit JobApplied(jobId, msg.sender);
    }

    /// @notice Cancels a job and refunds the client
    /// @param jobId Identifier of the job
    function cancelJob(uint256 jobId) external {
        Job storage job = jobs[jobId];
        require(job.client == msg.sender, "not client");
        require(job.status == Status.Created, "invalid status");
        stakeManager.release(jobId, job.client, new address[](0), 0);
        delete jobs[jobId];
        emit JobCancelled(jobId, job.client);
    }

    /// @notice Delists a job by the contract owner
    /// @param jobId Identifier of the job
    function delistJob(uint256 jobId) external onlyOwner {
        Job storage job = jobs[jobId];
        require(job.status == Status.Created, "invalid status");
        stakeManager.release(jobId, job.client, new address[](0), 0);
        delete jobs[jobId];
        emit JobDelisted(jobId, job.client);
    }

    /// @notice Submits work for a job, validated by validation module
    /// @param jobId Identifier of the job
    /// @param result Submission payload
    function submit(uint256 jobId, bytes calldata result) external {
        Job storage job = jobs[jobId];
        require(job.worker == msg.sender, "not worker");
        require(job.status == Status.Applied, "invalid status");
        require(block.timestamp <= job.deadline, "deadline passed");
        require(validationModule.validate(jobId, result), "validation failed");
        job.status = Status.Submitted;
        emit JobSubmitted(jobId, job.client, msg.sender, result);
    }

    /// @notice Opens a dispute for a submitted job
    /// @param jobId Identifier of the job
    function dispute(uint256 jobId) external {
        Job storage job = jobs[jobId];
        require(job.status == Status.Submitted, "invalid status");
        require(address(disputeModule) != address(0), "no module");
        disputeModule.dispute(jobId);
        emit JobDisputed(jobId);
    }

    /// @notice Finalizes a job and releases payment
    /// @param jobId Identifier of the job
    function finalize(uint256 jobId) external {
        Job storage job = jobs[jobId];
        require(job.client == msg.sender, "not client");
        require(job.status == Status.Submitted, "invalid status");
        require(validationModule.validationResult(jobId), "validation failed");
        address[] memory winners = validationModule.getWinningValidators(jobId);
        stakeManager.release(jobId, job.worker, winners, validatorRewardPct);
        uint256 duration = block.timestamp - job.createdAt;
        reputationEngine.onFinalize(job.worker, job.reward, duration, true);
        if (address(disputeModule) != address(0)) {
            disputeModule.onFinalize(jobId);
        }
        if (address(certificateNFT) != address(0)) {
            certificateNFT.mint(job.worker, jobId);
        }
        job.status = Status.Finalized;
        emit JobFinalized(jobId, job.client, job.worker);
    }
}

