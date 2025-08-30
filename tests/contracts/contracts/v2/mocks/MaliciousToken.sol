// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "../StakeManager.sol";

contract MaliciousToken is ERC20 {
    StakeManager public stake;
    bool public attack;

    constructor() ERC20("Malicious AGI", "MAGI") {}

    function setStake(address _stake) external {
        stake = StakeManager(_stake);
    }

    function setAttack(bool _attack) external {
        attack = _attack;
    }

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }

    function _update(address from, address to, uint256 value) internal override {
        super._update(from, to, value);
        if (attack) {
            attack = false;
            // attempt to reenter StakeManager
            stake.withdrawStake(StakeManager.Role.Agent, 0);
        }
    }
}
