from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lab.run import Miner


_MINERS: dict[str, type] = {}


def register(name: str, miner_cls: type) -> None:
    _MINERS[name] = miner_cls


def get_miner(name: str) -> Miner:
    key = name.strip().lower()
    if key not in _MINERS:
        known = ", ".join(sorted(_MINERS)) or "(none)"
        raise ValueError(f"Unknown miner {name!r}. Known: {known}")
    return _MINERS[key]()  # type: ignore[return-value]


def list_miners() -> list[str]:
    return sorted(_MINERS)


def _register_defaults() -> None:
    from lab.miners.arxiv.miner import ArxivMiner
    from lab.miners.manuals import ManualsMiner
    from lab.miners.news import NewsMiner
    from lab.miners.ugc import UgcMiner
    from lab.miners.youtube import YoutubeMiner

    register("arxiv", ArxivMiner)
    register("youtube", YoutubeMiner)
    register("manuals", ManualsMiner)
    register("news", NewsMiner)
    register("ugc", UgcMiner)


_register_defaults()
