from enum import StrEnum, auto
from typing import TypedDict


class BenchmarkType(StrEnum):
    BFS = auto()
    SSSP = auto()
    TC = auto()


class Tool(StrEnum):
    NETWORKX = auto()


class BenchMatrix(TypedDict):
    name: str
    enabled: bool
    algorithm: BenchmarkType
    tools: list[Tool]
    reorder: bool
    link: str
