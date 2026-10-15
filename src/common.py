import json
import logging
import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum, auto
from operator import attrgetter
from pathlib import Path
from typing import Concatenate, TypedDict

from dataclass_wizard import YAMLWizard
from toolz.itertoolz import unique

type RunToolCallable = Callable[
    Concatenate[Matrix, int, ...], subprocess.CompletedProcess[str]
]

LOGGER_NAME = "app"

DEFAULT_MATRICES_SPEC_PATH = Path("matrices.yaml")
DEFAULT_MATRICES_PATH = Path("matrices")
DEFAULT_RAW_RESULTS_PATH = Path("results") / "raw"
DEFAULT_DEPENDENCIES_PATH = Path("dependencies")
DEFAULT_TOOLS_PATH = Path("tools")
DEFAULT_LOGS_PATH = Path("logs")

MTX_EXTENSION = ".mtx"
IN_EXTENSION = ".in"
REORDERED_SUFFIX = "_reordered"

MAKE = "make"

logger = logging.getLogger(LOGGER_NAME)


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


# @dataclass would be fancier, but would require many setattrs and getattrs
class Results(TypedDict):
    bfs: dict[str, dict[int, list[str]]]
    sssp: dict[str, dict[int, list[str]]]
    tc: dict[str, dict[int, list[str]]]


def make_empty_results() -> Results:
    return Results(
        bfs={},
        sssp={},
        tc={},
    )


def get_enabled_matrices(matrices_spec_path: Path) -> list[Matrix]:
    matrices: list[Matrix] = Matrix.from_yaml_file(matrices_spec_path)  # type: ignore
    return list(filter(lambda matrix: matrix.enabled, matrices))


def get_enabled_matrices_for_tool(matrices_spec_path: Path, tool: Tool) -> list[Matrix]:
    matrices: list[Matrix] = Matrix.from_yaml_file(matrices_spec_path)  # type: ignore
    return list(
        filter(lambda matrix: matrix.enabled and (tool in matrix.tools), matrices)
    )


def get_unique_by_name_matrices(matrices: list[Matrix]) -> list[Matrix]:
    return list(unique(matrices, attrgetter("name")))


def get_matrix_base_name(matrix: Matrix) -> str:
    return matrix.name + (REORDERED_SUFFIX if matrix.reorder else "")


def get_matrix_filename_mtx(matrix: Matrix) -> str:
    return get_matrix_base_name(matrix) + MTX_EXTENSION


def get_matrix_filename_in(matrix: Matrix) -> str:
    return get_matrix_base_name(matrix) + IN_EXTENSION


def comma_separated_str_to_int_list(str: str | None) -> list[int] | None:
    if str is None:
        return None
    else:
        tmp = [int(x) for x in str.split(",")]
        return tmp


def run_tool_many_times(
    matrix: Matrix,
    thread_count: int,
    run_count: int,
    run_tool: RunToolCallable,
    **kwargs,
):
    results = []
    logger.info("Running with %s threads", thread_count)
    for i in range(run_count):
        logger.info("Starting run %s", i)
        result = run_tool(matrix, thread_count, **kwargs)
        if result.returncode != 0:
            logger.warning(
                "Process %s exited with code %s",
                result.args,
                result.returncode,
            )
        results.append(result.stdout)
    return results


def run_benchmark(
    matrix: Matrix,
    thread_counts: list[int] | None,
    run_count: int,
    run_tool: RunToolCallable,
    **kwargs,
):
    if thread_counts is None:
        nproc = os.cpu_count()
        if nproc is None:
            raise RuntimeError("Cannot get nproc")
        thread_counts = [1] + list(range(2, nproc + 1, 2))

    result: dict[int, list[str]] = {}

    for thread_count in thread_counts:
        result[thread_count] = run_tool_many_times(
            matrix, thread_count, run_count, run_tool, **kwargs
        )

    return result


def run_benchmarks(
    matrices: list[Matrix],
    thread_counts: list[int] | None,
    run_count: int,
    run_tool: RunToolCallable,
    **kwargs,
):
    results: Results = make_empty_results()

    for matrix in matrices:
        base_name = get_matrix_base_name(matrix)
        logger.info("Benchmarking %s on %s", matrix.algorithm, base_name)
        results[str(matrix.algorithm)][base_name] = run_benchmark(
            matrix, thread_counts, run_count, run_tool, **kwargs
        )

    return results


def get_timestamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="minutes")


def write_results(results: Results, raw_results_path: Path, tool: Tool):
    raw_results_path.mkdir(parents=True, exist_ok=True)
    results_path = raw_results_path / (get_timestamp() + "_" + str(tool) + ".json")
    with open(results_path, "w", encoding="utf-8") as r_file:
        json.dump(results, r_file, indent=4)

    logger.info("Successfully wrote results to %s", results_path)
