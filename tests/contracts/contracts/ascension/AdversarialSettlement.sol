// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;
import "./AscensionToken.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";

contract SettlementHarness is AscensionToken {
    function receiveTokens(uint256 amount) external { _receive(msg.sender, amount); }
    function sendTokens(address to, uint256 amount) external { _send(to, amount); }
    function burnTokens(uint256 amount) external { _burn(amount); }
}

contract AdversarialSettlementToken is ERC20Burnable {
    uint8 public mode;
    address public victim;
    constructor() ERC20("Adversarial test token", "TEST") {}
    function mint(address to, uint256 amount) external { _mint(to, amount); }
    function configure(uint8 value, address victim_) external { mode = value; victim = victim_; }
    function transfer(address to, uint256 amount) public override returns (bool) {
        if (mode == 1) { _transfer(msg.sender, to, amount - 1); _burn(msg.sender, 1); return true; }
        if (mode == 2) return true;
        return super.transfer(to, amount);
    }
    function burn(uint256 amount) public override {
        if (mode == 3) _burn(victim, amount);
        else if (mode == 4) _transfer(msg.sender, victim, amount);
        else super.burn(amount);
    }
}
