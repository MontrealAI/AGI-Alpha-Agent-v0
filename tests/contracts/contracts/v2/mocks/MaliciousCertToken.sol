// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "../CertificateNFT.sol";

contract MaliciousCertToken is ERC20 {
    CertificateNFT public cert;
    bool public attack;
    uint256 public tokenId;

    constructor() ERC20("Malicious AGI", "MAGI") {}

    function setCert(address _cert) external {
        cert = CertificateNFT(_cert);
    }

    function setAttack(bool _attack, uint256 _tokenId) external {
        attack = _attack;
        tokenId = _tokenId;
    }

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }

    function _update(address from, address to, uint256 value) internal override {
        super._update(from, to, value);
        if (attack) {
            attack = false;
            cert.purchase(tokenId);
        }
    }
}
