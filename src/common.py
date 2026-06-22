from dataclasses import dataclass
from enum import StrEnum, auto
from pathlib import Path
from typing import List

from dataclass_wizard import YAMLWizard
import yaml


class Algorithm(StrEnum):
    BFS = auto()
    SSSP = auto()
    TC = auto()


class Tool(StrEnum):
    NETWORKX = auto()
    FSHARP = auto()
    INPLA = auto()
    LAGRAPH = auto()
    VINE = auto()


@dataclass
class Matrix(YAMLWizard):
    name: str
    enabled: bool
    algorithm: Algorithm
    tools: list[Tool]
    reorder: bool
    link: str


def get_enabled_matrices(matrices_spec_path: Path) -> list[Matrix]:
    matrices: List[Matrix] = Matrix.from_yaml_file(matrices_spec_path)  # type: ignore
    return list(filter(lambda matrix: matrix.enabled, matrices))
