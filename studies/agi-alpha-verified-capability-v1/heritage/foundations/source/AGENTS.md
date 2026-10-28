# Instructions for Future Agents

Preserve the repository’s proof-first posture.

## Hard rules

- Do not remove claim boundaries.
- Do not add production, audit, AGI, ROI, legal, tax, security, or mainnet claims unless evidence exists in the repository.
- Do not add secrets or private data.
- Do not add live fund movement.
- Do not publish generated pages that lack claim-boundary language.
- Prefer small, reviewable changes with clear rollback.

## Preferred changes

- Better schemas.
- Better examples.
- Better validator reports.
- Better non-technical guides.
- Better public website clarity.
- Better QA checks.

## Required local checks

```bash
python scripts/validate_repo.py
python scripts/build_site.py
python scripts/verify_site.py
python -m unittest discover -s tests
```
