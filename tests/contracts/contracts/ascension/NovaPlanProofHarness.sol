// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/utils/cryptography/MerkleProof.sol";

/// @notice Test-only parity harness; uses the same pinned verifier as MARK.
contract NovaPlanProofHarness {
    function verify(bytes32[] calldata proof, bytes32 root, bytes32 leaf) external pure returns (bool) {
        return MerkleProof.verifyCalldata(proof, root, leaf);
    }
}
