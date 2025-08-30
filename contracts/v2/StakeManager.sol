// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/IERC20Metadata.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import "./Constants.sol";

/// @title StakeManager
/// @notice Handles staking and escrow of AGI tokens for jobs and validators
contract StakeManager is Ownable {
    IERC20 public agiToken;
    address public treasury;
    address public jobRegistry;
    address public slasher;

    enum Role {
        Agent,
        Employer,
        Validator
    }

    mapping(address => uint256) public agentStakes;
    mapping(address => uint256) public employerStakes;
    mapping(address => uint256) public validatorStakes;

    uint256 public minStakeAgent;
    uint256 public minStakeEmployer;
    uint256 public minStakeValidator;

    uint256 public feePct; // basis points
    uint256 public burnPct; // basis points

    mapping(address => uint256) public agiTypePayoutPct;
    address[] public agiTypes;
    mapping(uint256 => uint256) public jobEscrows;

    event StakeDeposited(address indexed user, Role role, uint256 amount);
    event StakeWithdrawn(address indexed user, Role role, uint256 amount);
    event FundsLocked(uint256 indexed jobId, address indexed employer, uint256 amount);
    event FundsReleased(
        uint256 indexed jobId,
        address indexed recipient,
        uint256 amount,
        uint256 fee,
        uint256 burn
    );
    event StakeSlashed(
        uint256 indexed jobId,
        address indexed offender,
        address indexed employer,
        uint256 amount,
        uint256 compensation,
        uint256 burned
    );

    constructor(address _treasury) Ownable(msg.sender) {
        agiToken = IERC20(Constants.AGIALPHA); // uses $AGIALPHA (18 decimals)
        treasury = _treasury;
        require(
            IERC20Metadata(Constants.AGIALPHA).decimals() == Constants.AGIALPHA_DECIMALS,
            "wrong decimals"
        );
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

    /// @notice Sets minimum stake for agents
    function setMinStakeAgent(uint256 amount) external onlyOwner {
        minStakeAgent = amount;
    }

    /// @notice Sets minimum stake for employers
    function setMinStakeEmployer(uint256 amount) external onlyOwner {
        minStakeEmployer = amount;
    }

    /// @notice Sets minimum stake for validators
    function setMinStakeValidator(uint256 amount) external onlyOwner {
        minStakeValidator = amount;
    }

    /// @notice Sets protocol fee percentage in basis points
    function setFeePct(uint256 pct) external onlyOwner {
        require(pct <= 10_000, "pct too high");
        feePct = pct;
    }

    /// @notice Sets burn percentage in basis points
    function setBurnPct(uint256 pct) external onlyOwner {
        require(pct <= 10_000, "pct too high");
        burnPct = pct;
    }

    /// @notice Adds an AGI type NFT and its payout percentage
    function addAGIType(address nft, uint256 payoutPct) external onlyOwner {
        agiTypePayoutPct[nft] = payoutPct;
        agiTypes.push(nft);
    }

    /// @notice Removes an AGI type NFT
    function removeAGIType(address nft) external onlyOwner {
        delete agiTypePayoutPct[nft];
        for (uint256 i = 0; i < agiTypes.length; i++) {
            if (agiTypes[i] == nft) {
                agiTypes[i] = agiTypes[agiTypes.length - 1];
                agiTypes.pop();
                break;
            }
        }
    }

    /// @notice Deposits AGI tokens as stake for a specific role
    function depositStake(Role role, uint256 amount) external {
        require(amount > 0, "amount 0");
        agiToken.transferFrom(msg.sender, address(this), amount);
        if (role == Role.Agent) {
            uint256 newStake = agentStakes[msg.sender] + amount;
            require(newStake >= minStakeAgent, "below min");
            agentStakes[msg.sender] = newStake;
        } else if (role == Role.Employer) {
            uint256 newStake = employerStakes[msg.sender] + amount;
            require(newStake >= minStakeEmployer, "below min");
            employerStakes[msg.sender] = newStake;
        } else {
            uint256 newStake = validatorStakes[msg.sender] + amount;
            require(newStake >= minStakeValidator, "below min");
            validatorStakes[msg.sender] = newStake;
        }
        emit StakeDeposited(msg.sender, role, amount);
    }

    /// @notice Withdraws available stake for a specific role
    function withdrawStake(Role role, uint256 amount) external {
        require(amount > 0, "amount 0");
        if (role == Role.Agent) {
            require(agentStakes[msg.sender] >= amount, "insufficient");
            uint256 remaining = agentStakes[msg.sender] - amount;
            require(remaining == 0 || remaining >= minStakeAgent, "below min");
            agentStakes[msg.sender] = remaining;
        } else if (role == Role.Employer) {
            require(employerStakes[msg.sender] >= amount, "insufficient");
            uint256 remaining = employerStakes[msg.sender] - amount;
            require(remaining == 0 || remaining >= minStakeEmployer, "below min");
            employerStakes[msg.sender] = remaining;
        } else {
            require(validatorStakes[msg.sender] >= amount, "insufficient");
            uint256 remaining = validatorStakes[msg.sender] - amount;
            require(remaining == 0 || remaining >= minStakeValidator, "below min");
            validatorStakes[msg.sender] = remaining;
        }
        agiToken.transfer(msg.sender, amount);
        emit StakeWithdrawn(msg.sender, role, amount);
    }

    modifier onlyJobRegistry() {
        require(msg.sender == jobRegistry, "not registry");
        _;
    }

    /// @notice Locks employer funds for a job
    function lock(uint256 jobId, address employer, uint256 amount) public onlyJobRegistry {
        require(jobEscrows[jobId] == 0, "escrow exists");
        agiToken.transferFrom(employer, address(this), amount);
        jobEscrows[jobId] = amount;
        emit FundsLocked(jobId, employer, amount);
    }

    /// @notice Releases locked funds applying fees, burns and validator rewards
    function release(
        uint256 jobId,
        address recipient,
        address[] calldata validators,
        uint256 validatorPct
    ) public onlyJobRegistry {
        uint256 amount = jobEscrows[jobId];
        require(amount > 0, "no escrow");
        delete jobEscrows[jobId];

        uint256 fee = (amount * feePct) / 10_000;
        uint256 burn = (amount * burnPct) / 10_000;
        uint256 net = amount - fee - burn;

        uint256 validatorReward = (net * validatorPct) / 100;
        uint256 perValidator = validators.length > 0 ? validatorReward / validators.length : 0;
        uint256 payout = net - (perValidator * validators.length);

        uint256 pct = 10_000;
        for (uint256 i = 0; i < agiTypes.length; i++) {
            address nft = agiTypes[i];
            if (agiTypePayoutPct[nft] > pct && IERC721(nft).balanceOf(recipient) > 0) {
                pct = agiTypePayoutPct[nft];
            }
        }
        payout = (payout * pct) / 10_000;

        if (fee > 0) agiToken.transfer(treasury, fee);
        if (burn > 0) agiToken.transfer(address(0), burn);
        for (uint256 i = 0; i < validators.length; i++) {
            if (perValidator > 0) agiToken.transfer(validators[i], perValidator);
        }
        agiToken.transfer(recipient, payout);

        emit FundsReleased(jobId, recipient, payout, fee, burn);
    }

    modifier onlySlasher() {
        require(msg.sender == slasher, "not slasher");
        _;
    }

    /// @notice Slashes a user's stake and compensates an employer
    function slash(
        address offender,
        address employer,
        uint256 amount,
        uint256 burnPctOverride,
        uint256 jobId
    ) external onlySlasher {
        uint256 available = validatorStakes[offender];
        if (available >= amount) {
            validatorStakes[offender] = available - amount;
        } else {
            require(agentStakes[offender] >= amount, "insufficient");
            agentStakes[offender] -= amount;
        }
        uint256 pct = burnPctOverride > 0 ? burnPctOverride : burnPct;
        uint256 burnAmount = (amount * pct) / 10_000;
        uint256 compensation = amount - burnAmount;
        if (compensation > 0 && employer != address(0)) {
            agiToken.transfer(employer, compensation);
        }
        if (burnAmount > 0) {
            agiToken.transfer(address(0), burnAmount);
        }
        emit StakeSlashed(jobId, offender, employer, amount, compensation, burnAmount);
    }
}

