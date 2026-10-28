# Independent mathematical check and acceptance design

Same-session checker role. This is not institutional independence or an external peer review. The checker uses its own direct graph constructors and integer multiplication; it imports no primary construction algorithm.

## Precise claim

The two specified 16-node uniform diffusion models cannot be distinguished by any input waveform through the original node-0 input/output interface. After aligning their root neighborhoods, adding arbitrary actuators alone while keeping node 0 as the sole sensor also cannot distinguish them; adding arbitrary sensors alone while keeping node 0 as the sole actuator cannot distinguish them. A suitable joint actuator/sensor addition makes discrimination possible, including under the stated independent nuisance-parameter and measurement-error bounds.

This is an exact statement about known model alternatives and permitted access. It is not a new graph-theory discovery, a physical measurement, an assertion that real thermal systems have perfectly uniform parameters, or evidence of market demand.

## Proof

Let A be either checked adjacency matrix, J the all-ones matrix, and L=6I−A. Integer arithmetic verifies A²=4I+2J and AJ=JA=6J. Thus every power of A, and hence every entire matrix function of L, is in the linear span of I, A and J. The coefficients are common to both graphs because they satisfy the same multiplication identities. Their node-0 adjacency rows are exactly equal under the recorded relabeling. Their entire node-0 rows of exp(−(kL+λI)t) are consequently equal for every t, k and λ, and symmetry gives equal node-0 columns.

By convolution, equality of the impulse-response kernels implies equality for every admissible input waveform. More samples, a richer waveform, a higher-precision fit, or more reasoning cannot separate the models at that interface. This conclusion assumes the same physical labeling and the stated linear model; it does not rely on a finite numerical sample.

The graphs are nonisomorphic: exhaustive enumeration finds eight 4-cliques in the rook graph and none in the Shrikhande graph. Their adjacency difference has 100 nonzero ordered entries, all away from row/column zero. Each such entry supplies a distinguishing joint port.

The spectral projectors are P0=J/16, P4=(A+2I)/4−J/8 and P8=I−P0−P4. Therefore

`exp(−(kL+λI)t)=exp(−λt)[P0+exp(−4kt)P4+exp(−8kt)P8]`.

For distinct actuator and sensor nodes, put z=exp(−4kt). An adjacent pair has response `g exp(−λt)(1+2z−3z²)/16`; a nonadjacent pair has response `g exp(−λt)(1−z)²/16`. The difference at common parameters is `g exp(−λt)(z−z²)/4`.

For independently unknown parameters under each model, a pointwise positive gap is insufficient. Bound each model's full output range separately. The nonadjacent polynomial is monotonic on z∈[0,1]. The adjacent polynomial has its only stationary point at z=1/3. Endpoints and that stationary point therefore give the exact extrema over the rate interval. Positive gain and leakage have monotonic effects. The implementation adds a 2×10⁻¹⁵ outward numerical allowance to the resulting elementary floating-point bounds. These are analytic interval bounds with floating evaluation, not a formal arbitrary-precision interval proof.

With bounded additive error ε on each alternative, robust separation requires the distance between the two response intervals to exceed 2ε. Model uncertainty, gain uncertainty and measurement error must not be counted as zero or shared unless the experiment independently establishes that restriction.

## Finite moments: when the more general shortcut is valid

For two finite state-space models of dimensions n1 and n2, equality of the first n1+n2 exact Markov parameters is sufficient to establish equality of their scalar transfer functions. Apply Cayley–Hamilton to the block diagonal difference realization of dimension n1+n2: every later moment is a common linear combination of earlier moments. Equality of only a few moments, approximate floating equality, or equality of eigenvalues alone is insufficient. The present witness uses the stronger explicit adjacency-algebra identity instead.

## Acceptance to freeze before fresh confirmation

1. Integer witness identities and nonisomorphism pass.
2. All original-interface and single-side-expansion cases are rejected as nondiscriminating.
3. A selected joint protocol has strictly positive robust margin under independently varied nuisance parameters and the declared measurement error.
4. An independent numerical physical-model implementation agrees with the response predictions within a tolerance stated before confirmation; tolerances must reflect its numerical method and are not physical tolerances.
5. Node permutations preserving the semantic port labels produce equivariant results. Unpermuted labels must not be silently treated as equivalent.
6. High-error, inaccessible-port and identical-model cases return no feasible protocol.
7. A fresh multi-hypothesis task changes the output from binary discrimination to an identifying experiment portfolio. Validate every pair of alternatives and compare with exact enumeration or another competent solver at the same resource/access limits.
8. The matched-information algebraic competitor can achieve the same useful discrimination. Any tie or baseline advantage defeats an exclusive-method advantage claim.

Acceptance source, selected protocol, technical bounds, economic policy and all seed-generating scripts must be hashed before drawing fresh confirmation randomness. Any later substantive change creates a new version and must preserve the original confirmation result.

## Known limitations and falsifiers

- Nonuniform component values may break the impossibility premise; they could make the original port informative. This would falsify transfer of the exact proof to that physical setup, not invalidate the finite model proof.
- Unknown port labels, an incomplete hypothesis set, hidden forcing, nonlinear dynamics, or unmodeled gain can defeat the experiment's classification guarantee.
- An ideal impulse is not a physical protocol. A finite pulse must be specified and validated, with its integration and timing errors charged.
- The algebraic construction is inexpensive enough that a competent conventional method should tie or beat a generic numerical search on this witness.
- The constructed question is important as a test of means and complementarity, but this study does not thereby establish that the particular graphs describe a paying beneficiary's unresolved problem.

## Sources

The graph family is classical. The academic reference at https://aeb.win.tue.nl/drg/graphs/Shrikhande.html gives the parameters, spectrum and original reference: S. S. Shrikhande, *The uniqueness of the L2 association scheme*, Annals of Mathematical Statistics 30 (1959), 781–798, DOI 10.1214/aoms/1177706207. All identities used for the campaign's witness are also checked directly from the supplied edge lists.
