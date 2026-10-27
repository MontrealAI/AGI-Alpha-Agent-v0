# Independent challenge: thermal decision certificates and measurement procurement

**Date:** 27 October 2026. **Status:** selection grounding only. Six focused web
queries and three deep primary sources were used; no customer outreach, quotation
request, purchase, new physical experiment or flagship implementation occurred.
The existing `foundations_candidates.md` was read before this challenge.

## Recommendation: NARROW; conditional go remains unearned

There is a credible service setting—thermal evidence for material and device
decisions—but the search does not establish unsatisfied demand for this particular
artifact. Established providers already offer thermal measurement, extraction,
multilayer analysis and model validation. The additional value must be a correctly
bounded answer to a recipient's original decision, or a better justified and
physically available evidence-acquisition plan, relative to competent current
practice. It is not generic access to TDTR or to a thermal simulation.

**Narrow the initial offering to an independent evidence-sufficiency and
decision-robustness assessment, with a conditional measurement plan.** Do not
promise full tensor recovery, a field-safe device, universal three-face access,
or successful characterization of an arbitrary encapsulated stack. A supplier
or laboratory may already supply an equivalent service; obtain a scoped
comparison before any commercial novelty claim.

For this hybrid edition, a computational construction may proceed only after
the selection team fixes two independently motivated mission briefs, their
genuine symmetry/orientation information, and an inspectable evidence route. If
those are unavailable, the result is an explicitly supplied-model engineering
demonstration, and it should not be promoted into a new profitable possibility.
This note does not itself satisfy those gates.

## 1. Credible beneficiaries and the decisions they could buy

| Beneficiary class | Useful original decision | What would have to be verified before offering |
|---|---|---|
| Anisotropic material/substrate supplier | Which orientation/temperature-specific characterization can it truthfully provide for a defined lot or state? | Material symmetry, lot homogeneity, preparation history, supported temperature range, evidence rights and a customer's actual need |
| Device or heat-spreader development team | Does an unchanged operating/design option meet its thermal requirement, or is more evidence needed before commitment? | Device geometry and boundary conditions, actual heat loads, permissible design alternatives, acceptance threshold and uncertainty standard |
| Thermal-metrology laboratory | Which available measurement is worth performing for a specific question, and what can its report support? | Apparatus and fixture limits, existing expert capability, actual quote, data deliverables, calibration, queue and responsibility boundaries |

These are credible classes, **not identified buyers**. NETZSCH's product page
ties thin-film thermal measurement to electronic thermal management [D1].
Microsanj markets pre-production and research testing for advanced packaging and
links measured properties to model extraction/validation [D2]. Neither source
demonstrates a customer's willingness to pay for our proposed global certificate.

The most suitable first case is likely a controlled bulk or accessible
anisotropic coupon with inspectable geometry and independently documented
orientation, plus a distinct application model. An opaque assembled package with
unknown layers is a poor first promise. A buried-interface problem must not be
renamed a six-component conductivity-tensor problem simply to fit the theorem.

## 2. A convenient material choice can erase the claimed restriction

The targeted supplier search returned a commercially listed research-grade
β-Ga2O3 specimen: nominal (010), ±1°, 5 × 5 × 0.35 mm, described as containing a
"Twin" and priced only on request [S3]. This is evidence that nominal material
and face information can be available. It is not evidence of three prepared
orthogonal faces, single-domain homogeneity, an accurately registered in-plane
axis or a metrology-ready specimen.

**Conditional mathematical challenge:** if a monoclinic material's unique axis
is known to be the surface normal, the twofold symmetry makes the
normal–tangential conductivity couplings zero. In a frame with that axis along
y, invariance under R = diag(−1, 1, −1) implies Kxy = Kyz = 0. Consequently the
measured normal coefficient and in-plane Schur block may already determine the
four symmetry-allowed components. The free six-component ambiguity is then the
wrong admissible set. This is reasoning conditional on a justified symmetry and
registration, not a measurement of the listed specimen.

For the commonly discussed monoclinic (010) orientation, the selection team must
check this issue explicitly. Twinning, offcut and uncertainty do not justify
discarding all known structure; they require an appropriate uncertainty model.
An oblique face may retain a consequential ambiguity, but choosing one solely to
manufacture a win would not establish an independent need.

Likewise, known transverse isotropy or a qualified supplier tensor can remove
the apparent problem. Start with the recipient's actual information, including
cheap conventional evidence, before constructing the compatible class.

## 3. Which observations are physically procurable?

### TDTR geometry and access are constraints, not labels

NETZSCH specifies a standard PicoTR substrate format of 10–20 mm square and at
most 1 mm thick, with 45 μm pump and 25 μm probe diameters. Its rear-heating /
front-detection description uses a film on a transparent substrate; front/front
operation accommodates opaque substrates. The supplied software already includes
thermal-property extraction and multilayer analysis. The listed ±6.2% accuracy
is tied to a named reference specimen, RF mode and 40-minute measurement, not a
universal tensor uncertainty [D1].

A 5 mm supplier coupon is therefore not automatically compatible with that
standard fixture. A sufficiently small optical spot does not settle mounting,
edge-distance, diffusion-length, surface-finish or coating requirements. A
different laboratory might support it, but that support must be confirmed.

Three geometrical faces are also not three interchangeable planar-stack
experiments. Cutting a side of a layered device changes how the layers intersect
the observed surface. The original forward model must be re-established. A
wafer's parallel front and back faces are not three independent non-coplanar
orientations. A vendor's RF mode does not by itself prove that an idealized
same-face ambiguity has been broken; the actual transmission/sensing model must
be checked.

Potential preparation costs include cutting, polishing, mounting, transducer
deposition, thickness measurement and registration. They can consume the specimen
or alter the region being characterized. An available second specimen is not
automatically the same physical evidence identity as the first.

### Crystallographic information is a genuine outside option

GFZ describes an operating Laue system with a 200 μm spot and orientation accuracy
of 0.1° tested on standards [S1]. This is infrastructure evidence, not a service
reservation or a general uncertainty guarantee. A separate supplier advertises
small-crystal orientation measurements [S2]. Thus it is not credible to assume
that orientation is unknowable unless a new thermal method is invented.

For reuse, require the actual coordinate transform or equivalent registered axes,
uncertainty, measured region, sample identifiers and surface references. A Miller
index alone does not generally provide the complete lab-frame transform required
for signed off-diagonal terms. Diffraction can also expose multiple domains; it
does not measure the thermal coefficients or prove uniformity throughout the
device. Distinguish crystallographic axes from thermal principal axes when the
symmetry does not make them coincide.

### Packaged-device access must be scoped

Microsanj's FAQ says its top-surface methods require optical access and a thin
metal transducer, with special scoping when no optical access exists. The company
also advertises buried-interface characterization and SanjTHERM model validation
[D2]. These are vendor capability claims to test on the requested specimen, not
general identifiability theorems. Do not copy its broad marketing claims or its
anonymous performance anecdotes into the study as independent validation.

## 4. Public costs, lead times and what they do not establish

| Source | Publicly displayed evidence | Permissible use in this study |
|---|---|---|
| TESTDOG orientation-analysis menu [D3] | Opened page: from GBP145/sample excluding VAT; GBP45 service fee for orders below GBP300; typical 8 working days after acceptance and method confirmation | An illustrative advertised starting price and conditional lead time for orientation work, not a quote for registered uncertainty needed by our certificate |
| Microsanj testing service [D2] | Typical 2–3 weeks, depending on complexity; report; NDA possible; no matched public price recovered | A real outside-option route and timing anchor; thermal-test cost remains unknown pending scope/quote |
| RISE TPS/TLS service [S4] | Price by tender; TPS measurement up to one week after arrival and completed report within three weeks after measurement; sample preparation/conditioning required | Evidence that procurement and reporting time are material; TPS/TLS are not substitutes for arbitrary thin-film full-tensor TDTR |
| NETZSCH PicoTR [D1] | A 40-minute reference measurement condition | Instrument time example only; not end-to-end turnaround or total service cost |

The initial search excerpt for TESTDOG showed GBP60 while the opened page showed
GBP145. Preserve this discrepancy. Use the opened page only as a dated menu
observation, and do not calibrate a profitable scenario to the cheaper cached
snippet. The provider's actual executing laboratory, applicable uncertainty and
scope were not independently verified in this bounded search.

No matched public tariff was found for the complete proposed service: global
ambiguity analysis, a mission certificate, specimen preparation, thermal traces,
orientation evidence and procurement coordination. A prospective cost model
should therefore retain unknown quoted line items and explicitly assumed labor.
For sensitivity only, an analyst could disclose an **assumed** 4–16 expert hours
at USD150–300/hour (USD600–4,800) before laboratory/preparation charges. These are
not observed hours, a sourced thermal-consulting rate, a buyer price or an
authorization to spend. They should be replaced by a matched H quote or measured
task effort before any margin claim.

Currencies should remain separate until a dated exchange rate is sourced. Include
shipping, tax where applicable, damaged/failed samples, retests, review,
correction, confidentiality handling and support. A refundable customer deposit
is an obligation. Lab prepayment and a two-to-three-week queue can create a cash
shortfall even with a positive expected contribution.

## 5. Incumbents may already supply much of the package

The strongest observed commercial counterexample is Microsanj: the public offer
combines thermal imaging, materials/interface characterization, parameter
extraction, model validation and a testing service [D2]. NETZSCH also supplies
analysis and contract-testing access [D1]. The foundations dossier separately
documents mature goal-oriented experimental-design algorithms and software.

The three deeply read pages do **not** specify independently checkable global
decision bounds over all compatible anisotropic tensors, signed multi-face
evidence lineage, or multi-buyer funding of mission-relevant evidence. That is a
documentation gap, **not proof that competent providers lack those services**.
One must compare the exact requested output with the incumbent's scoped service.
Do not weaken E to local fitting with no physics expertise.

An initial operational service could still have value by helping a recipient use
available metrology well. If so, price and evaluate that expert delivery honestly.
Technical novelty, newly learned Alpha, graph-specific benefit and customer
savings are separate claims.

## 6. A concrete offering that can be reviewed before commitment

The initial contract should bind an original thermal decision and acceptance
quantity to a specific material/sample identity, geometry, operating conditions,
available observations, justified priors and uncertainty model. It should permit
one of the outcomes agreed **before** execution:

1. A conditional robust decision with independently checked bounds.
2. Explicit compatible countermodels showing the decision is not yet supported.
3. A scoped measurement plan with feasibility state: confirmed, requires laboratory
   confirmation, or unavailable within the customer's constraints.

If the customer instead orders a successful design qualification, a negative
evidence report does not fulfill that contract automatically. Mathematical
certification of an assumed model is not a licensed engineering release or a
prediction that the fabricated device will behave exactly as modeled.

For each proposed measurement, the plan must specify sample and region,
orientation registration, preparation permissions, apparatus/fixture capability,
observable and its forward model, required raw data/uncertainty deliverables,
calendar dependencies, price status and failure handling. Same-face repeats may
reduce noise in already observable quantities; they should not be rejected
categorically. They must not be credited with recovering structural information
that the applicable theorem rules out.

The relevant construction test is whether frontier reasoning can derive a
different useful measurement or prove that none is affordable, given these actual
constraints. Supplying the finished tensor formula, compatible specimens and
cheap additional faces would test possession of a recipe, not that discovery.

## 7. Commercial complementarity without invented compatible demand

A meaningful joint package is possible only when independently specified
questions share evidence that is valid for all of them. The common object might
be a particular supplier lot, a parent crystal, a calibrated observation model or
a qualified reference series. Common material names are insufficient. Differences
in temperature, treatment, defects, dopant level, coating, orientation, thickness
or interfaces can invalidate the proposed sharing.

The discovery procedure should compare separately sourced mission requests and
identify overlap in their **needed information**. It may find that one decision
is already robust, another needs orientation only, and a third needs a destructive
measurement. Those participants need not join one offering. Do not impose a
minimum number of investments or a universal subscription.

Technical-commercial complementarity would be demonstrated if the instrument
finds a qualified shared measurement that is sufficient for several decisions,
and actual conditional commitments make that measurement financeable when
private purchase is not. A coalition receiving a discount for identical routine
tests is an arrangement result, not automatically a technical invention.

No provider confirmed a shared setup fee or batch discount in this search.
Therefore a cost function such as C(S) = F + sum_i c_i is an explicit modeling
assumption, not a measured economy of scale. The conventional arrangement-only
control must be allowed to use ordinary batch procurement and existing lab
consultation. Compare private expert delivery, technical instrument alone,
coordination alone and the combination.

For a real joint order, specify each participant's outside option, price ceiling,
data rights and cancellation point. Collect conditional commitments before
irreversible preparation. Release funds only under the agreed milestones; reserve
refunds and retesting obligations. Allocate the risk that a common calibration,
specimen defect or invalid transfer assumption invalidates everyone's result.
Pooling does not diversify that common failure. No such commitments have been
obtained here.

## 8. Selection gates and stop conditions

**Go to a bounded implementation only if all are met:**

- Two consequential mission briefs exist independently of the theorem and retain
  their original purpose/threshold; they are not selected for an easy crossing.
- Available symmetries, orientation evidence and conventional measurements have
  been included before declaring the relevant ambiguity.
- At least one actual trace/metadata source or clearly labeled assumed observation
  model can be audited, and a distinct application forward model can be checked.
- Proposed additional observations are physically described and their access
  status is explicit; an unavailable face is not an inexpensive oracle.
- E has the same strong prior art, expertise, evidence and procurement options.

**Stop or narrow further** if orientation/symmetry already resolves the useful
decision, no feasible informative measurement exists, all mission-relevant
conclusions are invariant without new work, an incumbent supplies the package
more economically, the only witness is the paper's supplied matrix example, or
the shared-demand/financing assumptions drive the entire positive result.

Even if construction passes, measured economic possibility remains unestablished
until buyer participation, real preparation/measurement costs, delivery timing
and rights are tested. A valid abstention or decision certificate can still be a
useful research outcome.

## Primary-source register and search accounting

### Three deep sources

- **[D1] NETZSCH PicoTR, official product/specification page:**
  <https://analyzing-testing.netzsch.com/en-US/products/time-domain-thermoreflectance-analyzer-tdtr/picotr>.
  Read relevant method, geometry, specifications and software sections. Vendor
  specifications, not independent validation.
- **[D2] Microsanj advanced packaging / 3DHI, official offer:**
  <https://microsanj.com/advanced-packaging-3dhi/>.
  Read offer, model integration and FAQ. Vendor capability/timing statements;
  anonymous anecdotes and broad superlatives are not adopted as evidence.
- **[D3] TESTDOG single-crystal orientation analysis, seller service menu:**
  <https://testdog.co.uk/single-crystal-orientation-analysis-analysis.html>.
  Read price, timing, preparation, output and limitation statements. Menu is
  conditional and is not a matched quotation or independent lab accreditation.

### Primary search-excerpt support; not deep full-page audits

- **[S1] GFZ Laue infrastructure:**
  <https://www.gfz.de/en/section/chemistry-and-physics-of-earth-materials/infrastructure/laue-x-ray-diffraction-crystal-orientation-system>.
- **[S2] Photonic Science, Laue orientation application:**
  <https://photonicscience.com/laue-crystal-orientation-system-used-in-micro-diffraction-experiment/>.
- **[S3] MTI Korea β-Ga2O3 (010) research-grade substrate:**
  <https://mtikorea.co.kr/product/ga2o3-%C3%9F-single-crystal-substrate-1%C2%B0-ori-5-x-5-x-035mm-2sp-research-gra/5267/>.
- **[S4] RISE thermal-conductivity services:**
  <https://www.ri.se/en/metrology/service/thermal-conductivity-measurements-according-to-iso-220072>.
  Its page excerpt inconsistently names a standard in its first paragraph versus
  title; this note uses the service/timing/preparation statements and makes no
  independent accreditation or standard-compliance conclusion.

Six exact focused queries were: (1) TDTR thermal conductivity measurement service
sample requirements price turnaround site:edu; (2) thermal conductivity
anisotropic TDTR measurement service price turnaround sample; (3) Laue crystal
orientation measurement service price turnaround; (4) NETZSCH PicoTR sample
dimensions front rear transmission anisotropic; (5) Ga2O3 substrate 010 100 201
orientation 10 10 0.5 mm MTI Corporation; (6) Laue orientation crystal service
external rates university sample X ray orientation. No further search was used.
