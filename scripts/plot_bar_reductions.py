from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
from typing import Annotated

from matplotlib import pyplot as plt
from matplotlib.axes import Axes
import numpy as np
import typer
import yaml
import pandas as pd

from common import (
    BenchMatrix,
    Tool,
    get_matrix_base_name,
)


@dataclass
class Results:
    inpla_results: dict
    vine_results: dict


def load_results(raw_results_path: Path) -> Results:
    try:
        inpla_results_json = sorted(
            raw_results_path.glob("*_inpla.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[0]
        with open(inpla_results_json, "r", encoding="utf-8") as f:
            inpla_results = json.load(f)
            print("Read", inpla_results_json)
    except FileNotFoundError:
        print("Inpla results weren't found")
        inpla_results = dict()

    try:
        vine_results_json = sorted(
            raw_results_path.glob("*_vine.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[0]
        with open(vine_results_json, "r", encoding="utf-8") as f:
            vine_results = json.load(f)
            print("Read", vine_results_json)
    except FileNotFoundError:
        print("QTreeVine results weren't found")
        vine_results = dict()

    return Results(inpla_results, vine_results)


def get_inpla_reductions(result: str) -> float:
    if "Error".casefold() in result.casefold():
        return math.nan
    lines = result.splitlines()[1:]
    interaction_counts = map(lambda line: float(line.split(" ")[0][1:]), lines)
    return sum(interaction_counts)


def find_inpla_reductions(
    results: Results, matrix: BenchMatrix, thread_count: int
) -> int:
    filename_base = get_matrix_base_name(matrix)
    benchmark_result = results.inpla_results[matrix["algorithm"]][filename_base]
    reductions = list(map(get_inpla_reductions, benchmark_result[str(thread_count)]))
    first_not_nan = next(x for x in reductions if not math.isnan(x))
    return math.trunc(first_not_nan)


# def draw_inpla(
#     results: Results,
#     matrix: BenchMatrix,
#     thread_counts: list[int],
#     ax: Axes,
# ):
#     filename_base = get_matrix_base_name(matrix)
#     benchmark_result = results.inpla_results[matrix["algorithm"]][filename_base]
#     reductions = []
#     error = []
#     for thread_count in thread_counts:
#         times = list(map(get_inpla_reductions, benchmark_result[str(thread_count)]))
#         reductions.append(np.nanmean(times))
#         error.append(np.nanstd(times))
#     ax.errorbar(
#         thread_counts,
#         reductions,
#         yerr=error,
#         color="#F0E442",
#         linestyle="-.",
#         label="QTreeInpla",
#     )


def get_vine_reductions(result: str) -> int:
    return int(result.split(" ")[2][:-1])


def find_vine_reductions(
    results: Results, matrix: BenchMatrix, thread_count: int
) -> int:
    filename_base = get_matrix_base_name(matrix)
    benchmark_result = results.vine_results[matrix["algorithm"]][filename_base]
    return get_vine_reductions(benchmark_result[str(thread_count)][1])


# def draw_vine(
#     results: Results,
#     matrix: BenchMatrix,
#     thread_counts: int,
#     ax: Axes,
# ):
#     filename_base = get_matrix_base_name(matrix)
#     benchmark_result = results.vine_results[matrix["algorithm"]][filename_base]
#     reductions = []
#     error = []
#     times = list(map(get_vine_reductions, benchmark_result[str(thread_counts)]))
#     reductions.append(np.mean(times))
#     error.append(np.std(times))
#     ax.errorbar(
#         thread_counts,
#         reductions,
#         yerr=error,
#         color="#CC79A7",
#         linestyle=(0, (3, 1, 1, 1, 1, 1)),
#         label="Vine",
#     )


# def plot_graph(
#     results: Results,
#     matrix: BenchMatrix,
#     processed_results_path: Path,
#     thread_count: int,
# ):
#     print("Processing", matrix["algorithm"], matrix["name"], end="...", flush=True)
#     fig, ax = plt.subplots(layout="constrained")

#     ax.set_title(
#         matrix["algorithm"]
#         + " on "
#         + matrix["name"]
#         + (", reordered" if matrix["reorder"] else "")
#     )
#     ax.set_xticks(thread_count)
#     ax.set_xlabel("Threads")
#     ax.set_ylabel("Reductions")
#     ax.set_yscale("log")

#     draw_vine(results, matrix, thread_count, ax)
#     draw_inpla(results, matrix, thread_count, ax)

#     fig.legend(loc="outside lower center", ncols=2)

#     result_path = processed_results_path / (
#         "inpla_vs_vine_reductions_"
#         + matrix["algorithm"]
#         + "_"
#         + matrix["name"]
#         + ("_reordered" if matrix["reorder"] else "")
#         + ".pdf"
#     )
#     plt.savefig(result_path, bbox_inches="tight")
#     print("Drawn", result_path)


def main(
    matrices_spec_path: Annotated[
        Path,
        typer.Option(
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ] = Path("matrices.yaml"),
    raw_results_path: Annotated[
        Path,
        typer.Option(
            file_okay=False,
            dir_okay=True,
            readable=True,
            writable=True,
            resolve_path=True,
        ),
    ] = Path("results") / "raw",
    processed_results_path: Annotated[
        Path,
        typer.Option(
            file_okay=False,
            dir_okay=True,
            readable=True,
            writable=True,
            resolve_path=True,
        ),
    ] = Path("results") / "processed",
    thread_count: Annotated[int, typer.Option] = 0,
):
    print("*** Reading results ***")
    results = load_results(raw_results_path)
    print("")

    with open(matrices_spec_path, "r", encoding="utf-8") as m_file:
        matrices: list[BenchMatrix] = yaml.safe_load(m_file)
    enabled_matrices = filter(lambda matrix: matrix["enabled"], matrices)
    inpla_vine_matrices = list(
        filter(
            lambda matrix: (
                (Tool.INPLA in matrix["tools"]) and (Tool.VINE in matrix["tools"])
            ),
            enabled_matrices,
        )
    )

    if thread_count <= 0:
        thread_count = 1

    algorithms = []
    matrix_names = []
    tools = []
    reduction_count = []

    for matrix in inpla_vine_matrices:
        algorithms.append(matrix["algorithm"])
        matrix_names.append(get_matrix_base_name(matrix))
        tools.append("inpla")
        reduction_count.append(find_inpla_reductions(results, matrix, thread_count))

        algorithms.append(matrix["algorithm"])
        matrix_names.append(get_matrix_base_name(matrix))
        tools.append("vine")
        reduction_count.append(find_vine_reductions(results, matrix, thread_count))

    df = pd.DataFrame(
        {
            "algorithm": algorithms,
            "matrix": matrix_names,
            "tool": tools,
            "reduction_count": reduction_count,
        }
    )
    df = df.pivot(
        index=["algorithm", "matrix"], columns="tool", values="reduction_count"
    )
    ax = df.plot.bar(
        color={"vine": "#CC79A7", "inpla": "#F0E442"},
        rot=45,
        legend=True,
        figsize=(20, 10),
        logy=True,
    )
    plt.savefig("abc1.pdf", bbox_inches="tight")

    # print("*** Drawing plots ***")
    # fig, ax = plt.subplots(layout="constrained")

    # x = np.arange(len(inpla_vine_matrices))
    # width = 0.25  # the width of the bars

    # processed_results_path.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    typer.run(main)
