# Matrix attribution and exact experimental inputs

These are the four fixed Harwell-Boeing matrices cataloged by the [SuiteSparse Matrix Collection](https://sparse.tamu.edu/). The collection's [license statement](https://sparse.tamu.edu/about) assigns the matrices [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Cite Timothy A. Davis and Yifan Hu, *The University of Florida Sparse Matrix Collection*, ACM TOMS 38(1), article 1, 2011, DOI [10.1145/2049662.2049663](https://doi.org/10.1145/2049662.2049663), and the original matrix metadata below.

| Matrix | Original description | Creator / year | Official metadata |
| --- | --- | --- | --- |
| HB/1138_bus | Admittance matrix, 1138-bus power system | D. Tylavsky / 1985 | https://sparse.tamu.edu/HB/1138_bus |
| HB/bcsstk14 | Stiffness matrix, roof of Omni Coliseum, Atlanta | M. Will / 1985 | https://sparse.tamu.edu/HB/bcsstk14 |
| HB/bcsstk18 | Stiffness matrix, R. E. Ginna nuclear power station | M. Will / 1985 | https://sparse.tamu.edu/HB/bcsstk18 |
| HB/bcsstk24 | Symmetric stiffness matrix, winter sports arena | J. Lewis / 1984 | https://sparse.tamu.edu/HB/bcsstk24 |

Editors named by the collection: I. Duff, R. Grimes and J. Lewis.

Official file endpoints returned acquisition errors. `source_provenance.json` lists each pinned public research mirror, commit, source path, Git blob or LFS identity, transport hash and exact numeric Matrix Market payload hash. `manifest.json` fixes the precise compressed files consumed by this study. The numeric Matrix Market bytes were not edited; only the transport was recompressed. During in-memory parsing, duplicate coordinate entries are summed, explicit zero entries removed and CSC indices sorted; no scaling or regularization is applied. Original comments are retained where present. The bcsstk18 research copy contains only its Matrix Market format header, so its descriptive attribution is supplied in this file and the provenance ledger.

Dimensions and expanded nonzero counts agree with official metadata. Byte equality to unavailable official downloads has not been established. A pattern-only bcsstk14 candidate was rejected before any numerical execution and is recorded separately. None of these numerical studies certifies an actual structure, energy installation or power network. Manufactured right-hand sides are synthetic and documented in the protocol.
