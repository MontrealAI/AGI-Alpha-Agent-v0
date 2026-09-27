// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/cryptography/MerkleProof.sol";
import "./AscensionJobMarket.sol";

/// @notice MARK's reversible linear-curve AMM becomes a plan-restricted Sovereign treasury at bloom.
contract AscensionMark is AscensionToken, ReentrancyGuard {
    using SafeERC20 for IERC20;
    enum Phase { None, Funding, Bloomed, Closed }
    struct Campaign {
        address business;
        uint96 base;
        uint96 slope;
        uint96 target;
        uint32 maxLots;
        uint32 supply;
        uint32 posted;
        uint32 active;
        uint32 duration;
        uint64 fundingEnd;
        uint64 executionEnd;
        uint256 reserve;
        Phase phase;
        bytes32 businessNode;
    }
    NovaSeed public immutable seed;
    AscensionAccess public immutable access;
    AscensionRiskOracle public immutable oracle;
    AscensionJobMarket public immutable jobs;
    mapping(uint256 => Campaign) public campaigns;
    mapping(uint256 => mapping(address => uint256)) public lots;
    mapping(uint256 => mapping(uint32 => bool)) public posted;
    mapping(uint256 => uint256) public jobSeed;
    mapping(uint256 => bool) public collected;
    event MarketOpened(uint256 indexed id, address indexed business, uint96 base, uint96 slope, uint96 target);
    event Traded(uint256 indexed id, address indexed account, bool buy, uint32 lots, uint256 value);
    event LotsTransferred(uint256 indexed id, address indexed from, address indexed to, uint32 count);
    event Bloomed(uint256 indexed id, bytes32 indexed businessNode, bytes32 planRoot, uint256 funding);
    event MissionRouted(uint256 indexed id, uint32 indexed index, uint256 indexed jobId, bytes32 leaf);
    event MissionCollected(uint256 indexed id, uint256 indexed jobId, uint256 refund);
    event CampaignClosed(uint256 indexed id, uint256 unused, uint32 supply);
    event CapitalReturned(uint256 indexed id, address indexed account, uint256 amount);

    constructor(NovaSeed seed_, AscensionAccess access_, AscensionRiskOracle oracle_, AscensionJobMarket jobs_) {
        seed = seed_; access = access_; oracle = oracle_; jobs = jobs_;
    }
    function open(uint256 id, uint96 base, uint96 slope, uint32 maxLots, uint96 target,
        uint64 fundingEnd, uint32 duration) external {
        require(seed.ownerOf(id) == msg.sender && oracle.green(id), "green seed owner required");
        require(campaigns[id].phase == Phase.None && base > 0 && maxLots > 0 && maxLots <= 1000000, "market bounds");
        require(target > 0 && target <= quote(0, maxLots, base, slope), "unreachable target");
        require(fundingEnd > block.timestamp && fundingEnd <= block.timestamp + 30 days &&
            duration > jobs.REVIEW_WINDOW() && duration <= 90 days, "time bounds");
        Campaign storage c = campaigns[id];
        c.business = msg.sender; c.base = base; c.slope = slope; c.target = target; c.maxLots = maxLots;
        c.fundingEnd = fundingEnd; c.duration = duration; c.phase = Phase.Funding;
        c.businessNode = access.names(msg.sender, AscensionAccess.Role.Business);
        emit MarketOpened(id, msg.sender, base, slope, target);
    }
    function quote(uint32 supply, uint32 count, uint96 base, uint96 slope) public pure returns (uint256) {
        require(uint256(supply) + count <= 1000000, "lot bound");
        return uint256(count) * base + uint256(slope) * count * (2 * uint256(supply) + count - (count > 0 ? 1 : 0)) / 2;
    }
    function buy(uint256 id, uint32 count, uint256 maxCost) external nonReentrant {
        Campaign storage c = campaigns[id];
        require(c.phase == Phase.Funding && block.timestamp < c.fundingEnd, "funding closed");
        require(access.admitted(msg.sender) && oracle.green(id) && seed.ownerOf(id) == c.business, "admission gate");
        require(count > 0 && uint256(c.supply) + count <= c.maxLots, "lot bound");
        uint256 cost = quote(c.supply, count, c.base, c.slope);
        require(cost <= maxCost, "slippage");
        _receive(msg.sender, cost); c.supply += count; c.reserve += cost; lots[id][msg.sender] += count;
        emit Traded(id, msg.sender, true, count, cost);
    }
    function sell(uint256 id, uint32 count, uint256 minReturn) external nonReentrant {
        Campaign storage c = campaigns[id];
        // Revoked admission or expired risk never prevents withdrawing unused funding.
        require(c.phase == Phase.Funding && count > 0 && lots[id][msg.sender] >= count, "not redeemable");
        uint256 value = quote(c.supply - count, count, c.base, c.slope);
        require(value >= minReturn, "slippage");
        c.supply -= count; c.reserve -= value; lots[id][msg.sender] -= count;
        token.safeTransfer(msg.sender, value); emit Traded(id, msg.sender, false, count, value);
    }
    function transferLots(uint256 id, address to, uint32 count) external {
        Campaign storage c = campaigns[id];
        require(c.phase == Phase.Funding && block.timestamp < c.fundingEnd && oracle.green(id) &&
            seed.ownerOf(id) == c.business, "funding closed");
        require(access.admitted(msg.sender) && access.admitted(to) && to != address(0), "admission gate");
        require(count > 0 && lots[id][msg.sender] >= count, "insufficient lots");
        lots[id][msg.sender] -= count; lots[id][to] += count;
        emit LotsTransferred(id, msg.sender, to, count);
    }
    function bloom(uint256 id) external {
        Campaign storage c = campaigns[id];
        require(c.phase == Phase.Funding && block.timestamp < c.fundingEnd && c.reserve >= c.target, "not funded");
        require(msg.sender == c.business && seed.ownerOf(id) == c.business && oracle.green(id), "green business required");
        require(access.owns(c.business, c.businessNode), "business ENS changed");
        c.phase = Phase.Bloomed; c.executionEnd = uint64(block.timestamp + c.duration);
        (bytes32 root,) = seed.plan(id);
        emit Bloomed(id, c.businessNode, root, c.reserve);
    }
    function route(uint256 id, uint32 index, AscensionJobMarket.Spec calldata spec, bytes32[] calldata proof,
        uint32 auctionSeconds, address[3] calldata validators) external nonReentrant returns (uint256 jobId) {
        Campaign storage c = campaigns[id];
        require(c.phase == Phase.Bloomed && msg.sender == c.business && access.owns(msg.sender, c.businessNode), "business authority");
        require(seed.ownerOf(id) == c.business && oracle.green(id), "green business required");
        require(block.timestamp + auctionSeconds + spec.duration + jobs.REVIEW_WINDOW() <= c.executionEnd, "execution horizon");
        (bytes32 root, uint32 count) = seed.plan(id);
        bytes32 leaf = jobs.hashSpec(index, spec);
        require(index < count && !posted[id][index] && MerkleProof.verify(proof, root, leaf), "FusionPlan proof");
        require(c.reserve >= spec.bounty, "treasury budget");
        posted[id][index] = true; c.posted++; c.active++; c.reserve -= spec.bounty;
        token.forceApprove(address(jobs), spec.bounty);
        jobId = jobs.postFromSeed(c.business, spec, auctionSeconds, validators);
        token.forceApprove(address(jobs), 0);
        jobSeed[jobId] = id;
        emit MissionRouted(id, index, jobId, leaf);
    }
    function collect(uint256 jobId) external nonReentrant {
        uint256 id = jobSeed[jobId];
        require(id != 0 && !collected[jobId] && jobs.terminal(jobId), "not collectible");
        collected[jobId] = true;
        Campaign storage c = campaigns[id]; c.active--;
        uint256 amount = jobs.claimRefund(jobId); c.reserve += amount;
        emit MissionCollected(id, jobId, amount);
    }
    function close(uint256 id) external {
        Campaign storage c = campaigns[id];
        (, uint32 count) = seed.plan(id);
        if (c.phase == Phase.Funding) require(block.timestamp >= c.fundingEnd, "funding still open");
        else require(c.phase == Phase.Bloomed && c.active == 0 &&
            (c.posted == count || block.timestamp > c.executionEnd), "missions still open");
        c.phase = Phase.Closed; emit CampaignClosed(id, c.reserve, c.supply);
    }
    function reclaim(uint256 id) external nonReentrant returns (uint256 amount) {
        Campaign storage c = campaigns[id]; uint256 count = lots[id][msg.sender];
        require(c.phase == Phase.Closed && count > 0, "no capital claim");
        amount = c.reserve * count / c.supply;
        lots[id][msg.sender] = 0; c.supply -= uint32(count); c.reserve -= amount;
        if (amount > 0) token.safeTransfer(msg.sender, amount);
        emit CapitalReturned(id, msg.sender, amount);
    }
}
