# Research edition downloads

- [Complete executable research companion](AGI_ALPHA_FLYWHEEL_Research_Companion.zip)
- [Paper — PDF](paper/paper.pdf)
- [Executive brief — PDF](paper/executive_brief.pdf)
- [Connected example — PDF](paper/connected_example.pdf)
- [Standalone browser edition — HTML](web/index.html)
- [LinkedIn draft — approval pending](paper/LINKEDIN_DRAFT.md)

The companion contains the new study, all public synthetic inputs, source closures and licenses, frozen protocols, results, reviews, publication files and the separately preserved earlier battery exploration. The companion's inner directory is `agi-alpha-opportunity-construction-v1/`.

`FILE_MANIFEST.json` hashes the companion's files. It excludes itself and the outer companion ZIP/checksum to avoid circular hashes. `COMPANION.sha256` identifies the exact ZIP. To verify the download from the directory containing both files:

```sh
sha256sum -c COMPANION.sha256
```

The companion uses lossless LZMA compression inside the ZIP container to fit the publication service's request limit while preserving every file. Python 3.12 can extract it without another dependency:

```sh
python -m zipfile -e AGI_ALPHA_FLYWHEEL_Research_Companion.zip research-companion
```

The browser-readable GitHub Markdown source remains useful without executing code. Download the standalone HTML and open it locally for the designed reading edition. This research source publication is separate from canonical Pages or a repository software release.
