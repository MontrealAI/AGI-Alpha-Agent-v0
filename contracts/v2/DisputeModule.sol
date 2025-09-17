// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";

interface IStakeManager {
    function slash(address offender, address beneficiary, uint256 amount) external;
}

interface IJobRegistry {
    function jobs(uint256 jobId)
        external
        view
        returns (
            address client,
            uint96 reward,
            address worker,
            uint40 createdAt,
            uint40 deadline,
            uint8 status
        );

    function resolveDispute(uint256 jobId) external;
}

/// @title DisputeModule
/// @notice Handles job disputes and resolutions
contract DisputeModule is Ownable {
    IStakeManager public stakeManager;
    address public jobRegistry;

    mapping(address => bool) public moderators;

    struct Dispute {
        address employer;
        address worker;
        bool resolved;
        bool employerWins;
        bool exists;
    }

    mapping(uint256 => Dispute) public disputes;

    event DisputeRaised(uint256 indexed jobId, address indexed employer, address indexed worker);
    event DisputeResolved(uint256 indexed jobId, bool employerWins);

    modifier onlyJobRegistry() {
        require(msg.sender == jobRegistry, "not registry");
        _;
    }

    modifier onlyModeratorOrOwner() {
        require(moderators[msg.sender] || msg.sender == owner(), "not authorized");
        _;
    }

    constructor(address _jobRegistry, address _stakeManager) Ownable(msg.sender) {
        jobRegistry = _jobRegistry;
        stakeManager = IStakeManager(_stakeManager);
    }

    /// @notice Updates the job registry address
    function setJobRegistry(address _registry) external onlyOwner {
        jobRegistry = _registry;
    }

    /// @notice Updates the stake manager address
    function setStakeManager(address _stakeManager) external onlyOwner {
        stakeManager = IStakeManager(_stakeManager);
    }

    /// @notice Adds a moderator
    function addModerator(address mod) external onlyOwner {
        moderators[mod] = true;
    }

    /// @notice Removes a moderator
    function removeModerator(address mod) external onlyOwner {
        delete moderators[mod];
    }

    /// @notice Logs a new dispute
    function dispute(uint256 jobId, address employer, address worker) external onlyJobRegistry {
        require(!disputes[jobId].exists, "disputed");
        disputes[jobId] = Dispute({
            employer: employer,
            worker: worker,
            resolved: false,
            employerWins: false,
            exists: true
        });
        emit DisputeRaised(jobId, employer, worker);
    }

    /// @notice Resolves an existing dispute
    /// @param jobId Identifier of the job
    /// @param employerWins True if employer wins the dispute
    function resolve(uint256 jobId, bool employerWins) external onlyModeratorOrOwner {
        Dispute storage d = disputes[jobId];
        require(d.exists && !d.resolved, "no dispute");
        d.resolved = true;
        d.employerWins = employerWins;
        if (employerWins) {
            ( , uint96 reward, , , , ) = IJobRegistry(jobRegistry).jobs(jobId);
            IJobRegistry(jobRegistry).resolveDispute(jobId);
            stakeManager.slash(d.worker, d.employer, reward);
        }
        emit DisputeResolved(jobId, employerWins);
    }

    /// @notice Ensures job finalization only if dispute resolved in worker's favor
    function onFinalize(uint256 jobId) external view onlyJobRegistry {
        Dispute memory d = disputes[jobId];
        require(!d.exists || (d.resolved && !d.employerWins), "disputed");
    }
}

