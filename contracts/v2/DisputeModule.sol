// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";

interface IStakeManager {
    function lock(address user, uint256 amount) external;
    function release(address user, uint256 amount) external;
    function slash(address offender, address employer, uint256 amount, uint256 burnPctOverride) external;
}

/// @title DisputeModule
/// @notice Handles dispute resolution between employer and worker
contract DisputeModule is Ownable {
    IStakeManager public stakeManager;
    address public jobRegistry;

    mapping(uint256 => bool) public disputed;
    mapping(uint256 => address) public employer;
    mapping(uint256 => address) public worker;
    mapping(uint256 => uint256) public reward;

    mapping(address => bool) public moderators;

    event DisputeRaised(uint256 indexed jobId);
    event DisputeResolved(uint256 indexed jobId, bool employerWins);

    constructor(address _stakeManager, address _jobRegistry) Ownable(msg.sender) {
        stakeManager = IStakeManager(_stakeManager);
        jobRegistry = _jobRegistry;
    }

    modifier onlyAuthorized(address emp, address work) {
        require(msg.sender == jobRegistry || msg.sender == emp || msg.sender == work, "not auth");
        _;
    }

    modifier onlyModerator() {
        require(moderators[msg.sender], "not mod");
        _;
    }

    function addModerator(address mod) external onlyOwner {
        moderators[mod] = true;
    }

    function removeModerator(address mod) external onlyOwner {
        delete moderators[mod];
    }

    /// @notice Raises a dispute and locks worker stake
    function raiseDispute(
        uint256 jobId,
        address emp,
        address work,
        uint256 rew
    ) external onlyAuthorized(emp, work) {
        require(!disputed[jobId], "disputed");
        disputed[jobId] = true;
        employer[jobId] = emp;
        worker[jobId] = work;
        reward[jobId] = rew;
        stakeManager.lock(work, rew);
        emit DisputeRaised(jobId);
    }

    /// @notice Resolves a dispute
    function resolve(uint256 jobId, bool employerWins) external onlyModerator {
        require(disputed[jobId], "not disputed");
        disputed[jobId] = false;
        address emp = employer[jobId];
        address work = worker[jobId];
        uint256 rew = reward[jobId];
        delete employer[jobId];
        delete worker[jobId];
        delete reward[jobId];
        if (employerWins) {
            stakeManager.slash(work, emp, rew, 0);
            stakeManager.release(emp, rew);
        } else {
            stakeManager.release(work, rew);
        }
        emit DisputeResolved(jobId, employerWins);
    }

    /// @notice Returns whether a job is disputed
    function isDisputed(uint256 jobId) external view returns (bool) {
        return disputed[jobId];
    }
}

