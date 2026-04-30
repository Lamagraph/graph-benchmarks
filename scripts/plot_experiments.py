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
    fsharp_results: dict
    inpla_results: dict
    lagraph_results: dict
    networkx_results: dict
    vine_results: dict


def load_results(raw_results_path: Path) -> Results:
    try:
        fsharp_results_json = sorted(
            raw_results_path.glob("*_fsharp.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[0]
        with open(fsharp_results_json, "r", encoding="utf-8") as f:
            fsharp_results = json.load(f)
            print("Read", fsharp_results_json)
    except FileNotFoundError:
        print("QTreeFSharp results weren't found")
        fsharp_results = dict()

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
        lagraph_results_json = sorted(
            raw_results_path.glob("*_lagraph.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[0]
        with open(lagraph_results_json, "r", encoding="utf-8") as f:
            lagraph_results = json.load(f)
            print("Read", lagraph_results_json)
    except FileNotFoundError:
        print("LAGraph results weren't found")
        lagraph_results = dict()

    try:
        networkx_results_json = sorted(
            raw_results_path.glob("*_networkx.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[0]
        with open(networkx_results_json, "r", encoding="utf-8") as f:
            networkx_results = json.load(f)
            print("Read", networkx_results_json)
    except FileNotFoundError:
        print("QTreeFSharp results weren't found")
        networkx_results = dict()

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

    return Results(
        fsharp_results, inpla_results, lagraph_results, networkx_results, vine_results
    )


def draw_fsharp(
    results: Results,
    matrix: BenchMatrix,
    thread_counts: list[int],
    ax: Axes,
):
    benchmark_results = list(
        filter(
            lambda res: (
                get_matrix_filename_mtx(matrix).casefold() in res["FullName"].casefold()
            ),
            results.fsharp_results[matrix["algorithm"]]["Benchmarks"],
        )
    )[0]
    mean_sec = benchmark_results["Statistics"]["Mean"] / 1e9
    sd_sec = benchmark_results["Statistics"]["StandardDeviation"] / 1e9
    ax.plot(
        thread_counts,
        [mean_sec] * len(thread_counts),
        color="#0072B2",
        linestyle=":",
        label="QTreeFSharp",
    )
    ax.fill_between(
        thread_counts,
        mean_sec - sd_sec,
        mean_sec + sd_sec,
        color="#0072B2",
        linestyle=":",
        alpha=0.2,
    )


def get_inpla_time(result: str) -> float:
    if "Error".casefold() in result.casefold():
        return math.nan
    return float(result.splitlines()[-1].split(" ")[-2])


def draw_inpla(
    results: Results,
    matrix: BenchMatrix,
    thread_counts: list[int],
    ax: Axes,
):
    filename_base = get_matrix_base_name(matrix)
    benchmark_result = results.inpla_results[matrix["algorithm"]][filename_base]
    time = []
    error = []
    for thread_count in thread_counts:
        times = list(map(get_inpla_time, benchmark_result[str(thread_count)]))
        time.append(np.nanmean(times))
        error.append(np.nanstd(times))
    ax.errorbar(
        thread_counts,
        time,
        yerr=error,
        color="#F0E442",
        linestyle="-.",
        label="QTreeInpla",
    )


def get_lagraph_time(result: str) -> float:
    return float(result.splitlines()[-1].split(" ")[-2])


def draw_lagraph(
    results: Results,
    matrix: BenchMatrix,
    thread_counts: list[int],
    ax: Axes,
):
    filename_base = get_matrix_base_name(matrix)
    benchmark_result = results.lagraph_results[matrix["algorithm"]][filename_base]
    time = []
    error = []
    for thread_count in thread_counts:
        times = list(map(get_lagraph_time, benchmark_result[str(thread_count)]))
        time.append(np.mean(times))
        error.append(np.std(times))
    ax.errorbar(
        thread_counts,
        time,
        yerr=error,
        color="#E69F00",
        linestyle="--",
        label="LaGraph",
    )


def draw_networkx(
    results: Results,
    matrix: BenchMatrix,
    thread_counts: list[int],
    ax: Axes,
):
    benchmark_results = list(
        filter(
            lambda res: (
                res["extra_info"]["algorithm"] == matrix["algorithm"]
                and res["extra_info"]["graph_name"] == get_matrix_base_name(matrix)
            ),
            results.networkx_results["benchmarks"],
        )
    )[0]
    mean_sec = benchmark_results["stats"]["mean"]
    sd_sec = benchmark_results["stats"]["stddev"]
    ax.plot(
        thread_counts,
        [mean_sec] * len(thread_counts),
        color="#000000",
        linestyle="-",
        label="NetworkX",
    )
    ax.fill_between(
        thread_counts,
        mean_sec - sd_sec,
        mean_sec + sd_sec,
        color="#000000",
        linestyle="-",
        alpha=0.2,
    )


def get_vine_time(result: str) -> float:
    return float(result.split(" ")[-2])


def draw_vine(
    results: Results,
    matrix: BenchMatrix,
    thread_counts: list[int],
    ax: Axes,
):
    filename_base = get_matrix_base_name(matrix)
    benchmark_result = results.vine_results[matrix["algorithm"]][filename_base]
    time = []
    error = []
    for thread_count in thread_counts:
        times = list(map(get_vine_time, benchmark_result[str(thread_count)]))
        time.append(np.mean(times))
        error.append(np.std(times))
    ax.errorbar(
        thread_counts,
        time,
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
    ax.set_ylabel("Time, s")
    ax.set_yscale("log")

    if Tool.VINE in matrix["tools"]:
        draw_vine(results, matrix, thread_counts, ax)
    if Tool.INPLA in matrix["tools"]:
        draw_inpla(results, matrix, thread_counts, ax)
    if Tool.FSHARP in matrix["tools"]:
        draw_fsharp(results, matrix, thread_counts, ax)
    if Tool.NETWORKX in matrix["tools"]:
        draw_networkx(results, matrix, thread_counts, ax)
    if Tool.LAGRAPH in matrix["tools"]:
        draw_lagraph(results, matrix, thread_counts, ax)

    fig.legend(loc="outside lower center", ncols=5)

    result_path = processed_results_path / (
        matrix["algorithm"]
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
    for matrix in enabled_matrices:
        plot_graph(results, matrix, processed_results_path, thread_counts)


if __name__ == "__main__":
    typer.run(main)
