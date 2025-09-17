// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract MockReputationEngine {
    bool private blacklisted;

    event Applied(address indexed user, uint256 reward, uint256 duration);

    function setBlacklisted(bool value) external {
        blacklisted = value;
    }

    function onApply(address user, uint256 reward, uint256 duration) external {
        emit Applied(user, reward, duration);
    }

    function onFinalize(address, uint256, uint256, bool) external {}

    function isBlacklisted(address) external view returns (bool) {
        return blacklisted;
    }

    function reputationOf(address) external pure returns (uint256) {
        return 0;
    }

    function meetsThreshold(address) external pure returns (bool) {
        return true;
    }
}
