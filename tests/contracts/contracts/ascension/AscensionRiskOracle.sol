// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable2Step.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "./NovaSeed.sol";
import "./AscensionToken.sol";

interface IAscensionJobBinding {
    function oracle() external view returns (address);
    function access() external view returns (address);
}

/// @notice Staked, live-ENS validators attest to a specific seed owner and immutable plan; approvals expire.
contract AscensionRiskOracle is AscensionToken, Ownable2Step, ReentrancyGuard {
    using SafeERC20 for IERC20;
    struct Round { uint64 number; uint64 until; uint16 yes; uint16 no; address owner; }
    AscensionAccess public immutable access;
    NovaSeed public immutable seed;
    uint256 public immutable minimumStake;
    uint16 public immutable quorum;
    uint16 public immutable maximumRiskBps;
    address public marketplace;
    mapping(address => uint256) public stake;
    mapping(address => uint64) public lockedUntil;
    mapping(address => mapping(address => uint64)) public jobAvailability;
    mapping(address => uint32) public jobCapacity;
    mapping(address => uint32) public activeJobs;
    mapping(uint256 => Round) public rounds;
    mapping(uint256 => mapping(uint64 => mapping(address => bool))) public voted;
    mapping(uint256 => mapping(uint64 => address[])) private supporters;
    event ReviewOpened(uint256 indexed seedId, uint64 round, address owner, uint64 until);
    event RiskAttested(uint256 indexed seedId, uint64 round, address indexed validator,
        uint16 riskBps, bool admitted, bytes32 evidenceHash);
    event StakeChanged(address indexed validator, uint256 balance);
    event JobAvailability(address indexed validator, address indexed business, uint64 until, uint32 capacity);
    event MarketplaceBound(address indexed marketplace);

    constructor(AscensionAccess access_, NovaSeed seed_, uint256 minimum_, uint16 quorum_, uint16 risk_,
        address governor) Ownable(governor) {
        require(minimum_ > 0 && quorum_ >= 2 && quorum_ <= 15 && risk_ <= 10000, "oracle parameters");
        require(address(seed_.access()) == address(access_), "seed/access mismatch");
        access = access_; seed = seed_; minimumStake = minimum_; quorum = quorum_; maximumRiskBps = risk_;
    }
    function bindMarketplace(address value) external onlyOwner {
        require(marketplace == address(0) && value.code.length > 0, "binding is one-time");
        require(IAscensionJobBinding(value).oracle() == address(this) &&
            IAscensionJobBinding(value).access() == address(access), "marketplace/oracle mismatch");
        marketplace = value;
        emit MarketplaceBound(value);
    }
    function deposit(uint256 amount) external nonReentrant {
        require(amount > 0 && access.eligible(msg.sender, AscensionAccess.Role.Validator), "validator identity");
        _receive(msg.sender, amount); stake[msg.sender] += amount;
        emit StakeChanged(msg.sender, stake[msg.sender]);
    }
    function withdraw(uint256 amount) external nonReentrant {
        require(block.timestamp > lockedUntil[msg.sender] && amount > 0 && amount <= stake[msg.sender], "locked stake");
        stake[msg.sender] -= amount; token.safeTransfer(msg.sender, amount);
        emit StakeChanged(msg.sender, stake[msg.sender]);
    }
    function isValidator(address account) public view returns (bool) {
        return stake[account] >= minimumStake && access.eligible(account, AscensionAccess.Role.Validator);
    }
    function setJobAvailability(address business, uint64 until, uint32 capacity) external {
        require(business != address(0) && (until == 0 || (until > block.timestamp &&
            until <= block.timestamp + 120 days)) && capacity <= 128, "availability bounds");
        jobAvailability[msg.sender][business] = until; jobCapacity[msg.sender] = capacity;
        emit JobAvailability(msg.sender, business, until, capacity);
    }
    function releaseFromJob(address validator) external {
        require(msg.sender == marketplace && activeJobs[validator] > 0, "marketplace lock required");
        activeJobs[validator]--;
    }
    function lockForJob(address validator, address business, uint64 until) external {
        require(msg.sender == marketplace, "marketplace only");
        require(isValidator(validator) && until > block.timestamp && until <= block.timestamp + 120 days, "validator lock");
        require(jobAvailability[validator][business] >= until && activeJobs[validator] < jobCapacity[validator],
            "review capacity not reserved");
        activeJobs[validator]++;
        if (until > lockedUntil[validator]) lockedUntil[validator] = until;
    }
    function openReview(uint256 id) external {
        require(seed.ownerOf(id) == msg.sender && access.eligible(msg.sender, AscensionAccess.Role.Business), "seed owner");
        Round storage r = rounds[id];
        require(r.until < block.timestamp, "review still active");
        r.number++; r.until = uint64(block.timestamp + 7 days); r.yes = 0; r.no = 0; r.owner = msg.sender;
        emit ReviewOpened(id, r.number, msg.sender, r.until);
    }
    function attest(uint256 id, uint16 riskBps, bool policyApproved, bytes32 evidenceHash) external {
        Round storage r = rounds[id];
        require(r.until > block.timestamp && r.owner == seed.ownerOf(id), "review expired or transferred");
        require(r.yes < quorum && r.no < quorum, "review decided");
        require(isValidator(msg.sender) && msg.sender != r.owner && msg.sender != seed.creatorOf(id), "independent validator");
        require(!voted[id][r.number][msg.sender], "duplicate vote");
        require(riskBps <= 10000 && evidenceHash != bytes32(0), "attestation required");
        voted[id][r.number][msg.sender] = true;
        if (r.until > lockedUntil[msg.sender]) lockedUntil[msg.sender] = r.until;
        bool yes = policyApproved && riskBps <= maximumRiskBps;
        if (yes) { r.yes++; supporters[id][r.number].push(msg.sender); } else { r.no++; }
        emit RiskAttested(id, r.number, msg.sender, riskBps, yes, evidenceHash);
    }
    function green(uint256 id) external view returns (bool) {
        Round storage r = rounds[id];
        if (r.until <= block.timestamp || r.yes < quorum || r.owner != seed.ownerOf(id) ||
            !access.eligible(r.owner, AscensionAccess.Role.Business)) return false;
        address[] storage signers = supporters[id][r.number];
        for (uint256 i; i < signers.length; ++i) if (!isValidator(signers[i])) return false;
        return true;
    }
}
