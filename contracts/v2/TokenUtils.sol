// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "./Constants.sol";

/// @title TokenUtils
/// @notice Helper functions for converting between whole $AGIALPHA tokens and
/// their smallest units.
library TokenUtils {
    uint256 internal constant UNIT = 10 ** uint256(Constants.AGIALPHA_DECIMALS);

    /// @notice Converts whole tokens to base units (wei-style)
    /// @param amount Amount in whole tokens
    /// @return Amount scaled by 10**18
    function toTokenUnits(uint256 amount) internal pure returns (uint256) {
        return amount * UNIT;
    }

    /// @notice Converts base units to whole tokens
    /// @param amount Amount in base units
    /// @return Amount divided by 10**18
    function fromTokenUnits(uint256 amount) internal pure returns (uint256) {
        return amount / UNIT;
    }
}

