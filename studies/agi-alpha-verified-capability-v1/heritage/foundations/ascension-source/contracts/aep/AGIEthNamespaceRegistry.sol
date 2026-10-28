// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "../access/GoalOSAccessControl.sol";

contract AGIEthNamespaceRegistry is GoalOSAccessControl {
    enum NamespaceStatus { None, PreAlpha, Active, Paused, Deprecated, Quarantined }
    struct EnvironmentRecord { bytes32 envHash; bytes32 rootNameHash; bytes32 agentMountHash; bytes32 nodeMountHash; bytes32 clubMountHash; bytes32 policyVersionHash; bytes32 resolverPolicyHash; NamespaceStatus status; string metadataURI; uint256 createdAt; }
    mapping(bytes32 => EnvironmentRecord) public environments;
    event EnvironmentRegistered(bytes32 indexed envHash, bytes32 indexed rootNameHash, NamespaceStatus status, string metadataURI);
    event EnvironmentStatusUpdated(bytes32 indexed envHash, NamespaceStatus status, bytes32 indexed reasonHash);
    constructor(address admin) GoalOSAccessControl(admin) {}
    function registerEnvironment(bytes32 envHash, bytes32 rootNameHash, bytes32 agentMountHash, bytes32 nodeMountHash, bytes32 clubMountHash, bytes32 policyVersionHash, bytes32 resolverPolicyHash, NamespaceStatus status, string calldata metadataURI) external onlyOperator {
        require(envHash != bytes32(0), "NS_ZERO_ENV");
        require(environments[envHash].createdAt == 0, "NS_EXISTS");
        environments[envHash] = EnvironmentRecord(envHash, rootNameHash, agentMountHash, nodeMountHash, clubMountHash, policyVersionHash, resolverPolicyHash, status, metadataURI, block.timestamp);
        emit EnvironmentRegistered(envHash, rootNameHash, status, metadataURI);
    }
    function setEnvironmentStatus(bytes32 envHash, NamespaceStatus status, bytes32 reasonHash) external onlyOperator {
        require(environments[envHash].createdAt != 0, "NS_NOT_FOUND");
        environments[envHash].status = status;
        emit EnvironmentStatusUpdated(envHash, status, reasonHash);
    }
}
