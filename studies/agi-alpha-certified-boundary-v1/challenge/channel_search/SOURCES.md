# Primary source and candidate boundary

Target: construct at least 384 mutually non-confusable length-three words for the 15-symbol cycle channel, improving the retrieved explicit 383-word construction. This is a finite constructive target, not a claim to determine Shannon capacity.

The source data are from Nathaniel Itty, Christopher D. Rosin, Chase Carstensen and Daniel Reichman, *Improved lower bounds for the Shannon capacity of odd cycles*, arXiv:2607.21517v2, 30 July 2026, Table 9. Primary URL: https://arxiv.org/html/2607.21517v2 . The HTML page identifies a Creative Commons Attribution 4.0 license. Source table extracted without changing coordinates. The article HTML is preserved as reference.html; c15_3_published383.json contains the triples and exact pairwise validation.

The July 31 primary paper by Pjotr Buys, Sven Polak and Jeroen Zuiddam, *Lean-verified lower bounds for the Shannon capacity of odd cycles*, https://arxiv.org/html/2607.29681v1 , improves asymptotic capacity bounds via a profile product theorem. The small profile searches included here reproduce its C7 and C11 numerical bounds; they do not improve them. A later primary paper identified by the parent workstream, Tandon, *Strengthening Recursive Constructions for Zero-Error Shannon Capacity*, arXiv:2608.30273, is an additional comparator for profile constructions. Its figures must not be silently replaced by the July bounds.

An apparent search hit containing 384 is *On the Shannon Capacity of Triangular Graphs* (2013). It concerns T15, a different graph, and is not evidence of a 384-word construction for C15 cubed. Our limited search is not a proof that a more recent cycle construction does not exist.

The search uses ordinary SciPy/HiGHS mixed-integer programming. Each eight-vertex toroidal 2x2x2 cube forms a clique. The global run also uses all 45 adjacent two-layer slice inequalities. Each such slice projects injectively to an independent set of C15 squared. Summing adjacent-row inequalities gives size at most floor(15*7/2)=52 for that projection. Summing the 15 slice inequalities in one orientation gives an upper bound of 390 on C15 cubed. This is a valid elementary upper bound, not a new theorem.

The unseeded global run and the published-witness-seeded neighborhood run answer different operational questions. Their difference must not be reported as a controlled model advantage. The strong baseline is allowed the known witness and therefore starts at 383. Neither same-session language-model cost nor an ordinary/expert language-model A/B is measured here.

The separate verifier uses direct circular distances and an explicit channel-output inverse map. It does not import graph construction or clique constraints from the solver. The certified channel sends each coordinate x to either x or x+1 modulo 15. Errors outside that model can be silently confused with another valid codeword and are not certified.
