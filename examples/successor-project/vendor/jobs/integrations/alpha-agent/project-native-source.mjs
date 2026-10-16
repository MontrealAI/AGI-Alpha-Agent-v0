// Trusted source identity is shared by sealing and inspection. Freeze its full
// graph so consumers cannot change the authoritative manifests through exports.
function deepFreeze(value) {
  for (const nested of Object.values(value)) {
    if (nested && typeof nested === 'object') deepFreeze(nested);
  }
  return Object.freeze(value);
}

export const ALPHA_NATIVE_SOURCE = deepFreeze({
  "repository": "MontrealAI/AGI-Alpha-Agent-v0",
  "commit": "92e227c007d484323c7fd2a7001b9bb5b229e717",
  "license": "Apache-2.0; vendored agijobs compiler retains MIT provenance",
  "files": [
    {
      "path": "docs/assets/successor/engine.mjs",
      "sha256": "38c4f38978bf9fc29f207bae3adee0755bc6530d04502a36c491cc430787e488"
    },
    {
      "path": "examples/alpha-discovery/engine.mjs",
      "sha256": "452a25348a3209a99fef9eecbd94bdbfafdc9595777dc5d2bd2a70e9245ea850"
    },
    {
      "path": "examples/successor-project/engine.mjs",
      "sha256": "56b187b7d705b458809ba4c76ace0d24f116a8bec32712000c0f6f0463d7efa3"
    },
    {
      "path": "examples/successor-workbench/mission-record.mjs",
      "sha256": "e80338a4c89905e33b6856189080fd22593a7208b078ddf49a58b296b459ba0f"
    },
    {
      "path": "examples/successor-workbench/engine.mjs",
      "sha256": "f36f4c3fa45124901755bbb530a8161e98c164f5a66e9b8f932548f5286c93d7"
    },
    {
      "path": "examples/build-successor/model.mjs",
      "sha256": "8ea94108ef2ed27bce0fcff0b5d312f2e8f6db6584246cc66ab8c1c8d9281175"
    },
    {
      "path": "examples/build-successor/vendor/agijobs/compiler.mjs",
      "sha256": "5e4fc86d78af7a22e915d8b19803fc219cb68b9b73201f47cf1f643f19380762"
    },
    {
      "path": "examples/build-successor/vendor/agijobs/domain.mjs",
      "sha256": "2869bb750a408e12ada19f6d0b216d47c3b9f67fc66039db4372dae8430e47a3"
    },
    {
      "path": "examples/build-successor/vendor/agijobs/integrity.mjs",
      "sha256": "164000134cc9c8b54209c420a348e3e5c324ebf7ff8f71fc84dc44812345c428"
    },
    {
      "path": "examples/build-successor/vendor/agijobs/templates.mjs",
      "sha256": "bc035b1c38b36d2db24031ac92fb193946df9cf4f180120394506a8802be2b31"
    },
    {
      "path": "LICENSE",
      "sha256": "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4"
    },
    {
      "path": "examples/build-successor/vendor/agijobs/LICENSE",
      "sha256": "70842e0e7ae73b3ce65baa06a1c62b466bdb694570301969031cc48d9ac705d1"
    },
    {
      "path": "examples/build-successor/vendor/agijobs/provenance.json",
      "sha256": "92e4fb81d4561dbf251fb8797883fe06a43398d1de395c8469eff606434ebd28"
    }
  ]
});
export const JOBS_COMPILER_SOURCE = deepFreeze({
  "repository": "MontrealAI/AGIJobsv0",
  "commit": "7b21ce05b0b18b46162da66c2f528334101f6f40",
  "files": [
    {
      "path": "packages/successor-core/src/compiler.mjs",
      "sha256": "5e4fc86d78af7a22e915d8b19803fc219cb68b9b73201f47cf1f643f19380762"
    },
    {
      "path": "packages/successor-core/src/domain.mjs",
      "sha256": "2869bb750a408e12ada19f6d0b216d47c3b9f67fc66039db4372dae8430e47a3"
    },
    {
      "path": "packages/successor-core/src/integrity.mjs",
      "sha256": "164000134cc9c8b54209c420a348e3e5c324ebf7ff8f71fc84dc44812345c428"
    },
    {
      "path": "packages/successor-core/src/templates.mjs",
      "sha256": "bc035b1c38b36d2db24031ac92fb193946df9cf4f180120394506a8802be2b31"
    }
  ]
});
export const RECEIVER_SOURCE = deepFreeze({
  "repository": "MontrealAI/AGIJobsv0",
  "adapterVersion": "agijobsv0-project-receiver/v1",
  "files": [
    {
      "path": "integrations/alpha-agent/project-transfer.mjs",
      "sha256": "e33aef0d022333ed1715e01146db9b4b175295904f7f1409e7ede9df3f82d6c3"
    },
    {
      "path": "integrations/alpha-agent/project-receipt.cjs",
      "sha256": "3be27862394e6692e555ad77ee16e9387be11f4633d7255d69bac6c169cfec6b"
    },
    {
      "path": "integrations/alpha-agent/project-cli.mjs",
      "sha256": "46991dc1700bed8316da63388c6231300f4e86975eed4fa27bbaca1a1d03cb35"
    }
  ]
});
