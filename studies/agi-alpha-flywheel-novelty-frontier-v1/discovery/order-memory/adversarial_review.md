# Independent implementation review — order-memory erasure study

**Disposition: accept the finite mathematical result; reject novelty, physical-performance and AI-superiority inferences.** A separately written bitset decoder verified every one of the 198,840 saved five- and six-event erasure cases, with zero disagreements. Source, configuration and uncompressed case-stream hashes match the recorded values. The review also verified 24,000 one-erasure cases for a duplicated-comparison reference and generated additional mixed-fault counterexamples.

This is an independently implemented check by another assistant research process. It is not an external laboratory, a human-expert search trial, or a statistically independent model-family evaluation.

## Correct claims

Every named event occurs exactly once, so a history is a permutation. With `m=n(n−1)/2` complete pairwise comparisons, all noiseless histories have distinct encodings. If a single pairwise comparison is erased, two histories remain indistinguishable precisely when that pair was adjacent in the total order: exchanging neighboring events changes that comparator and no other. Each history has `n−1` such pairs. Therefore the total ambiguity count is `n!·(n−1)` and the average fraction of recoverable single-comparison erasures is `1−2/n`.

The study's numbers agree: five events give 480 ambiguous cases out of 1,200; six events give 3,600 out of 10,800. Every history has an adversarial erasure. The improvement cannot be summarized solely by the average recovery rate.

Appending one XOR bit produces an even-parity code. If one known coordinate is erased and all remaining coordinates are correct, it is recovered as the XOR of the known coordinates. This includes erasure of the parity coordinate itself. All 1,320 five-event and 11,520 six-event one-erasure cases recover uniquely. The ordinary library with identical information ties on all 12,840 cases. There is no retained-Alpha superiority here.

One bit substitution changes parity, so every such substitution is detected. A code distance of two does not permit unique correction of one unknown bit substitution. The author's equal-distance adjacent-transposition witness is valid.

## Duplicate reference: class restriction is essential

The `2m` storage lower bound is correct **within the class in which every stored bit is a direct copy of one particular pairwise comparison**. If any unordered pair has at most one copy, choose a permutation in which the pair is adjacent; erase its sole stored comparison. Swapping the pair cannot change any remaining observation. Thus two copies of each pair are necessary in that restricted class; duplicating every pair is also sufficient.

It is not a lower bound for arbitrary codes, arbitrary sensors, continuous measurements, mechanical parts, couplers or whole devices. The XOR code itself lies outside that direct-pairwise-observer class. In particular, 11 encoded bits versus 20 duplicated comparison bits does not demonstrate an 11-part versus 20-part mechanical device, lower manufacturing cost, lower energy or a smaller physical recorder. Computing, maintaining and reading the parity may dominate those resources.

The review exercised all 24,000 duplicated-reference cases at n=5 and n=6 and recovered the correct pairwise record after every single erasure.

## Preserved failures and added attacks

The author preserves all two-erasure cases. At n=5, 1,560 of 6,600 parity-code cases remain ambiguous. At n=6, 13,680 of 86,400 remain ambiguous. Every history remains vulnerable to at least one two-erasure pattern.

Two additional fault classes show why the single-erasure assumption must stay next to any reliability claim:

| Actual history | Fault | Decoder outcome | Interpretation |
|---|---|---|---|
| ABCDE | Erase parity; flip A-versus-B bit | BACDE, uniquely | Silent wrong recovery under an erasure plus a substitution |
| ABCDEF | Erase parity; flip A-versus-B bit | BACDEF, uniquely | Same failure at six events |
| ABCDE | Flip A-versus-B and A-versus-C bits | BCADE, uniquely; parity passes | Two substitutions can map directly to another valid codeword |
| ABCDEF | Flip A-versus-B and A-versus-C bits | BCADEF, uniquely; parity passes | Same failure at six events |

These are outside the promised fault model and do not refute its theorem. They prevent the broader claims that parity makes the record generally reliable, detects all corruptions, or corrects unknown errors.

## Freeze, reuse and evaluation interpretation

The source hash is `d964d42b80b1d5253daabc2e823c2d8c90fac43fc7c89fffa317ba00d11afe00`. The configuration hash is `2f6e9368caeef616c3a443848e66a98cf59a04224eb5b03537f424f77cce9e79`. The verified uncompressed case stream hash is `7aab69ed0bb22afd6ebb5ad54393d7b633156b7c2e8df64b5fea04f9b7b60e17`.

The freeze correctly states that n=4 exploration and the general parity theorem were already known before n=5/6 enumeration. Those new sizes are useful implementation checks, but they are not hidden scientific discoveries, evidence of prospective foresight, or proof of adaptation by a learned specialist. No parameter fitting occurs, and the formula is generic. Ordinary library reuse passes the same tests.

The naming `new_validation_sizes` is preferable to a broad claim of held-out learning. If the paper uses “held out,” it must say exactly that these sizes were not enumerated before the freeze, while the general solution was already derived. Cryptographic hashes attest to file content and recorded workflow; they do not independently prove that no actor had seen an answer.

## Review mechanics

The author decodes by constructing a precedence DAG, enumerating topological orders, and checking inversion parity. The review builds all candidate histories once, computes their comparison codewords directly, then creates a bitset of compatible histories for each observation coordinate and value. Decoding becomes intersection of bitsets for all non-erased observations. The recovered history sets were compared against every saved case, including ambiguous cases. The review implementation is at `../frontier_research/order_transfer_review.py`; machine-readable review output is `adversarial_review_results.json`.

No source edits were made to the frozen study. No model benchmark, human labor performance, material fabrication, commercial receipt or physical error rate was inferred. The study's existing interpretation fields are appropriately scoped.

## Required wording in the paper

Use “exhaustive abstract one-erasure recovery, under exact-once events and correct surviving bits.” Use “ordinary coding construction” and “technical reuse with conventional parity.” Do not promote bit counts into device counts, tests into customer acceptance, finite checks into real-world reliability, or the inherited formula into learned independent competence. The initial brief did not specify this application, but that alone does not make the well-known solution a substantive advance beyond prior art.
