# Public historical ledger projection

`exchange-public-ledger.sqlite` is a new, sanitized projection of a recovered
simulated exchange ledger. It is **not the original exchange database**, a fresh
confirmation sample, a current market observation, or evidence of real revenue.
The original private database remains unchanged and is deliberately excluded from
the public fixture.

Only the fields read by the installed `reserve-experience/v1` snapshot and
independent SQL verifier are retained. All other tables and columns are omitted,
including private artifacts, encryption material, buyer/task data and the
provider-key hash. The new database is built from selected values into an empty
database; it does not retain deleted SQLite pages. The four public JSON examples
bind the new database hash and a regenerated trusted source capture.

`public-ledger-provenance.json` records original and derived hashes, row counts,
omissions, unchanged arithmetic and the changed capture identity. Its original
hash is an identity reference, not a promise that the private source is public.
The published outcome remains cash 128,994,728, obligations 92,200,000 and free
capacity 36,794,728 in simulated microUSD. Both the original and derived snapshot
and independent verifier accepted these same amounts during sanitization.

With the authorized original already available locally, reproduce the database
using the bounded projector from the repository root and an absent destination:

```sh
python contrib/compounding_discovery/project_public_ledger.py \
  /PATH/TO/RECOVERED/exchange.sqlite /PATH/TO/NEW/exchange-public-ledger.sqlite
```

The projector accepts only the frozen original hash and refuses an existing
destination. Tests exercise the public schema, exact arithmetic and wrong-amount
rejection, and prove omission using an independent synthetic database containing
private markers. No private source or keys are needed to run those tests.
