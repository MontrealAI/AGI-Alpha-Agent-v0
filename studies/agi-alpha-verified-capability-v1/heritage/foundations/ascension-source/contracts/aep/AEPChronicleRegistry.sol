// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "../access/GoalOSAccessControl.sol";

contract AEPChronicleRegistry is GoalOSAccessControl {
    struct ChronicleEntry {
        bytes32 entryType;
        bytes32 entryHash;
        bytes32 previousEntryHash;
        bytes32 subjectHash;
        string metadataURI;
        address writer;
        uint256 createdAt;
    }

    uint256 public nextEntryId = 1;
    bytes32 public latestEntryHash;
    mapping(uint256 => ChronicleEntry) public entries;

    event ChronicleEntryRecorded(uint256 indexed entryId, bytes32 indexed entryType, bytes32 indexed entryHash, bytes32 previousEntryHash, string metadataURI);

    constructor(address admin) GoalOSAccessControl(admin) {}

    function recordEntry(bytes32 entryType, bytes32 entryHash, bytes32 subjectHash, string calldata metadataURI) external onlyOperator returns (uint256 entryId) {
        require(entryType != bytes32(0), "CHRON_ZERO_TYPE");
        require(entryHash != bytes32(0), "CHRON_ZERO_HASH");
        bytes32 previous = latestEntryHash;
        entryId = nextEntryId++;
        entries[entryId] = ChronicleEntry(entryType, entryHash, previous, subjectHash, metadataURI, msg.sender, block.timestamp);
        latestEntryHash = entryHash;
        emit ChronicleEntryRecorded(entryId, entryType, entryHash, previous, metadataURI);
    }
}
