// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

// Local acceptance fixtures only. Never shipped in contracts/ascension or deployed as identity services.
contract MockAscensionENS {
    mapping(bytes32 => address) public owner;
    function setOwner(bytes32 node, address account) external { owner[node] = account; }
}
contract MockAscensionWrapper {
    struct Name { address owner; uint32 fuses; uint64 expiry; }
    mapping(uint256 => Name) public getData;
    function set(uint256 node, address account, uint64 expiry) external { getData[node] = Name(account, 0, expiry); }
}
