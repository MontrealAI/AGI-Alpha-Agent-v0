// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract MockValidationStakeManager {
    mapping(address => uint256) private _validatorStakes;
    uint256 private _minStake;

    function setValidatorStake(address validator, uint256 amount) external {
        _validatorStakes[validator] = amount;
    }

    function setMinValidatorStake(uint256 amount) external {
        _minStake = amount;
    }

    function slash(address, address, uint256) external {}

    function validatorStakes(address user) external view returns (uint256) {
        return _validatorStakes[user];
    }

    function minStakeValidator() external view returns (uint256) {
        return _minStake;
    }
}
