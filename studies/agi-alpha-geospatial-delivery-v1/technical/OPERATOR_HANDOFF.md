# Montréal park and recreation-asset onboarding package

## What is delivered

The package preserves 2,245 public park/green-space polygons and 3,476 recreation-asset records. It records 3,175 associations where a source park identifier and one geometric park agree, and supplies 301 facility review rows. A further 456 park rows need review for joining: 455 lack a logical park index and one has invalid geometry. Missing indices can be legitimate for other or private green spaces; the queue does not declare them all erroneous.

Open `delivery/montreal_asset_onboarding.gpkg` in a GeoPackage-capable GIS. Its `parks` and `facilities` layers use NAD83 / MTM zone 8, EPSG:32188. `exception_queue` and `source_provenance` are ordinary SQLite tables. `delivery/reconciliation.csv` is the portable asset register, `delivery/exceptions.csv` the complete queue, and `delivery/asset_map.png` the overview. Run `acceptance_queries.sql` with an SQLite client for the recorded count and disposition checks. The original source data remains in `../data/`; canonical feature hashes and complete source-property JSON link every output row back to it.

The field `status=confirmed` means **source-consistent association**. It is not municipal approval, a cadastral determination, ownership evidence, a survey, a field observation or confirmation that the facility currently operates. Source boundaries are not legal boundary references. The two downloaded resources were interpreted as WGS84 longitude/latitude GeoJSON and transformed with explicit XY axis order. The source files, dependency versions and all transformations are recorded.

## How to use the queue

Retain the source identity, declared park reference and geometric candidates together. A declared reference is never silently overwritten with a nearer or more convenient park. Geometry-only matches are suggestions. A missing reference, source geometry defect or identifier/geometry disagreement is an explicit follow-up item for an authorized source owner. The product is an evidence-backed onboarding and review handoff; it does not include fieldwork or resolution of owner-controlled facts.

The original borough labels `Verdum` and `Verdun` are preserved separately. The source has twenty distinct nonempty labels; this is not a claim that Montréal has twenty boroughs. New consumers must decide, with appropriate authority, whether a label normalization is legitimate.

## One connected example

The originating development slice was Ahuntsic-Cartierville: 253 assets, 245 source-consistent associations and eight review items. The instrument was frozen before outcome execution on the other source-labelled boroughs. Those other labels contained 3,223 assets, of which 2,930 received source-consistent associations and 293 remained in review. The common full park layer was available during development; this is fresh recipient application, not an unseen-geography benchmark.

An independent local recipient process then used the copied frozen instrument on Anjou: 100 assets, 89 source-consistent associations and 11 review items. For example, facility `OBJECTID=57`, asset `032-0020`, named `Fer / Galet`, has declared park `2010-000`; the spatial evidence agrees with that same park index, whose source name is Lucie-Bruneau. It is output as a source-consistent association, with original fields and hashes intact.

Facility `OBJECTID=61`, asset `073-0104-76-S2`, is a useful counterexample from the same recipient. Its source label is `Soccer sous-terrain à 7` and its declared park is `1267-000` (Carlos-d'Alcantara). Its geometry instead supports `2012-000`. The instrument records an identifier/geometry conflict and retains both references; it does not choose an owner or silently fix the source. Both this review item and the successful association are part of the same accepted handoff.

An ordinary local library containing identical source bytes and information produced byte-identical versions of all seven recipient files. Copying and provenance are demonstrated; an exclusive economic advantage is not. The transferred version 1.0.0 was later found to have robustness defects on null properties and nonpolygon park inputs. Those failures and the original transfer remain preserved. Version 1.1.0 corrects them and adds the explicit target-area and source-hash checks. Its full municipal replay is unchanged; 48 newly authored structural cases and 128 independently computed public-source decisions pass. Neither replay nor later signatures retroactively changes the original evidence.

## Optional practice and the next capability

The optional CSV/WKT adapter requires a fresh field map and declared source CRS for each mission. An eight-row origin practice case exercised this researcher-authored executable extension; no closed-model weights were modified. All original extra CSV fields survive normalization.

Fresh generated format missions preserved all 256 rows and their extra fields, with identical association semantics in 29 of 32 missions. The three divergences occur at exact polygon vertices after EPSG:3857 round trips: a previously supported boundary association becomes an explicit review case. All divergent records remain visible. The adapter is held for unrestricted automatic cross-CRS boundary decisions. A prospective precision/tolerance policy, followed by fresh boundary cases and owner-specified accuracy obligations, is the next technical validation step. These optional limitations do not erase the completed official-source onboarding package.

## Reproduction

Use Python 3.11–3.13 with the dependency versions in `dependency_versions.json`. From the study root:

```bash
python src/reproduce_technical.py --out /tmp/geospatial-study-replay
```

Choose a new or empty output directory. The runner checks input and instrument hashes, regenerates the package, executes sixteen scoped regressions, replays the separate reviewer’s structural and conventional controls, and reproduces all thirty-two format missions including their three divergences. It writes a receipt and step logs without overwriting historical experiment receipts. No paid model API, customer system, wallet, live ENS or network download is needed.

For the original technical delivery alone:

```bash
python src/geodelivery.py --parks data/parks.geojson --facilities data/facilities.geojson --sources sources/public_data_sources.json --out /tmp/geospatial-delivery
```

## Inheritance and authority

Reuse stable parsing, reconciliation and packaging structure. Recheck source rights, field meaning, CRS, current versions and acceptance criteria. Regrant mission authority separately. `capability_manifest.json` contains provenance, rights, dependencies and failure modes, and is bound to a local fixture using the existing repository TrustRegistry. Existing native scope does not admit geospatial execution. No live ENS authentication, production admission or municipal/customer authorization is asserted.

Commercial service pricing and complete costs are modeled separately under `../configs/economics.json`. The fraction of records whose identifiers agree with geometry is not a calibrated probability that an AI-operated mission passes customer acceptance. Controlled H/U/E/E+ trials, actual customer collections and complete actual research expenditure were not measured by this technical experiment.

## Prior art and primary sources

- Ville de Montréal, [parks and public spaces catalogue](https://open.canada.ca/data/en/dataset/2e9e4d2f-173a-4c3d-a5e3-565d79baa27d) and [outdoor recreation facilities catalogue](https://open.canada.ca/data/en/dataset/60850740-dd83-47ee-9a19-13d674e90314). Original data is attributed under CC BY 4.0; derived outputs do not imply endorsement.
- GDAL, [ogr2ogr](https://gdal.org/en/stable/programs/ogr2ogr.html) and [geometry validity](https://gdal.org/en/stable/user/geometry_validity.html). Conversion, spatial checks and repairs are mature capabilities. This study preserves exceptions instead of silently repairing them.
- OGC, [GeoPackage](https://www.ogc.org/standards/geopackage/). The package uses this established format; successful SQLite/GDAL readback is narrower than certification of every standard clause.
- IETF, [RFC 7946](https://www.rfc-editor.org/rfc/rfc7946), for GeoJSON coordinate conventions.
