# SPDX-License-Identifier: Apache-2.0
"""Explicit, source-bound LF repair for reviewed capability checkouts.

No Git command, index/configuration change or generator runs here. Unexpected
content refuses the entire plan; original raw bytes stay in a private backup.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tempfile
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[1]
CATALOG = "docs/successor/capabilities/sources.json"
SOURCE_HASH = "644258ac21cc938aff861d02ad728e8f3c9716f6ea78700acc35e4d7400eebf2"
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024
# Reviewed canonical bytes. Each catalogue digest authenticates its closed source
# paths/hashes, so an edited catalogue cannot choose its own repair targets.
EXTRA_FILES = {
    "examples/successor-capability/discovery-lab-reproduce.mjs": (
        7903,
        "21aabff4e543789f6ddbc074fcf7e0a3ea706cada55345f680f4edcb7afac894",
    ),
    "docs/successor/capabilities/index.html": (
        782569,
        "7ce110be53cf4c699984c0cfd20e0e7d7434c463a676fe1dfb9498589e5319d3",
    ),
    "docs/successor/capabilities/sources.json": (
        5416,
        "9cddd00ed38a3500efeaac8977bf3db46363face0cfe56e713ec91750662e09a",
    ),
    "docs/alpha_factory_v1/demos/successor/capabilities/index.html": (
        782651,
        "bb8013b57a00134ef6c80b3ba840b013ec9dca76ec1ed14e2738a9a5bbc6cc9a",
    ),
    "docs/alpha_factory_v1/demos/successor/capabilities/sources.json": (
        5416,
        "9cddd00ed38a3500efeaac8977bf3db46363face0cfe56e713ec91750662e09a",
    ),
    "docs/service-worker.js": (23275, "fb8fd61467254b4af045443aa5f0575259b26129290958bf667c67a7deda75bb"),
    "docs/assets/service-worker.js": (23707, "d2b72a7115364078ab7c2212fab53c43452e8af6d644d1a16926c61a594619b0"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26299,
        "0b067ee54afeea5a22b7737deb752168d5d2ff6a4d7404a406579ea3f79df247",
    ),
}
ENTERPRISE_PARENT_SOURCE_HASH = "c64f26fac13d73dc4fb4a591ac6c87c314fc3f8e44449307db77ca4c7df2622f"
ENTERPRISE_PARENT_EXTRA_FILES = EXTRA_FILES | {
    "docs/successor/capabilities/index.html": (
        933102,
        "5c55a089546345eea1a9907cf736f437f28a58ab468342e73308a6ac2aee1634",
    ),
    "docs/successor/capabilities/sources.json": (
        6894,
        "0d8207718f1757e2d5c6707909825f034bb79fe7afcc61ac95eb9b6ffe228e5f",
    ),
    "docs/alpha_factory_v1/demos/successor/capabilities/index.html": (
        933190,
        "364aa919294001c1c9a154289a97c77abbc349be4824a1a34352d35e6397353c",
    ),
    "docs/alpha_factory_v1/demos/successor/capabilities/sources.json": (
        6894,
        "0d8207718f1757e2d5c6707909825f034bb79fe7afcc61ac95eb9b6ffe228e5f",
    ),
    "docs/service-worker.js": (23275, "095d2b9ab423ff133ff5ba5ae062b2ec471d10a87c6c24b27df9858765641107"),
    "docs/assets/service-worker.js": (23707, "ba23c3e95d420d2792109aea99afa653e9cdd46f9ce645d26c1f3059dffb16d4"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26299,
        "20e4dbd3e3780a361bff61b9536d3c22548c558bb87e98b9a2a42e165af6a3e9",
    ),
}
ENTERPRISE_SOURCE_HASH = "54769dbfde99ae13708a33292866f0ca7e6b8b7792a7a944f76bf2fbf1de1358"
ENTERPRISE_EXTRA_FILES = ENTERPRISE_PARENT_EXTRA_FILES | {
    "docs/successor/capabilities/index.html": (
        933603,
        "804f83eab8077d45a2e741a334d4c92be5209de1e9781ea865ed9ffc8487d97e",
    ),
    "docs/successor/capabilities/sources.json": (
        6894,
        "d1c3cb9a5c3eb96e9e5eb111b83a713786ec18ed1213a407cd77bbaf018c5adb",
    ),
    "docs/alpha_factory_v1/demos/successor/capabilities/index.html": (
        933691,
        "0d9235cf4e9050498c470c44cba74223d1c6481b3abcaf209d72ba794417a071",
    ),
    "docs/alpha_factory_v1/demos/successor/capabilities/sources.json": (
        6894,
        "d1c3cb9a5c3eb96e9e5eb111b83a713786ec18ed1213a407cd77bbaf018c5adb",
    ),
    "docs/service-worker.js": (23275, "7b6204079cd78d5cb92e91a9b6af4bfde99c01e765292697289fcfbff8a83f5d"),
    "docs/assets/service-worker.js": (23707, "0db9a2730d24548c730601bd56a5fae3dab82359df6402736f29c0b87378108c"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26299,
        "e02eb78e93d637475c5db53a2fe21efcabf85b410fd0ba450f155d7379dd652a",
    ),
}
# The 1.39 edition retains the same scientific catalogue and complete source
# closure. Only these three generated gallery workers have new reviewed bytes.
ENTERPRISE_139_EXTRA_FILES = ENTERPRISE_EXTRA_FILES | {
    "docs/service-worker.js": (23275, "ac2035bc13defd9e1118969eae165106d5eac952ee7d69b54f54c05f0664ff44"),
    "docs/assets/service-worker.js": (23707, "76eb433503202b0020a1df522afed3686b5f6d846634ff481bf57dced64685d6"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26299,
        "a36cc805ecbbefad9ac5b393c9aa42312f60d952802aa8ae7ff896d536d49549",
    ),
}
# The corrected 1.39 release metadata changes the gallery cache digest. Retain
# the initial edition and admit this complete, separately reviewed byte closure.
ENTERPRISE_139_RELEASE_EXTRA_FILES = ENTERPRISE_139_EXTRA_FILES | {
    "docs/service-worker.js": (23275, "93f8bf1fdab5d1af5cc4940f71617033ba35892cf19f8ea943cd147f877e77ad"),
    "docs/assets/service-worker.js": (23707, "00f8c57a5914aa30e686a72ce1954199262546ecb6ee22e4fb6e33f2b58b278f"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26299,
        "ec3b9aacbbe712af09575219d9164f5058970c70fa4900c0e0daa2b028e516d0",
    ),
}
# Moving the retained enterprise preview outside the paper renderer's markers
# creates one further exact cache edition; every prior edition stays admitted.
ENTERPRISE_139_PRESENTATION_EXTRA_FILES = ENTERPRISE_139_RELEASE_EXTRA_FILES | {
    "docs/service-worker.js": (23275, "ac1621a5e9efd104e56ff3865c0784e22a968975dc7b8465682b5528e9e967fd"),
    "docs/assets/service-worker.js": (23707, "64654fce9864c5f792e6b7e5bb595d85366ae4491ba179f7595e1bfa24d5e161"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26299,
        "be9396acf43738b48a233c24517e8a3d06a8b1a36a00448b50be7e8792b7b8a3",
    ),
}
# The complete enterprise-paper catalogue keeps the same scientific source closure.
# Admit its final 1.40 gallery workers as one whole edition; preserve all prior
# editions and reject combinations of their individually valid worker bytes.
FOUNDRY_140_EXTRA_FILES = ENTERPRISE_139_PRESENTATION_EXTRA_FILES | {
    "docs/service-worker.js": (23275, "7d0d5084198377c0c0d0cf55c6d0c7d3c1036d60781dfc8e575f58311d575823"),
    "docs/assets/service-worker.js": (23707, "24e955673e33c603f768a84aa013e446eaa21c80c6d2f5f284f731c8c3e05816"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26299,
        "4154e0b378cd411eca9e1f9630cd191632f96f06fdc1492a9bfd10d719db0907",
    ),
}
# The three bilingual guides and reconciled Discoverability add four cache inputs.
# Admit only this complete generated worker edition; all older editions remain exact.
RESEARCH_GUIDES_140_EXTRA_FILES = FOUNDRY_140_EXTRA_FILES | {
    "docs/service-worker.js": (23479, "6a7d7a7b226a9fc4cd1293e4de891a120b843024b6ab9ae2dd6fc6cb773f5269"),
    "docs/assets/service-worker.js": (23915, "f0fa0894af4f9388a6a0145d6ab660b394b8250c595c6d6d7c60ff529c83fda2"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26531,
        "857aa6fbb8549585329634c1c57865d2b25045daf9c5baf8fb5e9350841752ae",
    ),
}

# The corrected companion/site presentation advances only the three deterministic
# gallery workers. Admit this one complete 1.41 edition, retaining all eight
# historical editions and refusing mixtures of their otherwise valid bytes.
COMPANION_141_EXTRA_FILES = RESEARCH_GUIDES_140_EXTRA_FILES | {
    "docs/service-worker.js": (23479, "fbaf34fa291db4b564447f3ab2973ab0cc8d888499647f494d33c907cdcd8c77"),
    "docs/assets/service-worker.js": (23915, "ef26e24e1f8121fab9e6d0d7e060e163f2f8fd2692805fba9d52424371c6ab81"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26531,
        "19084de384bd92618dc3078f9b10e7f97a74207403026c3812751ab4f9107039",
    ),
}

# The 1.41.1 input-snapshot patch changes only this complete generated cache edition.
# Retain every prior edition; source admission still rejects mixed worker bytes.
WORKBENCH_1411_EXTRA_FILES = COMPANION_141_EXTRA_FILES | {
    "docs/service-worker.js": (23479, "96e6ff02fe1d1e19dd6c41f8bda185cfc4a04ea7fa59784704ef21a2e24f22c7"),
    "docs/assets/service-worker.js": (23915, "810710143b37cefdcff04666da7a5026e8a88c494302f8651510c69f767f85b6"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26531,
        "3ae68c4862b07c2c9538f2be37e5bf73f32a6161b345e0aad0b86a20d17295bf",
    ),
}


# The additive browser guide retains the scientific sources and admits one whole cache edition.
TI_GUIDE_142_EXTRA_FILES = WORKBENCH_1411_EXTRA_FILES | {
    "docs/service-worker.js": (23501, "5c44f328bff2ee3837eef10b755aabad609492e556a9099fe67185457b4bbde8"),
    "docs/assets/service-worker.js": (23938, "237ecc3ce3c8d82b0ada7c856d68ee1b7a7e154f222e6886af3f45ca8dc9f9d6"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26560,
        "2e6fd8bdacfe80d99f017a692a4545d7fdf3c1751367288f385d588a7479a5ab",
    ),
}


# This finite-operation edition preserves the scientific closure and every earlier cache edition.
SOURCE_OPERATION_143_EXTRA_FILES = TI_GUIDE_142_EXTRA_FILES | {
    "docs/service-worker.js": (23501, "7387c1e7ece8b4f6a7fa39c096678ba2ecccbfd1d59da23ac15bed58c03041a5"),
    "docs/assets/service-worker.js": (23938, "35ee39e25c24b61df9bc21b67596017cadd3e236da1b6c1bc47252b276d4dba0"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26560,
        "2153db651113b5b9cb317c60615f548e0b6bff3ea56f2e6ce0910688c516cad6",
    ),
}

# The bounded Strategy engineering release changes only the complete generated
# gallery cache edition; retain every historical edition and scientific source.
STRATEGY_144_EXTRA_FILES = SOURCE_OPERATION_143_EXTRA_FILES | {
    "docs/service-worker.js": (23501, "431c7e7860f44bffcede643128acfa05d4d84c1ddaa26352ac5000060aa0631e"),
    "docs/assets/service-worker.js": (23938, "19ddc910d7cf5e5adb452890d282233813bb2bc0aa42278abaeabbbba7c0d5c6"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26560,
        "e2d55209f31ad4b282e215fabbbf0f2544f398d71c23827387335bf6da8abc1c",
    ),
}

# The 2026-10-26 paper publication retains the complete scientific closure.
# Admit only its exact three-worker edition; preserve all historical editions.
PAPERS_20261026_EXTRA_FILES = STRATEGY_144_EXTRA_FILES | {
    "docs/service-worker.js": (
        23501,
        "d52a0859e4c4d8bf5b4c671beaa76ee44260057df59d496d6fa0d70c1b2f4438",
    ),
    "docs/assets/service-worker.js": (
        23938,
        "dd5752fa2577c376e31f4754b180c8cb1826ecfd6237c0cf10e7ea7527980b15",
    ),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26560,
        "09a14aca276b431cd6e2d369fcdf83dfca40c96101a21ac1027109a223a79040",
    ),
}

# Exact Next Upgrade publication candidate; older complete editions remain valid.
NEXT_UPGRADE_20261026_EXTRA_FILES = STRATEGY_144_EXTRA_FILES | {
    "docs/service-worker.js": (
        23501,
        "bdae48eb479f68189b2102267dc2c2a6e71e15a51ce035f51e44753c606a0c21",
    ),
    "docs/assets/service-worker.js": (
        23938,
        "1c8d664bdc82a62e2a556dc4e32c78474111df851567a10223648c09e578a6f6",
    ),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26560,
        "44267c58e069bdbd9b44877368066cea83d4ef7336913ecaefae6f2441bfe931",
    ),
}

# Exact Profitable Work publication candidate; preserve every older complete edition.
PROFITABLE_WORK_20261027_EXTRA_FILES = STRATEGY_144_EXTRA_FILES | {
    "docs/service-worker.js": (
        23501,
        "558ce6e044dfbf6f5d330f67aedfa7f02ce276b09578334ed38a9401aa4b6d47",
    ),
    "docs/assets/service-worker.js": (
        23938,
        "99aa41c0ca3be166621612ff5110d70a2f651459380a7ecf777c2337f6699ebf",
    ),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26560,
        "6fc4239d456bd3b0474a935e6f7d12310621513f6f82288da27ae46f2dce0854",
    ),
}

# Exact additive Flywheel 1.45 edition. Reviewed as a whole; prior editions remain immutable.
FLYWHEEL_145_EXTRA_FILES = PROFITABLE_WORK_20261027_EXTRA_FILES | {
    "docs/service-worker.js": (23528, "3c23a31d0aaca17395035d12da5d9670cac784b6a51234e01162dfa415e20aab"),
    "docs/assets/service-worker.js": (23966, "a6d4ad60a3c0f80155063a953fd7172d2c55cf0e6d8903d45db7159cf6c536a6"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26594,
        "70ae12f9748ca77701c42411281b71870a2c7b34b216ba4d048bfbad31f62a38",
    ),
}

# Exact sequential protected Flywheel 1.46 edition; retain every prior whole edition.
PROTECTED_FLYWHEEL_146_EXTRA_FILES = FLYWHEEL_145_EXTRA_FILES | {
    "docs/service-worker.js": (23528, "f5aef029f75b2f8b7da784acae899566065885f48a5a05499d3cf9ad031041c0"),
    "docs/assets/service-worker.js": (23966, "71c5f34a108fe9d069c0e611963a1582142bf1796d73213c6fd00655024ad509"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26594,
        "4c49c657e4271266dc0b26b646c39da6ca12b120571a02fb120a72f54e45cdc4",
    ),
}

# Exact paper-reader patch edition; preserve every prior complete worker profile.
PAPER_READERS_1461_EXTRA_FILES = PROTECTED_FLYWHEEL_146_EXTRA_FILES | {
    "docs/service-worker.js": (23649, "45d5d9b5930a9665aa7b0728b129ececfef861d786d52bfe19aa8025c0310aa4"),
    "docs/assets/service-worker.js": (24089, "8855c44e10a18d15e44fa2418d912bd75c226abfec6daff35f249fff2c350e02"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26729,
        "326f182573c0bc370b5efbd8a7d9bced6e0ddedd8033d7f9b5596abe5c9d2e89",
    ),
}

# Exact connected Insight 1.47 edition; every historical profile remains immutable.
INSIGHT_FRONTIER_147_EXTRA_FILES = PAPER_READERS_1461_EXTRA_FILES | {
    "docs/service-worker.js": (23649, "de5815981d4eef8056a8dda1302fc7ed60f1d48b3bb09e70c15502f4e383926d"),
    "docs/assets/service-worker.js": (24089, "70c2e651da23c750b2d0ba834e092aa6904a4347e04bf3393477ca7f6b457fbf"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26729,
        "bd55ce1a7de1db9d5b0b4f8088b793a047199bd49fd387796a1f56126f7ae965",
    ),
}

# Exact post-receipt-guard candidate; keep the original unpublished 1.47 edition intact.
INSIGHT_FRONTIER_147_POST_GUARD_EXTRA_FILES = INSIGHT_FRONTIER_147_EXTRA_FILES | {
    "docs/service-worker.js": (23649, "926119de5946ece7233bac3084deb735c5ce63964d32708c6146cc535f0e695c"),
    "docs/assets/service-worker.js": (24089, "5028ae800f527ecec69054d90ea764ec03447a35a1f8e0e7da74780b9c373f34"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26729,
        "c9c1b5787dc78f2c6a0da5aba7b80950b6a78844b440768bfecc04fa4e3979dc",
    ),
}

# Exact current-authority review candidate; retain all earlier complete byte editions.
INSIGHT_FRONTIER_147_REVIEW_AUTHORITY_EXTRA_FILES = INSIGHT_FRONTIER_147_POST_GUARD_EXTRA_FILES | {
    "docs/service-worker.js": (23649, "357308e5afd03495e75cfe557ccff8fc42c6c008e8c1b2b814138b92642eade9"),
    "docs/assets/service-worker.js": (24089, "0b0f9987d46e5c652d54f961b631cc68db78688da30321ff6b1b6e9b645183dd"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26729,
        "e8a05eaf3ccfbeea86ea9318bc66f2f382682c483a40792d76f9087eb2d32f65",
    ),
}

# Complete proposed discovery Flywheel successor; every predecessor remains exact.
FLYWHEEL_147_EXTRA_FILES = PAPER_READERS_1461_EXTRA_FILES | {
    "docs/service-worker.js": (23649, "f585d406396e500da306a8d10bb27498573332a9149e04794fbddb97365b1836"),
    "docs/assets/service-worker.js": (24089, "74990f5b2c3d134a00d1958383f8332ffd1fdfcd350ffd9235ecf832eb72dc65"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26729,
        "2edba968136cf0aa8c9911990b1fe244950e620fae032ceb91b363768a9b9a9e",
    ),
}

# Exact cross-owner successor; every earlier owner/child profile remains immutable.
RECONCILED_FLYWHEEL_147_EXTRA_FILES = INSIGHT_FRONTIER_147_REVIEW_AUTHORITY_EXTRA_FILES | {
    "docs/service-worker.js": (23649, "dc60056fcda731f1cc61c47d3dfd449210e82d0356760d053911b536f51a0485"),
    "docs/assets/service-worker.js": (24089, "bb66233d182bf8cadd96bd7bbdfdb7b66bd7dc06c6c27290f85aedffb75c0ef6"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26729,
        "58dd9778d1304277e0e3709cac531faa4e7cf8b8a1c02fd2df82261e9f131fd3",
    ),
}

# Exact current enterprise-acceptance candidate; keep all predecessor editions intact.
INSIGHT_FRONTIER_147_ENTERPRISE_ACCEPTANCE_EXTRA_FILES = INSIGHT_FRONTIER_147_REVIEW_AUTHORITY_EXTRA_FILES | {
    "docs/service-worker.js": (23649, "3e03df48a33790526091917aec7223b5b8c84eb820a5a927ea2cde7b803520de"),
    "docs/assets/service-worker.js": (24089, "c0b2123977d6f95ac3c09ab9e20db418484107d0f8a14893bd2ba5e74b941127"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26729,
        "06eca2a88af6bd6a50f15da4165a4e70c6015a388ecd9e4beba280ef3089d593",
    ),
}

# One complete connected owner delivery edition; preserve all25 predecessors.
CONNECTED_DELIVERY_147_EXTRA_FILES = INSIGHT_FRONTIER_147_ENTERPRISE_ACCEPTANCE_EXTRA_FILES | {
    "docs/service-worker.js": (23649, "923be9f30774f7e2f64992279cec28998a422e02e1fac65427db122ea8decd94"),
    "docs/assets/service-worker.js": (24089, "9b6538d46269b194f585fda6dcdef08f01a2b6e1b124010d2f48e6ec22e5da60"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26729,
        "ce562f326447e99f0c3cf2cc623bdcb7e9873f27a0cd0f89bb34d14f9ec839ad",
    ),
}

FRONTIER_DELIVERY_147_EXTRA_FILES = CONNECTED_DELIVERY_147_EXTRA_FILES | {
    "docs/service-worker.js": (23649, "b10442101f412c84313369d628c80aa2ed731bb99b04058209b75eb82f790265"),
    "docs/assets/service-worker.js": (24089, "7285d054d941b0ca75df99972385505b2dec6cdff73ef0ecc4f9ec68a5db08e2"),
    "docs/alpha_factory_v1/demos/alpha_agi_insight_v1/service-worker.js": (
        26729,
        "22d839d6ede9cd38ca791f98f07b2d5d2aa27ba96bb803813673e85ab3b1dba3",
    ),
}

SourceProfile = tuple[str, int, int, dict[str, tuple[int, str]]]


class Record(TypedDict):
    path: str
    raw: bytes
    canonical: bytes
    status: os.stat_result


class RefreshResult(TypedDict):
    schema: str
    sourceHash: str
    checked: int
    needsRefresh: list[str]
    applied: bool
    backupDirectory: str | None


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read(root: Path, name: str) -> tuple[bytes, os.stat_result]:
    parts = PurePosixPath(name).parts
    if not parts or name != "/".join(parts) or any(p in {"", ".", ".."} for p in parts) or "\\" in name:
        raise ValueError("Invalid fixed capability path")
    if PurePosixPath(name).is_absolute():
        raise ValueError("Absolute capability path")
    path = root
    for part in parts[:-1]:
        path /= part
        if not stat.S_ISDIR(path.lstat().st_mode):
            raise ValueError("Capability parent must be a direct directory: " + name)
    path /= parts[-1]
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE_BYTES:
        raise ValueError("Capability input must be a bounded regular file: " + name)
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise ValueError("Capability input changed while opening: " + name)
        raw = stream.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError("Capability input exceeds repair bound: " + name)
    return raw, opened


def _canonical(raw: bytes, expected: str, size: int | None, name: str) -> bytes:
    canonical = raw.replace(b"\r\n", b"\n")
    if b"\r" in canonical or _hash(canonical) != expected or size is not None and len(canonical) != size:
        raise ValueError("Private or unexpected capability bytes; nothing refreshed: " + name)
    if raw not in {canonical, canonical.replace(b"\n", b"\r\n")}:
        raise ValueError("Mixed line endings require manual review; nothing refreshed: " + name)
    return canonical


def _source_profiles(raw: bytes) -> list[SourceProfile]:
    digest = _hash(raw.replace(b"\r\n", b"\n"))
    profiles = []
    for source_hash, source_count, file_count, extra in (
        (SOURCE_HASH, 41, 49, EXTRA_FILES),
        (ENTERPRISE_PARENT_SOURCE_HASH, 53, 61, ENTERPRISE_PARENT_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, ENTERPRISE_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, ENTERPRISE_139_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, ENTERPRISE_139_RELEASE_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, ENTERPRISE_139_PRESENTATION_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, FOUNDRY_140_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, RESEARCH_GUIDES_140_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, COMPANION_141_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, WORKBENCH_1411_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, TI_GUIDE_142_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, SOURCE_OPERATION_143_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, STRATEGY_144_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, PAPERS_20261026_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, NEXT_UPGRADE_20261026_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, PROFITABLE_WORK_20261027_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, FLYWHEEL_145_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, PROTECTED_FLYWHEEL_146_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, PAPER_READERS_1461_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, INSIGHT_FRONTIER_147_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, INSIGHT_FRONTIER_147_POST_GUARD_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, INSIGHT_FRONTIER_147_REVIEW_AUTHORITY_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, FLYWHEEL_147_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, RECONCILED_FLYWHEEL_147_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, INSIGHT_FRONTIER_147_ENTERPRISE_ACCEPTANCE_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, CONNECTED_DELIVERY_147_EXTRA_FILES),
        (ENTERPRISE_SOURCE_HASH, 53, 61, FRONTIER_DELIVERY_147_EXTRA_FILES),
    ):
        if digest == extra[CATALOG][1]:
            profiles.append((source_hash, source_count, file_count, extra))
    if not profiles:
        raise ValueError("Private or unexpected capability bytes; nothing refreshed: " + CATALOG)
    return profiles


def _fingerprint(value: os.stat_result) -> tuple[int, ...]:
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_mode, value.st_uid, value.st_gid)


def _unchanged(root: Path, records: list[Record]) -> None:
    for record in records:
        raw, status = _read(root, record["path"])
        if raw != record["raw"] or _fingerprint(status) != _fingerprint(record["status"]):
            raise ValueError("Checkout changed during repair; stop and retain backup: " + record["path"])


def _profile_records(root: Path, catalog_raw: bytes, profile: SourceProfile) -> list[Record]:
    """Validate the entire fixed byte edition without writing or accepting a mixture."""
    source_hash, source_count, file_count, extra = profile
    catalog_bytes = _canonical(catalog_raw, extra[CATALOG][1], extra[CATALOG][0], CATALOG)
    catalog = json.loads(catalog_bytes)
    sources = catalog["sources"]
    if (
        catalog["schema"] != "successor-capability-source/v1"
        or len(sources) != source_count
        or catalog["sourceHash"] != source_hash
        or _hash(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()) != source_hash
    ):
        raise ValueError("Unsupported capability source identity")
    expected: dict[str, tuple[int | None, str]] = {name: (None, digest) for name, digest in sources.items()}
    expected.update(extra)
    if len(expected) != file_count:
        raise ValueError("Unsupported capability repair closure")
    records: list[Record] = []
    for name, (size, digest) in sorted(expected.items()):
        raw, status = _read(root, name)
        canonical = _canonical(raw, digest, size, name)
        records.append({"path": name, "raw": raw, "canonical": canonical, "status": status})
    if sum(len(r["raw"]) for r in records) > MAX_TOTAL_BYTES:
        raise ValueError("Capability repair exceeds total bound")
    return records


def refresh(root: Path = ROOT, *, apply: bool = False, backup_parent: Path | None = None) -> RefreshResult:
    """Check one complete exact closure before any backup or canonical-byte replacement."""
    root = root.resolve(strict=True)
    catalog_raw, _ = _read(root, CATALOG)
    failure: ValueError | None = None
    for profile in _source_profiles(catalog_raw):
        try:
            records = _profile_records(root, catalog_raw, profile)
        except ValueError as error:
            failure = error
        else:
            source_hash, _, file_count, _ = profile
            break
    else:
        assert failure is not None
        raise failure
    changed = [r for r in records if r["raw"] != r["canonical"]]
    result: RefreshResult = {
        "schema": "capability-lf-checkout-refresh/v1",
        "sourceHash": source_hash,
        "checked": file_count,
        "needsRefresh": [r["path"] for r in changed],
        "applied": False,
        "backupDirectory": None,
    }
    if not apply or not changed:
        result["applied"] = apply
        return result
    parent = (backup_parent or Path(tempfile.gettempdir())).resolve(strict=True)
    if not parent.is_dir() or parent == root or parent.is_relative_to(root):
        raise ValueError("Choose an existing backup parent outside the checkout")
    _unchanged(root, records)
    backup = Path(tempfile.mkdtemp(prefix="capability-lf-backup-", dir=parent))
    backup.chmod(0o700)
    backup_files: list[dict[str, str | int]] = []
    manifest = {"schema": "capability-lf-original-backup/v1", "sourceHash": source_hash, "files": backup_files}
    # Every original is retained before staging or replacing any checkout file.
    for record in records:
        destination = backup / "files" / record["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(record["raw"])
        destination.chmod(0o600)
        backup_files.append(
            {
                "path": record["path"],
                "bytes": len(record["raw"]),
                "sha256": _hash(record["raw"]),
                "mode": stat.S_IMODE(record["status"].st_mode),
            }
        )
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    staged: list[tuple[Record, Path]] = []
    applied: list[str] = []
    try:
        _unchanged(root, records)
        for record in changed:
            target = root / record["path"]
            descriptor, temporary = tempfile.mkstemp(prefix="." + target.name + ".lf-", dir=target.parent)
            staged.append((record, Path(temporary)))
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(record["canonical"])
                stream.flush()
                os.fsync(stream.fileno())
                if hasattr(os, "fchmod"):
                    os.fchmod(stream.fileno(), stat.S_IMODE(record["status"].st_mode))
            if not hasattr(os, "fchmod"):
                Path(temporary).chmod(stat.S_IMODE(record["status"].st_mode))
        _unchanged(root, records)
        for record, temporary in staged:
            raw, status = _read(root, record["path"])
            if raw != record["raw"] or _fingerprint(status) != _fingerprint(record["status"]):
                raise ValueError("Checkout changed during repair: " + record["path"])
            os.replace(temporary, root / record["path"])
            applied.append(record["path"])
    except (OSError, ValueError) as error:
        (backup / "result.json").write_text(json.dumps({"applied": applied, "complete": False}) + "\n")
        raise RuntimeError("Refresh stopped; original bytes retained at " + str(backup)) from error
    finally:
        for _, temporary in staged:
            temporary.unlink(missing_ok=True)
    (backup / "result.json").write_text(json.dumps({"applied": applied, "complete": True}) + "\n")
    result.update(applied=True, backupDirectory=str(backup))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--apply", action="store_true", help="Explicitly refresh only prevalidated CRLF capability files"
    )
    parser.add_argument(
        "--backup-parent", type=Path, help="Existing external directory for a new private retained backup"
    )
    arguments = parser.parse_args()
    print(json.dumps(refresh(arguments.root, apply=arguments.apply, backup_parent=arguments.backup_parent), indent=2))
