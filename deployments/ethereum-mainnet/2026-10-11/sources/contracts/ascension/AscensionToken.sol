// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol";
import "../v2/Constants.sol";

interface IAscensionBurn { function burn(uint256 amount) external; }

/// @notice Canonical token only; reject fee-on-transfer deposits and verify actual supply destruction.
abstract contract AscensionToken {
    using SafeERC20 for IERC20;
    IERC20 public constant token = IERC20(Constants.AGIALPHA);
    constructor() {
        require(address(token).code.length > 0, "AGIALPHA contract required");
        require(IERC20Metadata(address(token)).decimals() == 18, "wrong decimals");
    }
    function _receive(address from, uint256 amount) internal {
        uint256 before_ = token.balanceOf(address(this));
        token.safeTransferFrom(from, address(this), amount);
        require(token.balanceOf(address(this)) == before_ + amount, "non-exact deposit");
    }
    function _burn(uint256 amount) internal {
        if (amount == 0) return;
        uint256 before_ = token.totalSupply();
        IAscensionBurn(address(token)).burn(amount);
        require(token.totalSupply() == before_ - amount, "supply not burned");
    }
}
