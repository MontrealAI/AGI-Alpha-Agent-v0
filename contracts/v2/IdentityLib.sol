// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/utils/cryptography/MerkleProof.sol";

/// @title IdentityLib
/// @notice Provides ENS and Merkle-tree based identity verification utilities
library IdentityLib {
    using MerkleProof for bytes32[];

    /// @notice Emitted when ownership is successfully verified
    /// @param claimant Address whose ownership was proven
    /// @param subdomain ENS subdomain used for verification
    event OwnershipVerified(address indexed claimant, string subdomain);

    /// @notice Emitted when the merkle proof path is used for recovery
    /// @param claimant Address attempting recovery
    /// @param subdomain ENS subdomain used for verification
    event RecoveryInitiated(address indexed claimant, string subdomain);

    /// @notice Verifies that `claimant` controls `subdomain` under the `rootNode`.
    /// If the ENS record does not match, the provided Merkle proof can be used
    /// to prove prior ownership which triggers a recovery flow.
    /// @param claimant Address claiming ownership
    /// @param subdomain ENS subdomain being proven
    /// @param proof Merkle proof validating the claimant
    /// @param rootNode Root node used both for ENS hierarchy and Merkle proofs
    /// @return valid True if ownership verified or recovery initiated
    function verify(
        address claimant,
        string memory subdomain,
        bytes32[] memory proof,
        bytes32 rootNode
    ) internal returns (bool valid) {
        return _verifyOwnership(claimant, subdomain, proof, rootNode);
    }

    /// @notice Internal helper performing the actual verification logic
    function _verifyOwnership(
        address claimant,
        string memory subdomain,
        bytes32[] memory proof,
        bytes32 rootNode
    ) internal returns (bool valid) {
        bytes32 label = keccak256(bytes(subdomain));
        bytes32 node = keccak256(abi.encodePacked(rootNode, label));
        bytes32 leaf = keccak256(abi.encodePacked(node, claimant));
        valid = proof.verify(rootNode, leaf);
        if (valid) {
            emit OwnershipVerified(claimant, subdomain);
        } else {
            emit RecoveryInitiated(claimant, subdomain);
        }
    }
}

