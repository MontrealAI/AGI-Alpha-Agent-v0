// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable2Step.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

interface IAscensionENS { function owner(bytes32 node) external view returns (address); }
interface IAscensionWrapper {
    function getData(uint256 node) external view returns (address owner, uint32 fuses, uint64 expiry);
}

/// @notice Live ENS ownership plus expiring, attributable admission decisions. No resolver-address bypass.
contract AscensionAccess is Ownable2Step {
    enum Role { Business, Agent, Validator }
    struct Admission { bytes32 evidence; uint64 until; }
    IAscensionENS public immutable ens;
    IAscensionWrapper public immutable wrapper;
    mapping(Role => bytes32) public roots;
    mapping(address => mapping(Role => bytes32)) public names;
    mapping(address => Admission) public admission;
    event Registered(address indexed account, Role indexed role, bytes32 indexed node, string label);
    event AdmissionSet(address indexed account, bytes32 evidence, uint64 until);

    constructor(address ens_, address wrapper_, address governor) Ownable(governor) {
        require(ens_.code.length > 0, "ENS contract required");
        require(wrapper_ == address(0) || wrapper_.code.length > 0, "wrapper contract required");
        ens = IAscensionENS(ens_);
        wrapper = IAscensionWrapper(wrapper_);
        bytes32 agi = child(child(bytes32(0), "eth"), "agi");
        roots[Role.Business] = child(agi, "alpha");
        roots[Role.Agent] = child(child(agi, "agent"), "alpha");
        roots[Role.Validator] = child(child(agi, "club"), "alpha");
    }

    function child(bytes32 parent, string memory label) public pure returns (bytes32) {
        return keccak256(abi.encodePacked(parent, keccak256(bytes(label))));
    }

    function register(Role role, string calldata label) external {
        bytes memory raw = bytes(label);
        require(raw.length > 0 && raw.length <= 63, "single ASCII label required");
        for (uint256 i; i < raw.length; ++i) {
            bytes1 c = raw[i];
            require((c >= 0x61 && c <= 0x7a) || (c >= 0x30 && c <= 0x39) ||
                (c == 0x2d && i > 0 && i + 1 < raw.length), "noncanonical label");
        }
        bytes32 node = child(roots[role], label);
        require(owns(msg.sender, node), "ENS ownership required");
        names[msg.sender][role] = node;
        emit Registered(msg.sender, role, node, label);
    }

    function owns(address account, bytes32 node) public view returns (bool) {
        if (account == address(0) || node == bytes32(0)) return false;
        try ens.owner(node) returns (address holder) {
            if (holder == account) return true;
            if (holder != address(wrapper) || address(wrapper) == address(0)) return false;
            try wrapper.getData(uint256(node)) returns (address wrappedOwner, uint32, uint64 expiry) {
                return wrappedOwner == account && expiry > block.timestamp;
            } catch { return false; }
        } catch { return false; }
    }

    function setAdmission(address account, bytes32 evidence, uint64 until) external onlyOwner {
        require(account != address(0), "zero account");
        require(until == 0 || (evidence != bytes32(0) && until > block.timestamp &&
            until <= block.timestamp + 365 days), "invalid admission");
        admission[account] = Admission(evidence, until);
        emit AdmissionSet(account, evidence, until);
    }

    function admitted(address account) public view returns (bool) {
        return admission[account].until > block.timestamp;
    }

    function eligible(address account, Role role) public view returns (bool) {
        return admitted(account) && owns(account, names[account][role]);
    }
}
