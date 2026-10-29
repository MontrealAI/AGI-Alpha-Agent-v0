# Installed supplier delta CLI

This additive packaging change includes only the existing four
`contrib.enterprise_campaign` Python modules. It does not add an `alpha-agent`
command, vendor the broader campaign, change the catalogue producer, or expand
network, payment, customer-delivery or execution authority.

After installing the resulting wheel, use the same explicit local command:

```sh
python -m contrib.enterprise_campaign.delta_delivery \
  --before catalogue.csv --delta supplier.csv --keys sku \
  --write-fields price --decimal-fields price --output new-review-package
```

Input paths are supplied by the operator; examples and private evidence are not
required wheel resources. The command refuses to overwrite an existing output
directory. Its local package is development evidence, not customer acceptance.

The installed qualification builds the reviewed wheel, installs it in a fresh
environment without dependencies, checks that all four imported modules originate
there and equal source bytes, and runs from outside the checkout with Python
isolated mode. It checks a fixed expected output, byte-exact rollback, unchanged
source and two refusal controls. This deliberately qualifies this standard-library
CLI only, not a dependency-complete Alpha installation. Full release installation
and acceptance remain separate.

The prior 1.47 invention packaging metadata is preserved verbatim in
`tests/fixtures/fast-delivery-packaging-147-metadata.json`, identified by public
main commit `a6b2d869a7736e7c414d7d615d86c616c2f82615`. Transition tests permit only
the exact additional namespace and the corresponding project/profile digest
updates. The earlier 1.47 metadata snapshot, 13 finite lint exceptions and 241
legacy source pins remain unchanged.
