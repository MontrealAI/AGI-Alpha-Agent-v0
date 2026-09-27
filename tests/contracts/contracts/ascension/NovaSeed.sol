// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "./AscensionAccess.sol";

/// @notice Transferable ERC-721 binding an encrypted capsule, immutable FusionPlan and optional successor lineage.
contract NovaSeed is ERC721URIStorage {
    struct Genome {
        bytes32 capsuleHash;
        bytes32 planRoot;
        bytes32 evidenceHash;
        uint256 parent;
        uint32 jobs;
        address creator;
    }
    AscensionAccess public immutable access;
    uint256 public nextId;
    mapping(uint256 => Genome) public genomes;
    event SeedSealed(uint256 indexed seedId, address indexed creator, bytes32 capsuleHash,
        bytes32 planRoot, uint256 parent, bytes32 evidenceHash);

    constructor(AscensionAccess access_) ERC721("Alpha AGI Nova-Seeds", "NOVA") { access = access_; }

    function seal(bytes32 capsuleHash, bytes32 planRoot, uint32 jobs, string calldata metadataURI,
        uint256 parent, bytes32 evidenceHash) external returns (uint256 id) {
        require(access.eligible(msg.sender, AscensionAccess.Role.Business), "business identity");
        require(capsuleHash != bytes32(0) && planRoot != bytes32(0) && evidenceHash != bytes32(0), "empty commitment");
        require(jobs > 0 && jobs <= 128, "job bound");
        require(bytes(metadataURI).length > 0 && bytes(metadataURI).length <= 512, "metadata URI");
        if (parent != 0) require(ownerOf(parent) == msg.sender, "parent ownership");
        id = ++nextId;
        genomes[id] = Genome(capsuleHash, planRoot, evidenceHash, parent, jobs, msg.sender);
        // State and URI are complete before an ERC-721 receiver can be invoked.
        _mint(msg.sender, id);
        _setTokenURI(id, metadataURI);
        emit SeedSealed(id, msg.sender, capsuleHash, planRoot, parent, evidenceHash);
    }
    function plan(uint256 id) external view returns (bytes32 root, uint32 count) {
        ownerOf(id);
        Genome storage genome = genomes[id];
        return (genome.planRoot, genome.jobs);
    }
    function creatorOf(uint256 id) external view returns (address) { ownerOf(id); return genomes[id].creator; }
}
