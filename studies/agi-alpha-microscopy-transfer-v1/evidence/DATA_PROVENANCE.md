# Public microscopy inputs and measurement scope

Prepared 27 October 2026. These are public research images/labels; no personal health records or private customer information were accessed.

## Development source

IDR study **idr0062-blin-nuclearsegmentation**, image **6001240 (B1_C1.tif)**. The official study identifies Blin, Sadurska, Migueles, Chen, Watson and Lowell as authors; publication DOI `10.1371/journal.pbio.3000388`, dataset DOI `10.17867/10000125`, copyright Blin et al., CC BY 4.0. Official source: https://idr.openmicroscopy.org/study/idr0062/ . This is confocal mouse-cell research imagery. The study and labels precede this project.

The native OME-Zarr 0.4 label array was downloaded from `https://livingobjects.ebi.ac.uk/idr/zarr/v0.4/idr0062A/6001240.zarr/labels/0/0`. All 32 requested compressed chunks were obtained; no missing chunk was silently replaced. Published label bytes were decoded with Numcodecs 0.16.3, channel singleton removed, and saved as NumPy. No label was inferred, relabeled or corrected. Native shape is z/y/x = 236/275/271. Label metadata supplies spacing z/y/x = 0.5002025531914894 / 0.3603981534640209 / 0.3603981534640209 micrometers. Preserve `development/manifest.json`, original `.zattrs`/`.zarray`, compressed chunks and export hash.

## Fresh recipient source (quarantined pending freeze)

IDR study **idr0052-walther-condensinmap**, image **5514375**. Official source: https://idr.openmicroscopy.org/study/idr0052/ . Authors Walther, Hossain, Politi, Koch, Kueblbeck, Ødegård-Fougner, Lampe and Ellenberg; publication DOI `10.1083/jcb.201801048`, dataset DOI `10.17867/10000123`, copyright Walther et al., CC BY 4.0. The study concerns tagged condensin in HeLa cells; this study does not infer patient or clinical outcomes.

Native `Cell` and `Chromosomes` groups at **zero-based time index 7, channel 0** were selected before inspecting label statistics or experiment outcomes. Original chunks span time indices 0–9; only the fixed index 7 is exported. Native exported shape is 31/256/256, spacing 0.75/0.2516/0.2516 micrometers. Keep the folder inaccessible to implementation decisions until the selected capability is frozen. Freshness is **fresh to the receiving configuration/implementation development**, not a globally secret benchmark or unseen public research data.

## Meaning of measurements

These arrays supply a published integer partition of space. Object/label count is the number of distinct requested non-background label identities, not an independently validated biological cell count. A label can contain disconnected components; a connected-component count is a different quantity and requires a separate mission.

Native physical volume means occupied source voxel volume in the source metric. Mapped geometric volume under an explicitly supplied affine deformation is a different quantity: it changes by the absolute determinant of the linear transformation. A pure re-expression of units/coordinates does not change the physical specimen volume. A registration matrix in this experiment is researcher supplied unless independently estimated and validated; its availability does not establish physical alignment.

Current NGFF v0.6 explicitly states voxel centers at zero-based integer coordinates with half-open voxel extents centered on them; source https://ngff-spec.readthedocs.io/en/latest/ (Coordinate convention). These particular files are v0.4. The accepting measurement contract must state its center/extent interpretation. Do not silently add half a voxel or infer geometric meaning from matrix dimensions alone.

NGFF v0.6 excludes exact resampled-pixel reproducibility from its file-format guarantee. This motivates checking the useful quantity, but does not imply that existing expert tools cannot already perform the analytical measurements. Conventional feature extraction, affine algebra and an identical-content ordinary library must remain serious baselines.

## Provenance and reuse

Official study-page facts were retrieved using the web reader; a subsequent direct HTML request for idr0062 returned HTTP 403 and was not retried. Source facts, URLs, retrieval outcomes and any successfully obtained catalog/specification snapshots are retained in `provenance/`. Source image records and metadata are original public evidence. `.npy` exports are derived lossless array extraction, with unchanged label values and singleton/time selection documented. Redistribution must include the stated creator credit, study/data DOI, CC BY 4.0 license URL https://creativecommons.org/licenses/by/4.0/ , source URLs, and disclosure of these changes.

No biological segmentation validation, new cell-biology discovery, physical calibration, live customer acceptance or operating revenue is established by this acquisition. Downloaded bytes and successful decoding are observed; downstream transformations, acceptance and market economics require their own results.
