from enum import StrEnum, auto
from typing import TypedDict


class BenchmarkType(StrEnum):
    BFS = auto()
    SSSP = auto()
    TC = auto()


class Tool(StrEnum):
    NETWORKX = auto()
    FSHARP = auto()
    INPLA = auto()
    LAGRAPH = auto()


class BenchMatrix(TypedDict):
    name: str
    enabled: bool
    algorithm: BenchmarkType
    tools: list[Tool]
    reorder: bool
    link: str


def get_matrix_base_name(matrix: BenchMatrix) -> str:
    return matrix["name"] + ("_reordered" if matrix["reorder"] else "")


def get_matrix_filename_mtx(matrix: BenchMatrix) -> str:
    return get_matrix_base_name(matrix) + ".mtx"


def get_matrix_filename_in(matrix: BenchMatrix) -> str:
    return get_matrix_base_name(matrix) + ".in"
