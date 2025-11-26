[See docs/DISCLAIMER_SNIPPET.md](docs/DISCLAIMER_SNIPPET.md)

## Breaking Changes Policy
Incompatible updates are announced in advance whenever possible and remain deprecated for at least one minor release. Each release includes a dedicated `### Breaking Changes` section describing removed features or behavioural differences. Consult that section when upgrading.

The initial release is tagged `v0.1.0-alpha`.

For the full changelog, see [docs/CHANGELOG.md](docs/CHANGELOG.md).

### Migration Note
Production modules previously under `src/` now reside in
`alpha_factory_v1.core`.
Update imports accordingly.

## [Unreleased]
- Upgraded `rdkit` to version `2023.9.5` for Python 3.12 support.
- Adopted 18-decimal AGIALPHA token (`0xA61a3B3a130a9c20768EEBF97E21515A6046a1fA`) and removed multi-token support along with `setToken` functions. Existing deployments should scale token amounts by `1e12` when migrating from the previous 6-decimal token.

## [0.1.0-alpha] - 2024-05-01
- Initial alpha release.
- Git tag `v0.1.0-alpha`.
- This tag points at commit `0ff79a4f`.
 - If cloning from a snapshot without tags, recreate it using:
    ```bash
    # Verify the release tag
    git tag -l v0.1.0-alpha
    # Recreate the tag when missing
    ./scripts/create_release_tag.sh HEAD
    git push origin v0.1.0-alpha
    ```
 - The package exposes `alpha_factory_v1.__version__ = "0.1.0-alpha"` at this release.
