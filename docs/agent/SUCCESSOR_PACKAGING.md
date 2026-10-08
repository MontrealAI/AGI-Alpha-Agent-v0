[Project notice](../DISCLAIMER_SNIPPET.md)

# Release packs and independent restoration

Every distributed file is limited to **450,000,000 bytes**. The native wheel, matching dependency lock,
installer and operator guides form the small native installation. Browser/site downloads use `core`,
`models`, `media` and `research` ZIP packs. Original files, model notices, research and diagrams remain
in their original relative paths. Large individual files are split into bounded stored chunks and
reassembled by the supplied standard-library Python helper; do not concatenate ZIPs.

## First offline rehearsal

Download `release_packs.py`, `site-packs.json` and every `site-core-*.zip` from the **same release**.
Check their SHA-256 values against the release's `SHA256SUMS`, retained through your trusted channel.
The pack manifest is an integrity inventory, not a new signing key or trust root.

```sh
python release_packs.py restore --manifest site-packs.json --destination successor-site --groups core
python -m http.server 8080 --bind 127.0.0.1 --directory successor-site
```

Open `http://127.0.0.1:8080/successor/`. Its maintained bounded computation needs no model or credentials.
Some older galleries use optional model/media/research files. Their links are preserved; download the
corresponding packs for those experiences. A cached browser session and a complete model download are
separate prerequisites from the small first rehearsal.

## Complete preservation restore

Download the manifest and **all** packs with its prefix, then restore into a new directory:

```sh
python release_packs.py restore --manifest site-packs.json --destination complete-site
python release_packs.py restore --manifest browser-packs.json --destination complete-insight
```

The helper checks manifest structure, every selected pack's full digest and size, ZIP entries,
individual chunk digests and each reconstructed file before promoting a staged directory. It rejects
links, special files, traversal, duplicate entries, encrypted or compressed chunks, mismatched counts,
unknown schema versions and declared size overruns. An existing destination is never replaced.
Use a new directory for an upgrade or to add optional packs; retain the prior directory for rollback.
The complete site deployed by CI is reconstructed from these exact tested packs without rebuilding.

## Reproducibility and source identity

`release-manifest.json` binds the release version and exact source revision to distributed asset hashes
and sizes, distribution manifests, the workflow, and retained acceptance reports. Each pack manifest
also binds that source revision and records every original file path, byte count and SHA-256 digest.
ZIP timestamps and permissions are deterministic. Packs use stored bytes to make the size ceiling
independent of compression estimates and to bound decompression work.

`successor-preservation.json` inventories the complete pre-SUCCESSOR main revision
`aab4995ee87f7fb575180931c79b8bf86e26d50d`. Every original path remains; original media bytes and Mermaid
blocks are checked against that immutable revision. The earlier factory, README, manuscript and
contract-mirror checks remain required. The inventory records changed source blobs explicitly instead
of treating changed implementation as missing history.

Publication rechecks the size ceiling before any upload. The existing controlled workflow still
requires runtime, regression, types, hooks, real Docker, EVM, browser, model, dependency-audit, installed
wheel, gallery and public-site acceptance. A locally produced archive does not establish that those
remote gates passed. The historical Ed25519 wheel-signature format is unchanged; release packing neither
supplies a signing credential nor fabricates a signature.

## Restauration en français

Téléchargez `release_packs.py`, le manifeste et les archives de la **même version**. Vérifiez leurs
empreintes avec `SHA256SUMS`, conservé par un canal de confiance. Pour la répétition locale sans modèle,
utilisez la première commande avec `--groups core`, puis ouvrez `/successor/` sur le serveur local.
Pour retrouver tous les médias, recherches et modèles, téléchargez toutes les archives et restaurez
sans `--groups`. Chaque fichier distribué reste sous 450 000 000 octets. Le programme vérifie toutes
les données avant d'activer le nouveau dossier et refuse d'écraser un dossier existant. Conservez
l'ancienne installation pour revenir en arrière. Ces vérifications d'intégrité ne confèrent aucune
autorité opérationnelle ni qualification indépendante.
