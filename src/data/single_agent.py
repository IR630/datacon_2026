"""Fetch ChemX single-agent baseline predictions.

Network-agnostic: downloads once from raw.githubusercontent, then reads the local
cache so later runs (and offline machines) work without network.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.baseline_bridge import single_agent_pred_url
from src.utils.io import ensure_dir


def fetch_single_agent_pred(
    domain: str,
    cache_dir: str | Path = "data/cache",
    timeout: int = 45,
    force: bool = False,
) -> pd.DataFrame:
    cache = Path(cache_dir) / f"single_agent_{domain}_pred.csv"
    if cache.exists() and not force:
        return pd.read_csv(cache)
    import requests

    resp = requests.get(single_agent_pred_url(domain), timeout=timeout)
    resp.raise_for_status()
    ensure_dir(cache.parent)
    cache.write_bytes(resp.content)
    return pd.read_csv(cache)
