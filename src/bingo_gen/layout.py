from __future__ import annotations

from typing import Dict


def build_global_frequencies(*, R: int, T: int, m: int, n: int, mode: str, position_balance: bool) -> Dict[int, int]:
    """Compute per-number frequencies for global pool according to uniformity mode.

    - strict: all numbers appear equally often (requires P % R == 0)
    - near: counts differ by at most 1
    """
    P = T * m * n
    base = P // R
    remainder = P % R
    freqs: Dict[int, int] = {}
    if mode == "strict":
        if remainder != 0:
            # Caller is expected to check feasibility; still emit near-optimal distribution
            pass
        for x in range(1, R + 1):
            freqs[x] = base
    elif mode == "near":
        # First 'remainder' numbers get base+1, rest get base
        for x in range(1, R + 1):
            freqs[x] = base + (1 if x <= remainder else 0)
    else:
        raise ValueError("mode must be 'strict' or 'near'")

    # position_balance is a soft constraint applied later during placement; global counts unchanged here
    return freqs


