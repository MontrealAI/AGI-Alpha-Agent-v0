// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;
import './IdentityLib.sol';
contract IdentityHarness {
    function verify(address claimant, string calldata subdomain, bytes32[] calldata proof,
                    bytes32 node, bytes32 root) external returns (bool) {
        return IdentityLib.verify(claimant, subdomain, proof, node, root);
    }
}
