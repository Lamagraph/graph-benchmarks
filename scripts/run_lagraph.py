from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
from typing import Annotated

import typer
import yaml

from common import (
    BenchMatrix,
    BenchmarkType,
    get_matrix_base_name,
    get_matrix_filename_mtx,
)


def make_GraphBLAS(dependencies_path: Path):
    subprocess.run(["make"], cwd=dependencies_path / "GraphBLAS", check=True)


def check_GraphBLAS(dependencies_path: Path):
    subprocess.run(["make", "check"], cwd=dependencies_path / "GraphBLAS", check=True)


def make_LAGraph(dependencies_path: Path):
    subprocess.run(["make"], cwd=dependencies_path / "LAGraph", check=True)


def check_LAGraph(dependencies_path: Path):
    subprocess.run(["make", "test"], cwd=dependencies_path / "LAGraph", check=True)


def make_benchmarks(dependencies_path: Path, lagraph_bench_path: Path):
    (lagraph_bench_path / "build").mkdir(exist_ok=True)
    cc_common_args = [
        "-I",
        str(dependencies_path / "GraphBLAS" / "Include"),
        "-I",
        str(dependencies_path / "LAGraph" / "include"),
        "-L",
        str(dependencies_path / "GraphBLAS" / "build"),
        "-L",
        str(dependencies_path / "LAGraph" / "build" / "src"),
        "-lgraphblas",
        "-llagraph",
        "-Wl,-rpath=" + str(dependencies_path / "GraphBLAS" / "build"),
        "-Wl,-rpath=" + str(dependencies_path / "LAGraph" / "build" / "src"),
        "-O3",
        "-g",
    ]
    subprocess.run(
        ["cc", "src/lagraph_bfs.c", "-o", "build/lagraph_bfs"] + cc_common_args,
        cwd=lagraph_bench_path,
        check=True,
    )
    subprocess.run(
        ["cc", "src/lagraph_sssp.c", "-o", "build/lagraph_sssp"] + cc_common_args,
        cwd=lagraph_bench_path,
        check=True,
    )
    subprocess.run(
        ["cc", "src/lagraph_triangles.c", "-o", "build/lagraph_tc"] + cc_common_args,
        cwd=lagraph_bench_path,
        check=True,
    )


def run_lagraph(
    lagraph_bench_path: Path,
    matrices_path: Path,
    matrix: BenchMatrix,
    thread_count: int,
) -> str:
    run_res = subprocess.run(
        [
            Path("build") / ("lagraph_" + matrix["algorithm"]),
            matrices_path / get_matrix_filename_mtx(matrix),
        ],
        cwd=lagraph_bench_path,
        capture_output=True,
        text=True,
        env={"OMP_NUM_THREADS": str(thread_count)},
    )
    if run_res.returncode != 0:
        print(
            "Process",
            run_res.args,
            "exited with code",
            run_res.returncode,
            end="",
            flush=True,
        )
    return run_res.stdout


def run_lagraph_many_times(
    lagraph_bench_path: Path,
    matrices_path: Path,
    matrix: BenchMatrix,
    run_count: int,
    thread_count: int,
) -> list[str]:
    result = []
    print("Running with", thread_count, "threads. Run: ", end="")
    for i in range(run_count):
        print(i + 1, "...", sep="", end="", flush=True)
        result.append(
            run_lagraph(lagraph_bench_path, matrices_path, matrix, thread_count)
        )
    print("")
    return result


def run_experiment(
    lagraph_bench_path: Path,
    matrices_path: Path,
    matrix: BenchMatrix,
    run_count: int,
    thread_count: int,
) -> dict[int, list[str]]:
    if thread_count <= 0:
        result = dict()

        nproc = os.cpu_count()
        if nproc is None:
            raise RuntimeError("Cannot get nproc")
        thread_counts = [1] + list(range(2, nproc + 1, 2))

        for thread_count in thread_counts:
            result[thread_count] = run_lagraph_many_times(
                lagraph_bench_path, matrices_path, matrix, run_count, thread_count
            )

        return result
    else:
        result = run_lagraph_many_times(
            lagraph_bench_path, matrices_path, matrix, run_count, thread_count
        )
        return {thread_count: result}


def run_experiments(
    lagraph_bench_path: Path,
    matrices_path: Path,
    run_count: int,
    thread_count: int,
    lagraph_matrices: list[BenchMatrix],
):
    results: dict[str, dict[str, dict[int, list[str]]]] = {
        "bfs": dict(),
        "sssp": dict(),
        "tc": dict(),
    }
    for matrix in lagraph_matrices:
        base_name = get_matrix_base_name(matrix)
        print("Benchmarking", matrix["algorithm"], "on", base_name)
        results[matrix["algorithm"]][base_name] = run_experiment(
            lagraph_bench_path, matrices_path, matrix, run_count, thread_count
        )
        print("")

    return results


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
    dependencies_path: Annotated[
        Path,
        typer.Option(
            file_okay=False,
            dir_okay=True,
            readable=True,
            writable=True,
            resolve_path=True,
        ),
    ] = Path("dependencies"),
    lagraph_bench_path: Annotated[
        Path,
        typer.Option(
            file_okay=False,
            dir_okay=True,
            readable=True,
            writable=True,
            resolve_path=True,
        ),
    ] = Path("tools/lagraph-bench"),
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
    check: Annotated[bool, typer.Option()] = False,
    run_count: Annotated[int, typer.Option] = 20,
    thread_count: Annotated[int, typer.Option] = 0,
):
    print("*** Making GraphBLAS ***")
    make_GraphBLAS(dependencies_path)
    print("")
    if check:
        print("*** Checking GraphBLAS ***")
        check_GraphBLAS(dependencies_path)
        print("")

    print("*** Making LAGraph ***")
    make_LAGraph(dependencies_path)
    print("")
    if check:
        print("*** Checking LAGraph ***")
        check_LAGraph(dependencies_path)
        print("")

    print("*** Making benchmarks ***")
    make_benchmarks(dependencies_path, lagraph_bench_path)
    print("")

    with open(matrices_spec_path, "r", encoding="utf-8") as m_file:
        matrices: list[BenchMatrix] = yaml.safe_load(m_file)
    enabled_matrices = filter(lambda matrix: matrix["enabled"], matrices)
    lagraph_matrices = list(
        filter(lambda matrix: "lagraph" in matrix["tools"], enabled_matrices)
    )

    print("*** Running experiments ***")
    results = run_experiments(
        lagraph_bench_path, matrices_path, run_count, thread_count, lagraph_matrices
    )
    print("")

    print("*** Writing results ***")
    raw_results_path.mkdir(parents=True, exist_ok=True)
    results_path = raw_results_path / (
        datetime.now().astimezone().isoformat(timespec="minutes") + "_lagraph.json"
    )
    with open(results_path, "w", encoding="utf-8") as r_file:
        json.dump(results, r_file)
    print("Wrote to", str(results_path))


if __name__ == "__main__":
    typer.run(main)
