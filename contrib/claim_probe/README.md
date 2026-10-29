# AGI ALPHA FLYWHEEL — Construct a falsifying investigation

Vincent Boucher | President of MONTREAL.AI

The Blue Sky purpose is to make previously inaccessible investigations possible. This local seed checks an explicit continuous mathematical claim, constructs a counterexample or a proof, and returns independently checked evidence. It is an established-method implementation, with no demonstrated scientific breakthrough or physical certification. The conventional symbolic control is stronger on some tasks.

## English quickstart

Install the candidate wheel in an isolated environment with its declared dependencies. Use a new output directory:

```sh
mkdir claim-example
alpha-agent claim-probe example --output claim-example/task.json
alpha-agent claim-probe run claim-example/task.json --output claim-example/result.json
alpha-agent claim-probe check claim-example/task.json --result claim-example/result.json
```

Acceptance requires JSON `accepted: true`. A useful conclusion also requires `decisive: true`. `UNKNOWN` preserves the unresolved claim; it is never a safety pass. In this example a negative exact polynomial value refutes the universal claim. The witness gives an actual model input to investigate. It is not a measured physical observation.

The default uses the stronger ordinary exact symbolic method (SymPy optional extra `claim-probe`). Select `--method bernstein` to inspect the bounded experimental constructor and its possible UNKNOWN result. The new `joint` command reads a separately declared multi-affine box claim and returns its independent check.

The input accepts degree at most eight, rational strings, a rational interval, immutable scope, source references and explicit computation caps. Files are created exclusively. Existing files, final symlinks, duplicate JSON fields, invalid numbers, source changes and tampered proofs refuse. There is no shell, wallet, model API, or network execution in this command.

## Démarrage en français

```sh
mkdir exemple-preuve
alpha-agent claim-probe example --language fr --output exemple-preuve/question.json
alpha-agent claim-probe run exemple-preuve/question.json --language fr --output exemple-preuve/resultat.json
alpha-agent claim-probe check exemple-preuve/question.json --language fr --result exemple-preuve/resultat.json
```

Le résultat vérifie uniquement le modèle mathématique déclaré. `REFUTED` donne une entrée et une valeur négative exactes. `PROVED` nécessite une preuve complète; `UNKNOWN` conserve l'incertitude. Une preuve numérique ne qualifie ni une application physique, ni un acheteur réel, ni un règlement financier.

## Source and ecosystem boundary

Alpha owns the installed constructor, checker and evidence. Fleet preserves bounded execution, separate review and provisioning gates. Jobs v0 retains AGIALPHA with 18 decimals; Manager retains the alternative USDC route with 6 decimals. Current native discovery receivers select a different exact Alpha revision and refuse this current source. Their local inspector tests do not qualify the new task schema. No currency conversion, duplicate billing, chain settlement, release or publication is inferred.

Simulated purchasing is evaluated separately with funded escrow, an independent checker, gated artifact release and refunds. No real purchase or customer contact occurs. Technical acceptance, financial viability, optional construction, native execution and release decisions each need their own evidence.
