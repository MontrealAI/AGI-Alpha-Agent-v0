// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/math/Math.sol";

/// @title ReputationEngine
/// @notice Tracks agent and validator reputation with diminishing returns
contract ReputationEngine is Ownable {
    using Math for uint256;

    uint256 public constant MAX_REPUTATION = 88_888;

    mapping(address => uint256) public reputation;
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

    /// @notice Called when an agent applies for a job
    function onApply(address user) external onlyCaller {
        _requireNotBlacklisted(user);
        _increase(user, 100);
    }

    /// @notice Called when a job finalizes
    function onFinalize(address user, bool success) external onlyCaller {
        _requireNotBlacklisted(user);
        if (success) {
            _increase(user, 1000);
        } else {
            _decrease(user, 1000);
        }
    }

    /// @notice Called when a validator participates
    function onValidate(address user, bool success) external onlyCaller {
        _requireNotBlacklisted(user);
        if (success) {
            _increase(user, 200);
        } else {
            _decrease(user, 200);
        }
    }

    function _requireNotBlacklisted(address user) internal view {
        require(!blacklist[user], "blacklisted");
    }

    function _increase(address user, uint256 base) internal {
        uint256 current = reputation[user];
        uint256 delta = _calcPositiveDelta(current, base);
        uint256 newRep = current + delta;
        if (newRep > MAX_REPUTATION) newRep = MAX_REPUTATION;
        reputation[user] = newRep;
        emit ReputationUpdated(user, newRep);
    }

    function _decrease(address user, uint256 base) internal {
        uint256 current = reputation[user];
        uint256 delta = _calcNegativeDelta(current, base);
        uint256 newRep = current > delta ? current - delta : 0;
        reputation[user] = newRep;
        emit ReputationUpdated(user, newRep);
    }

    function _calcPositiveDelta(uint256 rep, uint256 base) internal pure returns (uint256) {
        uint256 logTerm = Math.log2(rep + 2);
        if (logTerm == 0) logTerm = 1;
        uint256 delta = base / logTerm;
        return delta == 0 ? 1 : delta;
    }

    function _calcNegativeDelta(uint256 rep, uint256 base) internal pure returns (uint256) {
        uint256 logTerm = Math.log2(rep + 2);
        if (logTerm == 0) logTerm = 1;
        return base * logTerm;
    }
}

