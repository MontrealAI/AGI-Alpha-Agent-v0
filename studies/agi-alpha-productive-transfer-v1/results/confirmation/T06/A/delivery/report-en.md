# Your upgrade decision

scipy 1.10.1 to 1.14.1: statsmodels source-contract assessment

**Next action:** Resolve the stated source or dispatch gap and run the relevant integration check before deciding.

Argument binding only. Review behavior and security before changing a deployed dependency.

**Complete monetary cost: unknown**. Unknown: setup, integration, upkeep, authoring/inference, customer effort.

## Selected calls

### T06-call-01

The selected call shape binds to both captured declarations.

```python
simpson(d2[:, :, None] * d2[:, None, :], x=x, axis=0)
```

The call-to-declaration target is supplied, and its runtime identity remains unproved.

- [consumer · L259–L259](https://github.com/statsmodels/statsmodels/blob/df825806c588b13e78d7788ddf33a8c61e106544/statsmodels/gam/smooth_basis.py#L259-L259) · SHA256 `1dd25ede73509245ff3cd179fef2a3e3fa53153ba0dfc501fa4b83f64fa76560`
- [b0 · L536–L664](https://github.com/scipy/scipy/blob/c1ed5ece8ffbf05356a22a8106affcd11bd3aee0/scipy/integrate/_quadrature.py#L536-L664) · SHA256 `944dcbbe8eac825688e350f3850693dcaf1da4699d626eeb8535d140a04ad015`
- [a0 · L535–L697](https://github.com/scipy/scipy/blob/92d2a8592782ee19a1161d0bf3fc2241ba78bb63/scipy/integrate/_quadrature.py#L535-L697) · SHA256 `c8f3365d3a909ef535cba39bbb62f195eb99be142278c46d6b1cd71c2350b5bc`

## What remains unresolved

- Selected calls and inert argument binding only; not full application, dependency security or release approval.
- A declared target is a conditional source relationship, not proof of runtime dispatch.
- An accepted binding does not establish behavior, values, types, imports or successful argument evaluation.
- Unselected calls and runtime monkeypatching remain unassessed. Source origin is supplied by the public-input curator; hashes bind bytes, not authorship.

Historical sources and recorded evidence; these pins are not current production recommendations.

Source record: decision-record.json. Canonical cost inputs/analysis: automated-costs.json / cost-analysis.json. Nontransactional ledger: ledger.json / ledger-analysis.json.
