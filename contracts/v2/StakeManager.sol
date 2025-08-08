// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/// @title StakeManager
/// @notice Handles staking and escrow of AGI tokens for jobs and validators
contract StakeManager is Ownable {
    IERC20 public agiToken;
    address public treasury;
    address public jobRegistry;
    address public slasher;

    // Total available stakes for each user
    mapping(address => uint256) public stakes;

    event StakeDeposited(address indexed user, uint256 amount);
    event StakeWithdrawn(address indexed user, uint256 amount);
    event FundsLocked(address indexed user, uint256 amount);
    event FundsReleased(address indexed user, uint256 amount);
    event StakeSlashed(
        address indexed offender,
        address indexed employer,
        uint256 amount,
        uint256 compensation,
        uint256 burned
    );

    constructor(address _token, address _treasury) Ownable(msg.sender) {
        agiToken = IERC20(_token);
        treasury = _treasury;
    }

    /// @notice Updates the AGI token address
    /// @param _token New token address
    function setToken(address _token) external onlyOwner {
        agiToken = IERC20(_token);
    }

    /// @notice Updates the treasury address
    /// @param _treasury New treasury address
    function setTreasury(address _treasury) external onlyOwner {
        treasury = _treasury;
    }

    /// @notice Sets the JobRegistry authorized to lock and release funds
    function setJobRegistry(address _registry) external onlyOwner {
        jobRegistry = _registry;
    }

    /// @notice Sets the contract allowed to slash stakes
    function setSlasher(address _slasher) external onlyOwner {
        slasher = _slasher;
    }

    /// @notice Deposits AGI tokens as stake
    /// @param amount Amount of tokens to deposit
    function depositStake(uint256 amount) external {
        require(amount > 0, "amount 0");
        agiToken.transferFrom(msg.sender, address(this), amount);
        stakes[msg.sender] += amount;
        emit StakeDeposited(msg.sender, amount);
    }

    /// @notice Withdraws available stake
    /// @param amount Amount of tokens to withdraw
    function withdrawStake(uint256 amount) external {
        require(stakes[msg.sender] >= amount, "insufficient");
        stakes[msg.sender] -= amount;
        agiToken.transfer(msg.sender, amount);
        emit StakeWithdrawn(msg.sender, amount);
    }

    modifier onlyJobRegistry() {
        require(msg.sender == jobRegistry, "not registry");
        _;
    }

    /// @notice Locks client funds for a job
    /// @param user Address whose stake is locked
    /// @param amount Amount to lock
    function lockJobFunds(address user, uint256 amount) public onlyJobRegistry {
        require(stakes[user] >= amount, "insufficient");
        stakes[user] -= amount;
        emit FundsLocked(user, amount);
    }

    /// @notice Releases locked funds to a worker
    /// @param user Address receiving the funds
    /// @param amount Amount to release
    function releaseJobFunds(address user, uint256 amount) public onlyJobRegistry {
        agiToken.transfer(user, amount);
        emit FundsReleased(user, amount);
    }

    modifier onlySlasher() {
        require(msg.sender == slasher, "not slasher");
        _;
    }

    /// @notice Slashes a user's stake and compensates an employer
    /// @param offender Address whose stake is slashed
    /// @param employer Address receiving compensation
    /// @param amount Total amount to slash
    function slash(address offender, address employer, uint256 amount)
        external
        onlySlasher
    {
        require(stakes[offender] >= amount, "insufficient");
        stakes[offender] -= amount;
        uint256 compensation = amount / 2;
        uint256 burnAmount = amount - compensation;
        if (compensation > 0) {
            agiToken.transfer(employer, compensation);
        }
        if (burnAmount > 0) {
            if (treasury == address(0)) {
                agiToken.transfer(address(0), burnAmount);
            } else {
                agiToken.transfer(treasury, burnAmount);
            }
        }
        emit StakeSlashed(offender, employer, amount, compensation, burnAmount);
    }
}

