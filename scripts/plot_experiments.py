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

from common import BenchMatrix


@dataclass
class Results:
    fsharp_results: dict
    inpla_results: dict
    lagraph_results: dict
    networkx_results: dict


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

    return Results(fsharp_results, inpla_results, lagraph_results, networkx_results)


def draw_fsharp(
    results: Results,
    matrix: BenchMatrix,
    thread_counts: list[int],
    ax: Axes,
):
    benchmark_results = list(
        filter(
            lambda res: res["Parameters"] == ("MatrixName=" + matrix["name"] + ".mtx"),
            results.fsharp_results[matrix["algorithm"]]["Benchmarks"],
        )
    )[0]
    mean_sec = benchmark_results["Statistics"]["Mean"] / 10e9
    sd_sec = benchmark_results["Statistics"]["StandardDeviation"] / 10e9
    ax.plot(
        thread_counts,
        [mean_sec] * len(thread_counts),
        color="blue",
        label="QTreeFSharp",
    )
    ax.fill_between(
        thread_counts, mean_sec - sd_sec, mean_sec + sd_sec, color="blue", alpha=0.2
    )


def get_inpla_time(result: str) -> float:
    if "Error" in result:
        return math.nan
    return float(result.splitlines()[-1].split(" ")[-2])


def draw_inpla(
    results: Results,
    matrix: BenchMatrix,
    thread_counts: list[int],
    ax: Axes,
):
    benchmark_result = results.inpla_results[matrix["algorithm"]][matrix["name"]]
    time = []
    error = []
    for thread_count in thread_counts:
        times = list(map(get_inpla_time, benchmark_result[str(thread_count)]))
        time.append(np.nanmean(times))
        error.append(np.nanstd(times))
    ax.errorbar(thread_counts, time, yerr=error, color="red", label="QTreeInpla")


def get_lagraph_time(result: str) -> float:
    return float(result.splitlines()[-1].split(" ")[-2])


def draw_lagraph(
    results: Results,
    matrix: BenchMatrix,
    thread_counts: list[int],
    ax: Axes,
):
    benchmark_result = results.lagraph_results[matrix["algorithm"]][matrix["name"]]
    time = []
    error = []
    for thread_count in thread_counts:
        times = list(map(get_lagraph_time, benchmark_result[str(thread_count)]))
        time.append(np.mean(times))
        error.append(np.std(times))
    ax.errorbar(thread_counts, time, yerr=error, color="green", label="LaGraph")


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
                and res["extra_info"]["graph_name"] == matrix["name"]
            ),
            results.networkx_results["benchmarks"],
        )
    )[0]
    mean_sec = benchmark_results["stats"]["mean"]
    sd_sec = benchmark_results["stats"]["stddev"]
    ax.plot(
        thread_counts, [mean_sec] * len(thread_counts), color="yellow", label="NetworkX"
    )
    ax.fill_between(
        thread_counts, mean_sec - sd_sec, mean_sec + sd_sec, color="yellow", alpha=0.2
    )


def plot_graph(
    results: Results,
    matrix: BenchMatrix,
    processed_results_path: Path,
    thread_counts: list[int],
):
    fig, ax = plt.subplots(layout="constrained")

    ax.set_title(matrix["algorithm"] + " on " + matrix["name"])
    ax.set_xticks(thread_counts)
    ax.set_xlabel("Threads")
    ax.set_ylabel("Time, s")
    # ax.set_yscale("log")

    # draw_fsharp(results, matrix, thread_counts, ax)
    # draw_inpla(results, matrix, thread_counts, ax)
    draw_lagraph(results, matrix, thread_counts, ax)
    draw_networkx(results, matrix, thread_counts, ax)

    fig.legend(loc="outside lower center", ncols=4)

    result_path = processed_results_path / (
        matrix["algorithm"] + "_" + matrix["name"] + ".pdf"
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
):
    print("*** Reading results ***")
    results = load_results(raw_results_path)
    print("")

    with open(matrices_spec_path, "r", encoding="utf-8") as m_file:
        matrices: list[BenchMatrix] = yaml.safe_load(m_file)
    enabled_matrices = filter(lambda matrix: matrix["enabled"], matrices)

    if thread_count <= 0:
        nproc = os.cpu_count()
        if nproc is None:
            raise RuntimeError("Cannot get nproc")
        thread_counts = [1] + list(range(2, nproc + 1, 2))
    else:
        thread_counts = [thread_count]

    print("*** Drawing plots ***")
    processed_results_path.mkdir(parents=True, exist_ok=True)
    for matrix in enabled_matrices:
        plot_graph(results, matrix, processed_results_path, thread_counts)


if __name__ == "__main__":
    typer.run(main)
