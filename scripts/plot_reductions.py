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

from common import (
    BenchMatrix,
    Tool,
    get_matrix_base_name,
    get_matrix_filename_mtx,
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


def draw_inpla(
    results: Results,
    matrix: BenchMatrix,
    thread_counts: list[int],
    ax: Axes,
):
    filename_base = get_matrix_base_name(matrix)
    benchmark_result = results.inpla_results[matrix["algorithm"]][filename_base]
    reductions = []
    error = []
    for thread_count in thread_counts:
        times = list(map(get_inpla_reductions, benchmark_result[str(thread_count)]))
        reductions.append(np.nanmean(times))
        error.append(np.nanstd(times))
    if not (reductions == reductions[0]).all():
        print("inpla", reductions, error)
    ax.errorbar(
        thread_counts,
        reductions,
        yerr=error,
        color="#F0E442",
        linestyle="-.",
        label="QTreeInpla",
    )


def get_vine_reductions(result: str) -> int:
    return int(result.split(" ")[2][:-1])


def draw_vine(
    results: Results,
    matrix: BenchMatrix,
    thread_counts: list[int],
    ax: Axes,
):
    filename_base = get_matrix_base_name(matrix)
    benchmark_result = results.vine_results[matrix["algorithm"]][filename_base]
    reductions = []
    error = []
    for thread_count in thread_counts:
        times = list(map(get_vine_reductions, benchmark_result[str(thread_count)]))
        reductions.append(np.mean(times))
        error.append(np.std(times))
    if not (reductions == reductions[0]).all():
        print("vine", reductions, error)
    ax.errorbar(
        thread_counts,
        reductions,
        yerr=error,
        color="#CC79A7",
        linestyle=(0, (3, 1, 1, 1, 1, 1)),
        label="Vine",
    )


def plot_graph(
    results: Results,
    matrix: BenchMatrix,
    processed_results_path: Path,
    thread_counts: list[int],
):
    print("Processing", matrix["algorithm"], matrix["name"], end="...", flush=True)
    fig, ax = plt.subplots(layout="constrained")

    ax.set_title(
        matrix["algorithm"]
        + " on "
        + matrix["name"]
        + (", reordered" if matrix["reorder"] else "")
    )
    ax.set_xticks(thread_counts)
    ax.set_xlabel("Threads")
    ax.set_ylabel("Reductions")
    ax.set_yscale("log")

    draw_vine(results, matrix, thread_counts, ax)
    draw_inpla(results, matrix, thread_counts, ax)

    fig.legend(loc="outside lower center", ncols=2)

    result_path = processed_results_path / (
        "inpla_vs_vine_reductions_"
        + matrix["algorithm"]
        + "_"
        + matrix["name"]
        + ("_reordered" if matrix["reorder"] else "")
        + ".pdf"
    )
    plt.savefig(result_path, bbox_inches="tight")
    print("Drawn", result_path)


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
    max_thread_count: Annotated[int, typer.Option] = 0,
):
    print("*** Reading results ***")
    results = load_results(raw_results_path)
    print("")

    with open(matrices_spec_path, "r", encoding="utf-8") as m_file:
        matrices: list[BenchMatrix] = yaml.safe_load(m_file)
    enabled_matrices = filter(lambda matrix: matrix["enabled"], matrices)
    inpla_vine_matrices = filter(
        lambda matrix: (
            (Tool.INPLA in matrix["tools"]) and (Tool.VINE in matrix["tools"])
        ),
        enabled_matrices,
    )

    if thread_count <= 0:
        if max_thread_count <= 0:
            nproc = os.cpu_count()
            if nproc is None:
                raise RuntimeError("Cannot get nproc")
        else:
            nproc = max_thread_count
        thread_counts = [1] + list(range(2, nproc + 1, 2))
    else:
        thread_counts = [thread_count]

    print("*** Drawing plots ***")
    processed_results_path.mkdir(parents=True, exist_ok=True)
    for matrix in inpla_vine_matrices:
        plot_graph(results, matrix, processed_results_path, thread_counts)


if __name__ == "__main__":
    typer.run(main)
