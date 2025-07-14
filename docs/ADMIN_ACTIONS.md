[See docs/DISCLAIMER_SNIPPET.md](DISCLAIMER_SNIPPET.md)

# GitHub Actions Access Notes

This repository restricts manual workflows to the repository owner or designated administrators.

- Each workflow uses the custom **Ensure Repository Owner** action which exits if `github.actor` does not match `github.repository_owner`.
- The main CI pipeline specifies the `ci-on-demand` environment. Configure this environment under **Settings → Environments** to require administrator approval before jobs run.
- Manual jobs appear in the **Actions** tab with a **Run workflow** button but will fail immediately for unauthorized users.

Only trusted maintainers should have permission to approve the protected environment or dispatch these workflows.
