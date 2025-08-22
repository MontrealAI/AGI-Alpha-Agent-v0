// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";

/// @title ReputationEngine
/// @notice Tracks agent and validator reputation with diminishing returns
contract ReputationEngine is Ownable {

    uint256 public constant MAX_REPUTATION = 88_888;

    mapping(address => uint256) private reputation;
    mapping(address => bool) public blacklist;
    mapping(address => bool) public callers;

    uint256 public premiumThreshold;

    event ReputationUpdated(address indexed user, uint256 newReputation);
    event PremiumThresholdUpdated(uint256 threshold);
    event CallerUpdated(address indexed caller, bool allowed);
    event BlacklistUpdated(address indexed user, bool blacklisted);

    constructor() Ownable(msg.sender) {}

    modifier onlyCaller() {
        require(callers[msg.sender], "not caller");
        _;
    }

    /// @notice Authorizes a module to update reputation
    function setCaller(address caller, bool allowed) external onlyOwner {
        callers[caller] = allowed;
        emit CallerUpdated(caller, allowed);
    }

    /// @notice Adds or removes a user from the blacklist
    function setBlacklist(address user, bool value) external onlyOwner {
        blacklist[user] = value;
        emit BlacklistUpdated(user, value);
    }

    /// @notice Checks if a user is blacklisted
    function isBlacklisted(address user) external view returns (bool) {
        return blacklist[user];
    }

    /// @notice Sets the premium reputation threshold
    function setPremiumThreshold(uint256 threshold) external onlyOwner {
        premiumThreshold = threshold;
        emit PremiumThresholdUpdated(threshold);
    }

    /// @notice Returns the reputation score for a user
    function reputationOf(address user) external view returns (uint256) {
        return reputation[user];
    }

    /// @notice Checks whether a user meets the premium threshold
    function meetsThreshold(address user) external view returns (bool) {
        return reputation[user] >= premiumThreshold;
    }

    /// @notice Called when an agent applies for a job
    function onApply(address user, uint256 reward, uint256 duration) external onlyCaller {
        _requireNotBlacklisted(user);
        uint256 points = calculateReputationPoints(reward, duration);
        enforceReputationGrowth(user, int256(points));
    }

    /// @notice Called when a job finalizes
    function onFinalize(
        address user,
        uint256 reward,
        uint256 duration,
        bool success
    ) external onlyCaller {
        _requireNotBlacklisted(user);
        uint256 points = calculateReputationPoints(reward, duration);
        enforceReputationGrowth(user, success ? int256(points) : -int256(points));
    }

    /// @notice Called when a validator participates
    function onValidate(
        address user,
        uint256 agentGain,
        bool success
    ) external onlyCaller {
        _requireNotBlacklisted(user);
        uint256 points = calculateValidatorReputationPoints(agentGain);
        enforceReputationGrowth(user, success ? int256(points) : -int256(points));
    }

    function _requireNotBlacklisted(address user) internal view {
        require(!blacklist[user], "blacklisted");
    }

    function enforceReputationGrowth(address user, int256 change) internal {
        uint256 current = reputation[user];
        uint256 newRep;
        if (change >= 0) {
            newRep = current + uint256(change);
            if (newRep > MAX_REPUTATION) newRep = MAX_REPUTATION;
        } else {
            uint256 decrease = uint256(-change);
            newRep = current > decrease ? current - decrease : 0;
        }
        reputation[user] = newRep;
        emit ReputationUpdated(user, newRep);
    }

    function calculateReputationPoints(uint256 reward, uint256 duration) public pure returns (uint256) {
        if (duration == 0) return reward;
        uint256 points = reward / duration;
        return points == 0 && reward > 0 ? 1 : points;
    }

    function calculateValidatorReputationPoints(uint256 agentGain) public pure returns (uint256) {
        uint256 points = agentGain / 10;
        return points == 0 && agentGain > 0 ? 1 : points;
    }
}

