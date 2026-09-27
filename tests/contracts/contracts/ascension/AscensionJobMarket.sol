// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/access/Ownable2Step.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "./AscensionRiskOracle.sol";

/// @notice Bounded reputation-weighted auctions with locked collateral, artifact-bound review and exact payouts.
contract AscensionJobMarket is AscensionToken, Ownable2Step, ReentrancyGuard {
    using SafeERC20 for IERC20;
    enum State { None, Auction, Assigned, Submitted, Paid, Failed, Refunded }
    struct Spec { string goal; string successMetric; uint96 bounty; uint32 duration; uint16 priceWeight; }
    struct Job {
        address client;
        address business;
        address worker;
        uint96 bounty;
        uint96 price;
        uint96 bond;
        uint64 auctionEnd;
        uint64 executionEnd;
        uint64 reviewEnd;
        uint64 due;
        uint32 duration;
        uint16 priceWeight;
        uint8 yes;
        uint8 no;
        State state;
        bytes32 specHash;
        bytes32 resultHash;
        uint256 refund;
        bool claimed;
    }
    struct Bid { address agent; uint96 price; uint32 duration; uint32 reputation; }
    AscensionAccess public immutable access;
    AscensionRiskOracle public immutable oracle;
    uint256 public immutable minimumStake;
    uint32 public constant REVIEW_WINDOW = 3 days;
    uint16 public constant VALIDATOR_BPS = 500;
    uint256 public nextId;
    address public mark;
    mapping(uint256 => Job) public jobs;
    mapping(uint256 => Bid[]) private bids;
    mapping(uint256 => address[3]) public committees;
    mapping(uint256 => mapping(address => bool)) public hasBid;
    mapping(uint256 => mapping(address => uint8)) public votes;
    mapping(address => uint256) public stake;
    mapping(address => uint256) public locked;
    mapping(address => uint32) public reputation;
    event JobPosted(uint256 indexed id, address indexed business, bytes32 specHash, string goal,
        string successMetric, uint96 bounty, uint64 auctionEnd, uint64 reviewEnd);
    event BidPlaced(uint256 indexed id, address indexed agent, uint96 price, uint32 duration, uint32 reputation);
    event Assigned(uint256 indexed id, address indexed agent, uint96 price, uint64 due);
    event Delivered(uint256 indexed id, bytes32 resultHash, string resultURI);
    event Validated(uint256 indexed id, address indexed validator, bool approved, bytes32 resultHash, bytes32 evidence);
    event Payout(uint256 indexed id, address indexed recipient, uint256 gross, uint256 burned);
    event Closed(uint256 indexed id, State state, uint256 refundable);
    event RefundClaimed(uint256 indexed id, address indexed client, uint256 amount);
    event MarkBound(address indexed mark);
    event StakeChanged(address indexed agent, uint256 balance, uint256 locked);

    constructor(AscensionAccess access_, AscensionRiskOracle oracle_, uint256 minimum_, address governor)
        Ownable(governor) {
        require(minimum_ > 0 && minimum_ <= type(uint96).max, "minimum stake");
        access = access_; oracle = oracle_; minimumStake = minimum_;
    }
    function bindMark(address value) external onlyOwner {
        require(mark == address(0) && value.code.length > 0, "binding is one-time");
        mark = value; emit MarkBound(value);
    }
    function deposit(uint256 amount) external nonReentrant {
        require(amount > 0 && access.eligible(msg.sender, AscensionAccess.Role.Agent), "agent identity");
        _receive(msg.sender, amount); stake[msg.sender] += amount;
        emit StakeChanged(msg.sender, stake[msg.sender], locked[msg.sender]);
    }
    function withdraw(uint256 amount) external nonReentrant {
        require(amount > 0 && amount <= stake[msg.sender] - locked[msg.sender], "locked stake");
        stake[msg.sender] -= amount; token.safeTransfer(msg.sender, amount);
        emit StakeChanged(msg.sender, stake[msg.sender], locked[msg.sender]);
    }
    function hashSpec(uint32 index, Spec calldata spec) public pure returns (bytes32) {
        return keccak256(bytes.concat(keccak256(abi.encode(index, keccak256(bytes(spec.goal)),
            keccak256(bytes(spec.successMetric)), spec.bounty, spec.duration, spec.priceWeight))));
    }
    function post(Spec calldata spec, uint32 auctionSeconds, address[3] calldata validators)
        external nonReentrant returns (uint256) {
        return _post(msg.sender, spec, auctionSeconds, validators);
    }
    function postFromSeed(address business, Spec calldata spec, uint32 auctionSeconds, address[3] calldata validators)
        external nonReentrant returns (uint256) {
        require(msg.sender == mark, "MARK only");
        return _post(business, spec, auctionSeconds, validators);
    }
    function _post(address business, Spec calldata spec, uint32 auctionSeconds, address[3] calldata validators)
        internal returns (uint256 id) {
        require(access.eligible(business, AscensionAccess.Role.Business), "business identity");
        require(bytes(spec.goal).length > 0 && bytes(spec.goal).length <= 512 &&
            bytes(spec.successMetric).length > 0 && bytes(spec.successMetric).length <= 512, "goal and success metric");
        require(spec.bounty >= 100 && spec.duration > 0 && spec.duration <= 90 days && spec.priceWeight <= 10000,
            "job bounds");
        require(auctionSeconds > 0 && auctionSeconds <= 7 days, "auction bounds");
        id = ++nextId;
        Job storage j = jobs[id];
        j.client = msg.sender; j.business = business; j.bounty = spec.bounty;
        j.bond = uint96(spec.bounty / 10 > minimumStake ? spec.bounty / 10 : minimumStake);
        j.auctionEnd = uint64(block.timestamp + auctionSeconds);
        j.executionEnd = j.auctionEnd + spec.duration; j.reviewEnd = j.executionEnd + REVIEW_WINDOW;
        j.duration = spec.duration; j.priceWeight = spec.priceWeight;
        j.state = State.Auction; j.specHash = hashSpec(0, spec);
        for (uint256 i; i < 3; ++i) {
            address v = validators[i];
            require(v != business && v != msg.sender && oracle.isValidator(v), "independent committee");
            for (uint256 k; k < i; ++k) require(v != validators[k], "duplicate validator");
            committees[id][i] = v; oracle.lockForJob(v, business, j.reviewEnd);
        }
        _receive(msg.sender, spec.bounty);
        emit JobPosted(id, business, j.specHash, spec.goal, spec.successMetric, spec.bounty, j.auctionEnd, j.reviewEnd);
    }
    function bid(uint256 id, uint96 price, uint32 duration) external {
        Job storage j = jobs[id];
        require(j.state == State.Auction && block.timestamp < j.auctionEnd, "auction closed");
        require(access.eligible(msg.sender, AscensionAccess.Role.Agent) && msg.sender != j.business, "agent identity");
        for (uint256 i; i < 3; ++i) require(committees[id][i] != msg.sender, "validator cannot execute");
        require(price >= 100 && price <= j.bounty && duration > 0 && duration <= j.duration, "bid bounds");
        require(!hasBid[id][msg.sender] && bids[id].length < 32, "duplicate or full auction");
        require(stake[msg.sender] - locked[msg.sender] >= j.bond, "insufficient free stake");
        hasBid[id][msg.sender] = true; locked[msg.sender] += j.bond;
        bids[id].push(Bid(msg.sender, price, duration, reputation[msg.sender]));
        emit BidPlaced(id, msg.sender, price, duration, reputation[msg.sender]);
    }
    function score(uint96 price, uint32 duration, uint32 rep, uint96 bounty, uint32 maximumDuration,
        uint16 priceWeight) public pure returns (uint256) {
        require(bounty > 0 && maximumDuration > 0 && priceWeight <= 10000, "score bounds");
        uint256 cost = uint256(price) * priceWeight * 1e6 / bounty;
        uint256 time = uint256(duration) * (10000 - priceWeight) * 1e6 / maximumDuration;
        return (cost + time) * 10000 / (10000 + (rep > 10000 ? 10000 : rep));
    }
    function award(uint256 id) external {
        Job storage j = jobs[id];
        require(j.state == State.Auction && block.timestamp >= j.auctionEnd, "auction not ended");
        uint256 best = type(uint256).max;
        uint256 bestScore = type(uint256).max;
        Bid[] storage entries = bids[id];
        for (uint256 i; i < entries.length; ++i) {
            Bid storage b = entries[i];
            if (!access.eligible(b.agent, AscensionAccess.Role.Agent) || block.timestamp + b.duration > j.executionEnd)
                continue;
            uint256 s = score(b.price, b.duration, b.reputation, j.bounty, j.duration, j.priceWeight);
            if (s < bestScore || (s == bestScore && (b.price < entries[best].price ||
                (b.price == entries[best].price && (b.duration < entries[best].duration ||
                (b.duration == entries[best].duration && uint160(b.agent) < uint160(entries[best].agent))))))) {
                best = i; bestScore = s;
            }
        }
        for (uint256 i; i < entries.length; ++i) if (i != best) locked[entries[i].agent] -= j.bond;
        if (best == type(uint256).max) {
            j.state = State.Refunded; j.refund = j.bounty; _releaseCommittee(id); emit Closed(id, j.state, j.refund); return;
        }
        Bid storage winner = entries[best];
        j.worker = winner.agent; j.price = winner.price; j.due = uint64(block.timestamp + winner.duration);
        j.state = State.Assigned;
        emit Assigned(id, j.worker, j.price, j.due);
    }
    function submit(uint256 id, bytes32 resultHash, string calldata resultURI) external {
        Job storage j = jobs[id];
        require(j.state == State.Assigned && msg.sender == j.worker && block.timestamp <= j.due, "not deliverable");
        require(access.eligible(msg.sender, AscensionAccess.Role.Agent), "agent identity");
        require(resultHash != bytes32(0) && bytes(resultURI).length > 0 && bytes(resultURI).length <= 512, "result required");
        j.resultHash = resultHash; j.state = State.Submitted;
        emit Delivered(id, resultHash, resultURI);
    }
    function validate(uint256 id, bytes32 resultHash, bool approved, bytes32 evidence) external nonReentrant {
        Job storage j = jobs[id];
        require(j.state == State.Submitted && block.timestamp <= j.reviewEnd, "not reviewable");
        require(resultHash == j.resultHash && evidence != bytes32(0), "artifact binding");
        bool member;
        for (uint256 i; i < 3; ++i) if (committees[id][i] == msg.sender) member = true;
        require(member && oracle.isValidator(msg.sender), "selected validator required");
        require(votes[id][msg.sender] == 0, "duplicate vote");
        votes[id][msg.sender] = approved ? 1 : 2;
        if (approved) ++j.yes; else ++j.no;
        emit Validated(id, msg.sender, approved, resultHash, evidence);
        if (j.yes == 2) _pay(id, j);
        else if (j.no == 2) _fail(id, j, true);
    }
    function _payout(uint256 id, address recipient, uint256 gross) internal {
        uint256 burned = gross / 100;
        _burn(burned); token.safeTransfer(recipient, gross - burned);
        emit Payout(id, recipient, gross, burned);
    }
    function _releaseCommittee(uint256 id) internal {
        for (uint256 i; i < 3; ++i) oracle.releaseFromJob(committees[id][i]);
    }
    function _pay(uint256 id, Job storage j) internal {
        for (uint256 i; i < 3; ++i) if (votes[id][committees[id][i]] == 1)
            require(oracle.isValidator(committees[id][i]), "approval no longer eligible");
        _releaseCommittee(id);
        j.state = State.Paid; j.refund = j.bounty - j.price;
        locked[j.worker] -= j.bond;
        if (reputation[j.worker] < 10000) reputation[j.worker] += 1;
        uint256 each = uint256(j.price) * VALIDATOR_BPS / 10000 / 2;
        _payout(id, j.worker, j.price - 2 * each);
        for (uint256 i; i < 3; ++i) if (votes[id][committees[id][i]] == 1) _payout(id, committees[id][i], each);
        emit Closed(id, j.state, j.refund);
    }
    function _fail(uint256 id, Job storage j, bool slash) internal {
        _releaseCommittee(id);
        j.state = slash ? State.Failed : State.Refunded; j.refund = j.bounty;
        locked[j.worker] -= j.bond;
        if (slash) {
            stake[j.worker] -= j.bond;
            if (reputation[j.worker] > 0) reputation[j.worker] -= 1;
            uint256 burned = uint256(j.bond) / 100;
            _burn(burned); j.refund += j.bond - burned;
            emit Payout(id, j.client, j.bond, burned);
        }
        emit Closed(id, j.state, j.refund);
    }
    function timeout(uint256 id) external nonReentrant {
        Job storage j = jobs[id];
        if (j.state == State.Assigned) {
            require(block.timestamp > j.due, "delivery still open"); _fail(id, j, true);
        } else {
            require(j.state == State.Submitted && block.timestamp > j.reviewEnd, "review still open");
            // Missing reviewer quorum is not proof that delivered work failed.
            _fail(id, j, false);
        }
    }
    function claimRefund(uint256 id) external nonReentrant returns (uint256 amount) {
        Job storage j = jobs[id];
        require(j.client == msg.sender && terminal(id) && !j.claimed, "refund unavailable");
        j.claimed = true; amount = j.refund;
        if (amount > 0) token.safeTransfer(msg.sender, amount);
        emit RefundClaimed(id, msg.sender, amount);
    }
    function terminal(uint256 id) public view returns (bool) {
        State s = jobs[id].state; return s == State.Paid || s == State.Failed || s == State.Refunded;
    }
    function bidCount(uint256 id) external view returns (uint256) { return bids[id].length; }
}
