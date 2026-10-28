// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "../access/GoalOSAccessControl.sol";

contract AEPAttestationRegistry is GoalOSAccessControl {
    struct Attestation { bytes32 subjectType; uint256 subjectId; bytes32 attestationHash; bytes32 schemaHash; string metadataURI; address attester; uint256 createdAt; bool revoked; }
    uint256 public nextAttestationId = 1;
    mapping(uint256 => Attestation) public attestations;
    event Attested(uint256 indexed attestationId, bytes32 indexed subjectType, uint256 indexed subjectId, bytes32 attestationHash, address attester);
    event AttestationRevoked(uint256 indexed attestationId, bytes32 indexed reasonHash);
    constructor(address admin) GoalOSAccessControl(admin) {}
    function attest(bytes32 subjectType, uint256 subjectId, bytes32 attestationHash, bytes32 schemaHash, string calldata metadataURI) external onlyOperator returns (uint256 attestationId) {
        require(subjectType != bytes32(0), "AEP_ATT_ZERO_TYPE");
        require(subjectId != 0, "AEP_ATT_ZERO_SUBJECT");
        require(attestationHash != bytes32(0), "AEP_ATT_ZERO_HASH");
        attestationId = nextAttestationId++;
        attestations[attestationId] = Attestation(subjectType, subjectId, attestationHash, schemaHash, metadataURI, msg.sender, block.timestamp, false);
        emit Attested(attestationId, subjectType, subjectId, attestationHash, msg.sender);
    }
    function revokeAttestation(uint256 attestationId, bytes32 reasonHash) external onlyOperator {
        require(attestations[attestationId].createdAt != 0, "AEP_ATT_NOT_FOUND");
        attestations[attestationId].revoked = true;
        emit AttestationRevoked(attestationId, reasonHash);
    }
}
