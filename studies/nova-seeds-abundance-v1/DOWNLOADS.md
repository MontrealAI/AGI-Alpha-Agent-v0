# Complete source archive

The saved deliverable includes the complete canonical
`Nova_Seeds_Abundance_v1_Source.zip`. Its contents and identity are unchanged.
For public repository transport, the same ZIP is split into two consecutive
byte parts because the connector's request-size limit cannot accommodate the
full archive after base64 encoding.

Keep `ASSEMBLE_ARCHIVE.py` and both `.zip.part01` / `.zip.part02` files together
at this study's root. From that directory, run:

```sh
python ASSEMBLE_ARCHIVE.py
```

Python 3.8 or later is sufficient; no installation or network access is needed.
The script verifies both part hashes, reconstructs the exact original ZIP,
reopens it to verify its full hash, and refuses to overwrite a conflicting file.
An existing identical archive is preserved. `PART_IDENTITIES.json` records the
part sizes, ordering, offsets and hashes.

The reconstructed archive is **15,317,764 bytes**, with SHA-256:

```text
b8785b08bf0a7d66e50dd28a5729e25705579a8774feb55aa02427710d2dba51
```

Extract it and follow its `README.md`; `verify_manifest.py` checks every
declared payload. The canonical PDF is already inside the ZIP.

The existing coordinator can publish the full ZIP as a public release
attachment after receiving acknowledgement and required review through
[issue #4850](https://github.com/MontrealAI/AGI-Alpha-Agent-v0/issues/4850).
The transport parts do not establish a qualified merge, release attachment,
or successful Pages deployment; those publication states require their own
verification.
