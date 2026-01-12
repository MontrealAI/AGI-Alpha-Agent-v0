# SPDX-License-Identifier: Apache-2.0
import random

from alpha_factory_v1.core.simulation import SelfRewriteOperator


def test_meme_reuse() -> None:
    rng = random.Random(0)
    op = SelfRewriteOperator(steps=3, rng=rng, templates=["meme"], reuse_rate=1.0)
    result = op("improve quick test")
    assert result == "meme"
    assert op.reuse_count >= 1


def test_meme_disabled() -> None:
    rng = random.Random(0)
    op = SelfRewriteOperator(steps=3, rng=rng, templates=["meme"], reuse_rate=0.0)
    result = op("improve quick test")
    assert result != "meme"


def test_performance_drop() -> None:
    rng1 = random.Random(1)
    op_good = SelfRewriteOperator(steps=1, rng=rng1, templates=["meme"], reuse_rate=1.0)
    score_good = len(op_good("improve quick test"))

    rng2 = random.Random(1)
    op_bad = SelfRewriteOperator(steps=1, rng=rng2, templates=["meme"], reuse_rate=0.0)
    score_bad = len(op_bad("improve quick test"))
    assert score_good < score_bad
