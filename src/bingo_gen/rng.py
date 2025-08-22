from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import List, Sequence


try:  # optional dependency
    import numpy as _np  # type: ignore
except Exception:  # pragma: no cover - optional
    _np = None


@dataclass
class RandomSource:
    engine: str

    def randint(self, a: int, b: int) -> int:
        raise NotImplementedError

    def random(self) -> float:
        raise NotImplementedError

    def choice(self, seq: Sequence[int]) -> int:
        raise NotImplementedError

    def shuffle(self, arr: List[int]) -> None:
        raise NotImplementedError

    def sample(self, seq: Sequence[int], k: int) -> List[int]:
        raise NotImplementedError


class PyRandomSource(RandomSource):
    def __init__(self, seed: int):
        super().__init__(engine="py_random")
        self._rng = random.Random(seed)

    def randint(self, a: int, b: int) -> int:
        return self._rng.randint(a, b)

    def random(self) -> float:
        return self._rng.random()

    def choice(self, seq: Sequence[int]) -> int:
        return self._rng.choice(list(seq))

    def shuffle(self, arr: List[int]) -> None:
        self._rng.shuffle(arr)

    def sample(self, seq: Sequence[int], k: int) -> List[int]:
        return self._rng.sample(list(seq), k)


class NumpyPCG64Source(RandomSource):  # pragma: no cover - covered when numpy present
    def __init__(self, seed: int):
        if _np is None:
            raise RuntimeError("numpy is not installed; install bingo-gen[pcg]")
        super().__init__(engine="numpy_pcg64")
        self._rng = _np.random.Generator(_np.random.PCG64(seed))

    def randint(self, a: int, b: int) -> int:
        return int(self._rng.integers(low=a, high=b + 1))

    def random(self) -> float:
        return float(self._rng.random())

    def choice(self, seq: Sequence[int]) -> int:
        return int(self._rng.choice(seq))

    def shuffle(self, arr: List[int]) -> None:
        self._rng.shuffle(arr)

    def sample(self, seq: Sequence[int], k: int) -> List[int]:
        idxs = self._rng.choice(len(seq), size=k, replace=False)
        return [seq[int(i)] for i in idxs]


def create_rng(engine: str, seed: int) -> RandomSource:
    engine = (engine or "py_random").strip().lower()
    if engine == "py_random":
        return PyRandomSource(seed)
    if engine == "numpy_pcg64":
        return NumpyPCG64Source(seed)
    raise ValueError(f"Unsupported RNG engine: {engine}")


def derive_parallel_seed(base_seed: int, index: int, purpose: str) -> int:
    """Derive per-task seed from base seed, index, and purpose using sha256.

    Returns a 63-bit positive integer suitable for seeding common RNGs.
    """
    s = f"{base_seed}|{index}|{purpose}".encode("utf-8")
    digest = hashlib.sha256(s).digest()
    # take first 8 bytes, mask to 63 bits to ensure non-negative
    val = int.from_bytes(digest[:8], byteorder="big") & ((1 << 63) - 1)
    return val


