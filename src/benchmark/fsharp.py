import json
import logging
from pathlib import Path
import re
import subprocess
from typing import Annotated

import typer

from ..common import (
    Algorithm,
    Matrix,
    Tool,
    get_enabled_matrices_for_tool,
    get_matrix_filename_mtx,
    get_unique_by_name_matrices,
    write_results,
    Results,
)
from ..type_aliases import DirPathOption, FilePathOption

app = typer.Typer()
log = logging.getLogger("rich")


DOTNETBENCHMARK_RUN_COMMAND = [
    "dotnet",
    "run",
    "--configuration",
    "Release",
    "--project",
    "QuadTree.Benchmark",
    "--",
    "--filter",
    "*",
    "--exporters",
    "json",
]


def get_fsharp_algorithm_name(algorithm: Algorithm) -> str:
    match algorithm:
        case Algorithm.BFS:
            return "BFS"
        case Algorithm.SSSP:
            return "SSSP"
        case Algorithm.TC:
            return "Triangles"


def get_benchmark_project_path(fsharp_bench_path: Path) -> Path:
    return fsharp_bench_path / "QuadTree.Benchmark"


def get_benchmark_project_data_path(fsharp_bench_path: Path) -> Path:
    return get_benchmark_project_path(fsharp_bench_path) / "data"


def clean_symlinks(fsharp_bench_path: Path) -> None:
    data_dir = get_benchmark_project_data_path(fsharp_bench_path)
    links_to_clean = data_dir.glob("*.mtx")
    for file in links_to_clean:
        log.info("Removing %s", file)
        file.unlink()


def symlink_matrices(
    matrices: list[Matrix], matrices_path: Path, fsharp_bench_path: Path
) -> None:
    matrices_unique = get_unique_by_name_matrices(matrices)
    for matrix in matrices_unique:
        file_path = matrices_path / get_matrix_filename_mtx(matrix)
        dst_path = get_benchmark_project_data_path(
            fsharp_bench_path
        ) / get_matrix_filename_mtx(matrix)
        log.info("Symlinking %s to %s", file_path, dst_path)
        dst_path.symlink_to(file_path)


def get_file_by_algorithm(fsharp_bench_path: Path, algorithm: Algorithm) -> Path:
    return get_benchmark_project_path(fsharp_bench_path) / (
        get_fsharp_algorithm_name(algorithm) + ".fs"
    )


def patch_benchmark(
    matrices: list[Matrix], fsharp_bench_path: Path, algorithm: Algorithm
) -> None:
    matrices_t = filter(lambda matrix: matrix.algorithm == algorithm, matrices)
    filenames_quoted = map(
        lambda matrix: '"' + get_matrix_filename_mtx(matrix) + '"', matrices_t
    )
    filenames_str = "[<Params(" + ", ".join(filenames_quoted) + ")>]"
    file_to_path = get_file_by_algorithm(fsharp_bench_path, algorithm)
    with open(file_to_path, "r", encoding="utf-8") as f:
        file = f.read()
    file_edited = re.sub(r"\[<Params\(.*\)>]", filenames_str, file)
    log.info(
        "Patching %s with %s",
        file_to_path,
        filenames_str,
    )
    with open(file_to_path, "w", encoding="utf-8") as f:
        f.write(file_edited)


def patch_benchmarks(matrices: list[Matrix], fsharp_bench_path: Path) -> None:
    for algorithm in Algorithm:
        patch_benchmark(matrices, fsharp_bench_path, algorithm)


def collect_result_of_algorithm(
    results: Results, fsharp_bench_path: Path, algorithm: Algorithm
) -> None:
    log.info("Collecting %s results", algorithm.name)
    results_dir = fsharp_bench_path / "BenchmarkDotNet.Artifacts" / "results"
    results_json = results_dir / (
        "QuadTree.Benchmarks."
        + get_fsharp_algorithm_name(algorithm)
        + ".Benchmark-report-full-compressed.json"
    )
    try:
        with open(results_json, "r", encoding="utf-8") as f:
            results[str(algorithm)] = json.load(f)
    except FileNotFoundError:
        results[str(algorithm)] = ""


def collect_results(results: Results, fsharp_bench_path: Path) -> None:
    for algorithm in Algorithm:
        collect_result_of_algorithm(results, fsharp_bench_path, algorithm)


@app.command()
def fsharp(
    matrices_spec_path: FilePathOption = Path("matrices.yaml"),
    matrices_path: DirPathOption = Path("matrices"),
    fsharp_bench_path: DirPathOption = Path("tools") / "QTreeFSharp",
    raw_results_path: DirPathOption = Path("results") / "raw",
    clean_benchmark: Annotated[bool, typer.Option()] = False,
):
    if clean_benchmark:
        log.info("Cleaning QTreeFSharp")
        subprocess.run(["git", "restore", "."], cwd=fsharp_bench_path, check=True)

    matrices = get_enabled_matrices_for_tool(matrices_spec_path, Tool.FSHARP)

    log.info("Removing matrices in QTreeFSharp")
    clean_symlinks(fsharp_bench_path)

    log.info("Symlinking matrices to QTreeFSharp")
    symlink_matrices(matrices, matrices_path, fsharp_bench_path)

    log.info("Enabling matrices in QTreeFSharp")
    patch_benchmarks(matrices, fsharp_bench_path)

    log.info("Starting QTreeFSharp benchmark")
    subprocess.run(
        DOTNETBENCHMARK_RUN_COMMAND,
        cwd=fsharp_bench_path,
        check=True,
    )

    results: Results = {
        "bfs": dict(),
        "sssp": dict(),
        "tc": dict(),
    }
    collect_results(results, fsharp_bench_path)

    write_results(results, raw_results_path, Tool.FSHARP)
