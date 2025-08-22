// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/utils/cryptography/MerkleProof.sol";

interface INameWrapper {
    function ownerOf(uint256 tokenId) external view returns (address);
}

interface IENS {
    function resolver(bytes32 node) external view returns (address);
}

interface IResolver {
    function addr(bytes32 node) external view returns (address);
}

/// @title IdentityLib
/// @notice Provides ENS and Merkle-tree based identity verification utilities
library IdentityLib {
    using MerkleProof for bytes32[];

    /// @notice Emitted when ownership is confirmed via Merkle proof or ENS data
    /// @param claimant Address whose ownership was proven
    /// @param subdomain ENS subdomain used for verification
    event OwnershipVerified(address indexed claimant, string subdomain);

    /// @notice Emitted when Merkle proof verification fails and ENS recovery kicks in
    /// @param claimant Address attempting recovery
    /// @param subdomain ENS subdomain used for verification
    event RecoveryInitiated(address indexed claimant, string subdomain);

    /// @notice Verifies that `claimant` controls `subdomain` under the `rootNode`.
    /// If the ENS record does not match, the provided Merkle proof can be used
    /// to prove prior ownership which triggers a recovery flow.
    /// @param claimant Address claiming ownership
    /// @param subdomain ENS subdomain being proven
    /// @param proof Merkle proof validating the claimant
    /// @param rootNode ENS root node under which the subdomain lives
    /// @param agentMerkleRoot Merkle root covering registered agents
    /// @param validatorMerkleRoot Merkle root covering registered validators
    /// @param ens ENS registry used for resolver lookups
    /// @param wrapper NameWrapper contract controlling wrapped names
    /// @return valid True if ownership verified or recovery initiated
    function verify(
        address claimant,
        string memory subdomain,
        bytes32[] memory proof,
        bytes32 rootNode,
        bytes32 agentMerkleRoot,
        bytes32 validatorMerkleRoot,
        IENS ens,
        INameWrapper wrapper
    ) internal returns (bool valid) {
        return
            _verifyOwnership(
                claimant,
                subdomain,
                proof,
                rootNode,
                agentMerkleRoot,
                validatorMerkleRoot,
                ens,
                wrapper
            );
    }

    /// @notice Convenience overload that defaults the agent Merkle root and
    /// ENS registry parameters. Used when only validator membership needs to
    /// be proven.
    /// @param claimant Address claiming ownership
    /// @param subdomain ENS subdomain being proven
    /// @param proof Merkle proof validating the claimant
    /// @param rootNode ENS root node under which the subdomain lives
    /// @param validatorMerkleRoot Merkle root covering registered validators
    /// @return valid True if ownership verified or recovery initiated
    function verify(
        address claimant,
        string memory subdomain,
        bytes32[] memory proof,
        bytes32 rootNode,
        bytes32 validatorMerkleRoot
    ) internal returns (bool valid) {
        return
            _verifyOwnership(
                claimant,
                subdomain,
                proof,
                rootNode,
                bytes32(0),
                validatorMerkleRoot,
                IENS(address(0)),
                INameWrapper(address(0))
            );
    }

    /// @notice Internal helper performing the actual verification logic
    function _verifyOwnership(
        address claimant,
        string memory subdomain,
        bytes32[] memory proof,
        bytes32 rootNode,
        bytes32 agentMerkleRoot,
        bytes32 validatorMerkleRoot,
        IENS ens,
        INameWrapper wrapper
    ) internal returns (bool valid) {
        bytes32 label = keccak256(bytes(subdomain));
        bytes32 subnode = keccak256(abi.encodePacked(rootNode, label));
        bytes32 leaf = keccak256(abi.encodePacked(subnode, claimant));

        // Step 1: Attempt Merkle proof against agent or validator roots
        if (proof.verify(agentMerkleRoot, leaf) || proof.verify(validatorMerkleRoot, leaf)) {
            emit OwnershipVerified(claimant, subdomain);
            return true;
        }

        // Merkle proof failed, attempt ENS-based recovery
        emit RecoveryInitiated(claimant, subdomain);

        // Step 3: Check ownership via NameWrapper
        try wrapper.ownerOf(uint256(subnode)) returns (address owner) {
            if (owner == claimant) {
                emit OwnershipVerified(claimant, subdomain);
                return true;
            }
        } catch {}

        // Step 4: Resolve ENS record directly
        try ens.resolver(subnode) returns (address resolverAddr) {
            if (resolverAddr != address(0)) {
                try IResolver(resolverAddr).addr(subnode) returns (address resolved) {
                    if (resolved == claimant) {
                        emit OwnershipVerified(claimant, subdomain);
                        return true;
                    }
                } catch {}
            }
        } catch {}

        // All checks failed
        return false;
    }
}

