# ENG-1 bounded follow-up: twelve real coastal-elevation evidence packages

**Date:** 27 October 2026. **Decision:** preserve as a useful real-artifact qualification fixture; do not select as the flagship on current evidence.

## What was actually checked

This follow-up inspected ten NOAA NCEI coastal DEM metadata records and two NOAA Office for Coastal Management DEM records. The sample was purposive, not random: it used the coastal records returned by the declared primary-source queries, included paired MHW/NAVD88 products, and added two modern Florida records from the official Sea Level Rise Viewer directory. It therefore cannot estimate the prevalence of errors in NOAA's catalog or geospatial work generally.

The activity used two targeted queries and eight web open/click retrievals, within the follow-up ceiling of six queries and eight retrievals. Two XML responses could not be rendered by the web reader. Authorized read-only downloads then preserved twelve small source XML files, two linked NcML headers and the already inspected Florida index. All source metadata downloads succeeded. Raw bytes, URLs and SHA-256 hashes are preserved under `raw_metadata/`; `inventory.json` gives the researcher classifications and their boundaries. No raster was downloaded, no elevation transformed, no customer interviewed and no new instrument built.

## The useful purpose comes from the public project

NOAA describes its Sea Level Rise Viewer and associated data as a screening aid for coastal managers to understand potential flooding and prioritize responses. It supplies mapping-confidence information and explicitly limits the intended use. That supplies a real planning purpose for the evidence check: **can a candidate elevation source be interpreted and combined correctly for that screening task, and what limits must follow it into the new use?** The task is not a survey, permit decision, navigation service or new flood-risk certification. [S1]

This distinction matters commercially. NOAA already offers an integrated, free public screening product and publishes current DEMs with source metadata. Reconstructing the same map from older mixed coastal products needs a concrete reason to beat that outside option. The sample did not establish one. [S2]

## Findings from actual source bytes

| Package | Concrete observed issue or useful control | What an adequate existing workflow can conclude |
|---|---|---|
| Miami, 5270 | Title and structured reference identify MHW; abstract describes NAVD88. Lineage records constructing a NAVD88 grid and then a derived MHW grid. | The abstract alone is unsafe for choosing a transform. The provenance supports the MHW interpretation of this record, while an actual delivery should bind it to the exact raster identity. |
| Panama City, 684 | Title and filename identify NAVD88; the ISO structured vertical reference identifies MHW. The linked NcML header explicitly identifies NAVD88. | Cross-checking the actual product header supports NAVD88 for that file. Preserve the catalog conflict; do not silently rewrite the source or claim that the raster itself is wrong. |
| Fort Bragg, 3547 | Catalog describes two datum variants; this record and its NcML header identify MHW. The technical report explains the source transformation and its scale-dependent horizontal-reference treatment. | Select the exact MHW product; do not equate the two variants or inherit the report's scale-dependent approximations into a higher-precision mission. |
| Portland, 606 | A processing step describes a deliberately approximate conversion of one NED source class and assigns values below 0.5 m to 0.5 m above MHW. Lidar limits the affected coverage. | Qualification must preserve that processing operation and locate its affected cells before interpreting fine coastal thresholds. A datum conversion cannot recover discarded source information. This is not a claim that every Portland cell was altered. |
| Central Oregon, 11500 | Generic abstract mentions MHW or NAVD88; title, structured reference and lineage identify the NAVD88 product. | Read product-specific fields and lineage. No unresolved datum contradiction was established in this check. |
| Port Townsend, 1786 | Abstract discusses both products; title and structured reference identify NAVD88, and lineage explains construction of the additional MHW version. | Keep the product distinction. A multi-datum abstract is not itself evidence of defective data. |
| Puget Sound MHW, 5164 | Record identifies MHW; lineage first constructs NAVD88 and then adds a conversion grid. | A normal provenance-aware workflow resolves the apparent intermediate/final-datum difference. |
| Puget Sound NAVD88, 5165 | Paired product identifies NAVD88, consistently with its stated preparation. | Useful negative control: do not manufacture a contradiction because another product covers the same geography. |
| Northern Gulf, 720 | Generic description mentions three vertical datums; selected product title and structured reference identify NAVD88. | Dataset-family prose is insufficient, but existing structured metadata supports selecting the variant. |
| Mobile, 673 | Record identifies MHW; lineage describes NAVD88 preparation followed by MHW conversion. | Distinguish intermediate and delivered states; competent existing tools and a reader can do this. |
| Florida southeast OCM metadata | Directory associates the file with the southeast product; XML title and descriptive label say southwest. Coordinates and listed counties require reconciliation. | Flag a geographic identity conflict. Bounds checking helps; metadata review alone does not establish which raster coverage is wrong, if any. |
| Florida Keys OCM metadata | Title, source lidar descriptions and bounds concern the Keys, but an abstract sentence lists Panhandle counties. | Flag the internal location conflict. Do not treat that sentence as proof that the actual raster covers the Panhandle. |

The two modern OCM records state that vertical accuracy was not separately tested on the finished DEM; they describe source-data specifications instead. That is a qualification boundary, not proof that the DEM is inaccurate. Their acquisition ranges are also not geodetic coordinate epochs. The inventory preserves both distinctions. [S3, S4]

The strongest semantic witness is Portland: a valid processing choice for the original product can remove information relevant to a later question. However, the follow-up has not mapped which cells carry that operation, has not established their effect on a present planning result, and has not obtained a purpose-specific numeric acceptance threshold. An assertion of a newly feasible coastal-planning service would outrun the evidence. [S5]

## Does this establish an unresolved gap?

It establishes that **schema-valid metadata and a computable coordinate transform are insufficient evidence for some cross-purpose reuse**. It does not establish that ordinary approaches fail to manage the problem economically. Every decisive issue found is available to an attentive GIS practitioner in existing source material. FME can check fields, bounds, product identity and structured consistency; PROJ and VDatum can execute legitimate transformations. Human review can distinguish process intermediates from the final product and interpret non-invertible processing steps.

A frontier agent might reduce the cost of reading those sources and producing a source-linked decision record. That is a credible Operational Alpha hypothesis, particularly for cross-document semantics, but it remains untested. Calling the task a newly invented geospatial instrument before that comparison would merely rename a competent review workflow. Likewise, a collection of deliberately selected metadata conflicts would be a diagnostic fixture, not proof of portfolio-level prevalence or buyer value.

The exact public purpose investigated already has a strong outside option: NOAA's own screening layers and confidence products. A more demanding customer-specific purpose might expose a valuable gap, but could require new measurements or professional analysis that no metadata tool can supply. That purpose must come from evidence about a decision, not from selecting an arbitrarily strict threshold to force the baseline to fail.

## Small test justified by these findings, if retained as supporting research

Freeze a source-reconciliation task on the original files, with scope limited to identifying the delivered product, resolving supported ambiguities, preserving conflicts and specifying what remains unqualified. Use a selection rule that includes consistent controls, paired products and unfamiliar source families. Separate the development documents from fresh confirmation. Give all arms the full relevant source access and normal GIS documentation; supply FME or equivalent conventional checks where available.

Measure whether U, E and E+ produce correct evidence records at the same effort budget. An accepted answer must distinguish actual contradictions from valid intermediate-to-final transformations, avoid converting missing information into invented certainty, and avoid rejecting every record. Give the discovered provenance representation to U to isolate its contribution. Cost all reading, source retrieval, corrections and review. This is a proportionate transfer experiment, but it would remain supporting evidence rather than the present edition's consequential flagship.

An independent acceptance reviewer could verify documentary claims against pinned metadata and actual file headers. That would validate the evidence audit, not the physical elevations or a flood model. The latter require a different experiment and acceptance authority.

## Responsibility, participation and financing

If a scoped evidence-audit service eventually proves useful, the provider could be responsible for accurately reporting what the supplied sources support, with an explicit acceptance record and correction process. The infrastructure owner would retain the decision about additional surveys or engineering work. An authenticated shared capability could contain generic parsers and review procedures, while customer archives and mission-specific decisions remain permissioned.

A consortium could finance those generic adapters, but the observed public-data sample supplies no reason to assume participants will join or prepay. Existing public tooling reduces the potential incremental value. Consortium exploration should therefore wait until a named class of decisions shows material repeated review cost. Positive expected savings would still not finance construction before collection; deposits, withdrawal rights, obligations and opening cash would need a separate dated cash model.

## Stop decision

**Do not build a large simulator or promote ENG-1 to flagship from this check.** Preserve the real conflicts, the successful conventional resolutions and the negative controls. They are useful evidence for mission requalification and a possible cheap expert-workflow test. They do not yet demonstrate a consequential opportunity that current approaches cannot already deliver well. Another candidate with a clearer unmet decision and a more decisive executable test should take precedence.

## Source links and artifact evidence

- [S1] NOAA, [Sea Level Rise Inundation](https://coast.noaa.gov/digitalcoast/data/slr.html), accessed 2026-10-27.
- [S2] NOAA, [Sea Level Rise Viewer DEM directory](https://coast.noaa.gov/slrdata/DEMs/index.html), accessed 2026-10-27.
- [S3] NOAA, [Florida southeast metadata](https://coast.noaa.gov/slrdata/DEMs/FL/FL_SE_dem_metadata.xml), downloaded and hashed.
- [S4] NOAA, [Florida Keys metadata](https://coast.noaa.gov/slrdata/DEMs/FL/FL_Keys_dem_metadata.xml), downloaded and hashed.
- [S5] NOAA, [Portland metadata](https://data.noaa.gov/waf/NOAA/NESDIS/NGDC/MGG/DEM/iso/xml/606.xml), downloaded and hashed.
- [S6] NOAA, [Miami metadata](https://data.noaa.gov/waf/NOAA/NESDIS/NGDC/MGG/DEM/iso/xml/5270.xml), downloaded and hashed.
- [S7] NOAA, [Panama City metadata](https://data.noaa.gov/waf/NOAA/NESDIS/NGDC/MGG/DEM/iso/xml/684.xml), with its linked NcML header preserved.
- [S8] Love et al., [Digital Elevation Models of Fort Bragg, California: Procedures, Data Sources and Analysis](https://www.ngdc.noaa.gov/mgg/dat/dems/regional_tr/fort_bragg_13_navd88_2012.pdf), 2012, inspected as the original technical report.

The inventory JSON contains every metadata URL, local artifact name and SHA-256; raw files permit independent review of these classifications. Source documents support their attributed observations. The proposed commercial mechanism and test are researcher hypotheses. No model-versus-model result, physical validation, observed demand or revenue was produced.
