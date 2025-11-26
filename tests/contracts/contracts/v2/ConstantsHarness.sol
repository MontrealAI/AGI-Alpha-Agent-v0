// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "./Constants.sol";

contract ConstantsHarness {
    function agiAlpha() external pure returns (address) {
        return Constants.AGIALPHA;
    }

    function agiDecimals() external pure returns (uint8) {
        return Constants.AGIALPHA_DECIMALS;
    }
}
