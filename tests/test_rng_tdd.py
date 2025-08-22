from __future__ import annotations

from bingo_gen.rng import create_rng, derive_parallel_seed


def test_py_random_determinism():
    r1 = create_rng("py_random", 12345)
    r2 = create_rng("py_random", 12345)
    seq1 = [r1.randint(1, 100) for _ in range(10)]
    seq2 = [r2.randint(1, 100) for _ in range(10)]
    assert seq1 == seq2


def test_parallel_seed_derivation_stable_and_distinct():
    base = 20250824
    s0 = derive_parallel_seed(base, 0, "build")
    s1 = derive_parallel_seed(base, 1, "build")
    s0b = derive_parallel_seed(base, 0, "build")
    assert s0 != s1
    assert s0 == s0b
