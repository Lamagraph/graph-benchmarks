from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
from typing import Annotated

import typer
import yaml

from common import BenchMatrix, BenchmarkType, get_matrix_filename_mtx


def get_file_by_algorithm(fsharp_bench_path: Path, algorithm: BenchmarkType):
    base = fsharp_bench_path / "QuadTree.Benchmark"
    match algorithm:
        case BenchmarkType.BFS:
            return base / "BFS.fs"
        case BenchmarkType.SSSP:
            return base / "SSSP.fs"
        case BenchmarkType.TC:
            return base / "Triangles.fs"


def clean_symlinks(fsharp_bench_path: Path):
    data_dir = fsharp_bench_path / "QuadTree.Benchmark" / "data"
    links_to_clean = data_dir.glob("*.mtx")
    for file in links_to_clean:
        file.unlink()
        print("Cleaned", file)


def symlink_matrices(
    fsharp_matrices: list[BenchMatrix], matrices_path: Path, fsharp_bench_path: Path
):
    for matrix in fsharp_matrices:
        file_path = matrices_path / get_matrix_filename_mtx(matrix)
        dst_path = (
            fsharp_bench_path
            / "QuadTree.Benchmark"
            / "data"
            / get_matrix_filename_mtx(matrix)
        )
        dst_path.symlink_to(file_path)
        print("Symlinked", file_path, "to", dst_path)


def patch_benchmark(
    fsharp_bench_path: Path,
    fsharp_matrices: list[BenchMatrix],
    algorithm: BenchmarkType,
):
    matrices = filter(lambda matrix: matrix["algorithm"] == algorithm, fsharp_matrices)
    filenames_quoted = map(
        lambda matrix: '"' + get_matrix_filename_mtx(matrix) + '"', matrices
    )
    filenames_str = "[<Params(" + ", ".join(filenames_quoted) + ")>]"
    with open(
        get_file_by_algorithm(fsharp_bench_path, algorithm), "r", encoding="utf-8"
    ) as f:
        file = f.read()
    file_edited = re.sub(r"\[<Params\(.*\)>]", filenames_str, file)
    with open(
        get_file_by_algorithm(fsharp_bench_path, algorithm), "w", encoding="utf-8"
    ) as f:
        f.write(file_edited)
    print(
        "Patched",
        get_file_by_algorithm(fsharp_bench_path, algorithm),
        "with",
        filenames_str,
    )


def patch_benchmarks(fsharp_bench_path: Path, fsharp_matrices: list[BenchMatrix]):
    patch_benchmark(fsharp_bench_path, fsharp_matrices, BenchmarkType.BFS)
    patch_benchmark(fsharp_bench_path, fsharp_matrices, BenchmarkType.SSSP)
    patch_benchmark(fsharp_bench_path, fsharp_matrices, BenchmarkType.TC)


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
    matrices_path: Annotated[
        Path,
        typer.Option(
            file_okay=False,
            dir_okay=True,
            readable=True,
            writable=True,
            resolve_path=True,
        ),
    ] = Path("matrices"),
    fsharp_bench_path: Annotated[
        Path,
        typer.Option(
            file_okay=False,
            dir_okay=True,
            readable=True,
            writable=True,
            resolve_path=True,
        ),
    ] = Path("tools") / "QTreeFSharp",
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
    reset_tree: Annotated[bool, typer.Option()] = False,
):
    if reset_tree:
        print("*** Reset QTreeFSharp ***")
        subprocess.run(["git", "restore", "."], cwd=fsharp_bench_path, check=True)
        print("")

    with open(matrices_spec_path, "r", encoding="utf-8") as m_file:
        matrices: list[BenchMatrix] = yaml.safe_load(m_file)
    enabled_matrices = filter(lambda matrix: matrix["enabled"], matrices)
    fsharp_matrices = list(
        filter(lambda matrix: "fsharp" in matrix["tools"], enabled_matrices)
    )

    print("*** Cleaning symlinks ***")
    clean_symlinks(fsharp_bench_path)
    print("")

    print("*** Symlinking matrices ***")
    symlink_matrices(fsharp_matrices, matrices_path, fsharp_bench_path)
    print("")

    print("*** Patching benchmarks ***")
    patch_benchmarks(fsharp_bench_path, fsharp_matrices)
    print("")

    print("*** Running experiments ***")
    subprocess.run(
        [
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
        ],
        cwd=fsharp_bench_path,
        check=True,
    )
    print("")

    print("*** Writing results ***")
    raw_results_path.mkdir(parents=True, exist_ok=True)
    results_path = raw_results_path / (
        datetime.now().astimezone().isoformat(timespec="minutes") + "_fsharp.json"
    )
    results = dict()

    results_dir = fsharp_bench_path / "BenchmarkDotNet.Artifacts" / "results"
    bfs_results_json = (
        results_dir / "QuadTree.Benchmarks.BFS.Benchmark-report-full-compressed.json"
    )
    try:
        with open(bfs_results_json, "r", encoding="utf-8") as f:
            results["bfs"] = json.load(f)
    except FileNotFoundError:
        results["vfs"] = ""

    sssp_results_json = (
        results_dir / "QuadTree.Benchmarks.SSSP.Benchmark-report-full-compressed.json"
    )
    try:
        with open(sssp_results_json, "r", encoding="utf-8") as f:
            results["sssp"] = json.load(f)
    except FileNotFoundError:
        results["sssp"] = ""

    tc_results_json = (
        results_dir
        / "QuadTree.Benchmarks.Triangles.Benchmark-report-full-compressed.json"
    )
    try:
        with open(tc_results_json, "r", encoding="utf-8") as f:
            results["tc"] = json.load(f)
    except FileNotFoundError:
        results["tc"] = ""

    with open(results_path, "w", encoding="utf-8") as r_file:
        json.dump(results, r_file)
    print("Wrote to", str(results_path))


if __name__ == "__main__":
    typer.run(main)
