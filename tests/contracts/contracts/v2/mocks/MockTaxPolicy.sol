// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract MockTaxPolicy {
    bool private acknowledged = true;

    function setAcknowledged(bool value) external {
        acknowledged = value;
    }

    function isAcknowledged(address) external view returns (bool) {
        return acknowledged;
    }
}
