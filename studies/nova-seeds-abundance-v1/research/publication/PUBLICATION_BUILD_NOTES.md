# Publication build and review notes

The scientific source, protocol, statistical analysis and original audit remained frozen throughout publication work. The final confirmation was run once. Presentation-only code under `research/publication/` consumes its unchanged results.

The first all-page PDF review found two isolated section headings, a few single-line paragraph splits, stretched table text, and a practical reproduction issue: TeX ligatures rendered command-line `--` flags as en dashes. The final layout adds heading space reservation, widow/orphan protection, ragged table columns, correct cover leading and disabled monospaced ligatures. Extracted final PDF commands contain literal ASCII `--mode` and `--out`.

The complete standalone TeX embeds four generated vector PGF sources and the bibliography. TeX writes those embedded vector files locally during compilation; no external asset or download is needed. An initial direct PGF-in-macro approach failed because Matplotlib's category-code definitions are not safe inside that macro argument; the supported embedded-file approach and the PGF math macro were then qualified. These were presentation build repairs, not scientific changes. The original structured PDF remains canonical because the standalone PGF rebuild uses different TeX figure-text metrics.

The shared workspace encountered actual ENOSPC during development and later packaging. The incomplete development data and wrapper failure remain retained. The successful confirmation was already durably preserved before layout. Recovery removed only this task's reproducible upstream/dependency caches and redundant already-backed-up copies; no other task's work, frozen source or completed experimental records were removed.

The exact pinned repository PDF parser is used locally with its hash-pinned pypdf dependency. That check covers passive PDF contents, not a full catalogue import, hosted source qualification, formal review, merge or deployment. The source/artifact proposal stays separate from the existing coordinator's shared catalogue and Pages ownership.
