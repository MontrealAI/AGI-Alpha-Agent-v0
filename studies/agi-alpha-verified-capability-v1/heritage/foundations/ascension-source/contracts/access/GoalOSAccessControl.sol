// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/Pausable.sol";

abstract contract GoalOSAccessControl is AccessControl, Ownable, Pausable {
    bytes32 public constant PROTOCOL_ADMIN_ROLE = keccak256("PROTOCOL_ADMIN_ROLE");
    bytes32 public constant OPERATOR_ROLE = keccak256("OPERATOR_ROLE");
    bytes32 public constant REVIEWER_MANAGER_ROLE = keccak256("REVIEWER_MANAGER_ROLE");
    bytes32 public constant TREASURY_ROLE = keccak256("TREASURY_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    bytes32 public constant VAULT_MANAGER_ROLE = keccak256("VAULT_MANAGER_ROLE");
    bytes4 private constant _ERC173_INTERFACE_ID = 0x7f5828d0;

    error GoalOSDefaultAdminRoleCoupledToOwner();
    error GoalOSOwnershipRenunciationDisabled();
    error GoalOSOwnershipNoOp();
    error GoalOSOwnershipTransferPending();
    error GoalOSOwnershipTransferDelayNotElapsed();
    error GoalOSOwnerCoupledRoleRemovalDisabled();

    uint48 public constant OWNERSHIP_TRANSFER_DELAY = 1 days;

    address private _goalOSPendingOwner;
    uint48 private _goalOSPendingOwnerAcceptAfter;

    event OwnershipTransferStarted(address indexed previousOwner, address indexed newOwner);
    event GoalOSOwnershipTransferCancelled(address indexed owner, address indexed pendingOwner);
    event GoalOSOwnershipRolesMigrated(address indexed previousOwner, address indexed newOwner);

    constructor(address admin) {
        require(admin != address(0), "GOALOS_ZERO_ADMIN");
        _transferOwnership(admin);
        _grantManagedRoles(admin);
    }

    modifier onlyAdmin() {
        require(
            hasRole(DEFAULT_ADMIN_ROLE, msg.sender) || hasRole(PROTOCOL_ADMIN_ROLE, msg.sender),
            "GOALOS_NOT_ADMIN"
        );
        _;
    }

    modifier onlyOperator() {
        require(
            hasRole(DEFAULT_ADMIN_ROLE, msg.sender) || hasRole(OPERATOR_ROLE, msg.sender),
            "GOALOS_NOT_OPERATOR"
        );
        _;
    }

    function pause() external {
        require(hasRole(PAUSER_ROLE, msg.sender) || hasRole(DEFAULT_ADMIN_ROLE, msg.sender), "GOALOS_NOT_PAUSER");
        _pause();
    }

    function unpause() external {
        require(hasRole(PAUSER_ROLE, msg.sender) || hasRole(DEFAULT_ADMIN_ROLE, msg.sender), "GOALOS_NOT_PAUSER");
        _unpause();
    }

    function managedOwnershipRoleCount() public pure returns (uint256) {
        return 7;
    }

    function managedOwnershipRoleAt(uint256 index) public pure returns (bytes32) {
        if (index == 0) return DEFAULT_ADMIN_ROLE;
        if (index == 1) return PROTOCOL_ADMIN_ROLE;
        if (index == 2) return OPERATOR_ROLE;
        if (index == 3) return REVIEWER_MANAGER_ROLE;
        if (index == 4) return TREASURY_ROLE;
        if (index == 5) return PAUSER_ROLE;
        if (index == 6) return VAULT_MANAGER_ROLE;
        revert("GOALOS_ROLE_INDEX");
    }

    function transferOwnership(address newOwner) public override onlyOwner {
        require(newOwner != address(0), "Ownable: new owner is the zero address");
        address previousOwner = owner();
        if (newOwner == previousOwner) revert GoalOSOwnershipNoOp();
        _goalOSPendingOwner = newOwner;
        _goalOSPendingOwnerAcceptAfter = uint48(block.timestamp) + OWNERSHIP_TRANSFER_DELAY;
        emit OwnershipTransferStarted(previousOwner, newOwner);
    }

    function pendingOwner() public view returns (address) {
        return _goalOSPendingOwner;
    }

    function pendingOwnerAcceptAfter() public view returns (uint48) {
        return _goalOSPendingOwnerAcceptAfter;
    }

    function cancelOwnershipTransfer() public onlyOwner {
        address pending = _goalOSPendingOwner;
        if (pending == address(0)) revert GoalOSOwnershipNoOp();
        delete _goalOSPendingOwner;
        delete _goalOSPendingOwnerAcceptAfter;
        emit GoalOSOwnershipTransferCancelled(msg.sender, pending);
    }

    function acceptOwnership() public {
        address newOwner = _goalOSPendingOwner;
        if (msg.sender != newOwner) revert GoalOSOwnershipTransferPending();
        if (block.timestamp < _goalOSPendingOwnerAcceptAfter) revert GoalOSOwnershipTransferDelayNotElapsed();
        address previousOwner = owner();
        _grantManagedRoles(newOwner);
        delete _goalOSPendingOwner;
        delete _goalOSPendingOwnerAcceptAfter;
        _transferOwnership(newOwner);
        _revokeManagedRoles(previousOwner);
        emit GoalOSOwnershipRolesMigrated(previousOwner, newOwner);
    }

    function renounceOwnership() public view override onlyOwner {
        revert GoalOSOwnershipRenunciationDisabled();
    }

    function grantRole(bytes32 role, address account) public override {
        if (role == DEFAULT_ADMIN_ROLE) revert GoalOSDefaultAdminRoleCoupledToOwner();
        super.grantRole(role, account);
    }

    function revokeRole(bytes32 role, address account) public override {
        if (role == DEFAULT_ADMIN_ROLE) revert GoalOSDefaultAdminRoleCoupledToOwner();
        if (account == owner() && _isOwnerCoupledRole(role)) revert GoalOSOwnerCoupledRoleRemovalDisabled();
        super.revokeRole(role, account);
    }

    function renounceRole(bytes32 role, address account) public override {
        if (role == DEFAULT_ADMIN_ROLE) revert GoalOSDefaultAdminRoleCoupledToOwner();
        if (account == owner() && _isOwnerCoupledRole(role)) revert GoalOSOwnerCoupledRoleRemovalDisabled();
        super.renounceRole(role, account);
    }

    function supportsInterface(bytes4 interfaceId) public view virtual override returns (bool) {
        return interfaceId == _ERC173_INTERFACE_ID || super.supportsInterface(interfaceId);
    }

    function _grantManagedRoles(address account) internal {
        for (uint256 i = 0; i < managedOwnershipRoleCount(); i++) {
            _grantRole(managedOwnershipRoleAt(i), account);
        }
    }

    function _revokeManagedRoles(address account) internal {
        for (uint256 i = 0; i < managedOwnershipRoleCount(); i++) {
            _revokeRole(managedOwnershipRoleAt(i), account);
        }
    }

    function _isOwnerCoupledRole(bytes32 role) internal pure returns (bool) {
        return role == PROTOCOL_ADMIN_ROLE || role == OPERATOR_ROLE || role == REVIEWER_MANAGER_ROLE || role == TREASURY_ROLE || role == PAUSER_ROLE || role == VAULT_MANAGER_ROLE;
    }
}
