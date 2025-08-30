// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";

contract JobRegistry is Ownable {
    uint96 public maxJobReward;
    uint40 public maxJobDuration;
    uint256 public validatorRewardPct;

    event ValidatorRewardPctUpdated(uint256 pct);
    event MaxJobRewardUpdated(uint96 amount);
    event MaxJobDurationUpdated(uint40 duration);

    constructor() Ownable(msg.sender) {}

    function setValidatorRewardPct(uint256 pct) external onlyOwner {
        require(pct <= 100, "pct too high");
        validatorRewardPct = pct;
        emit ValidatorRewardPctUpdated(pct);
    }

    function setMaxJobReward(uint96 amount) external onlyOwner {
        maxJobReward = amount;
        emit MaxJobRewardUpdated(amount);
    }

    function setMaxJobDuration(uint40 duration) external onlyOwner {
        maxJobDuration = duration;
        emit MaxJobDurationUpdated(duration);
    }
}
