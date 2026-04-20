from datetime import datetime
import json
import os
from pathlib import Path
import resource
import subprocess
from typing import Annotated

import typer
import yaml

from common import (
    BenchMatrix,
    get_matrix_base_name,
    get_matrix_filename_in,
    get_matrix_filename_mtx,
)


def make_inpla(inpla_path: Path):
    subprocess.run(["make"], cwd=inpla_path, check=True)
    subprocess.run(["make", "clean"], cwd=inpla_path, check=True)
    subprocess.run(["make", "thread"], cwd=inpla_path, check=True)


def check_inpla(inpla_path: Path, inpla_bench_path: Path):
    subprocess.run(
        ["dotnet", "fsi", "test.fsx", inpla_path / "inpla"],
        cwd=inpla_bench_path,
        check=True,
    )


def convert_matrix_to_inpla(
    matrix: BenchMatrix,
    matrices_path: Path,
    inpla_bench_path: Path,
):
    subprocess.run(
        [
            Path("scripts") / "mtx_to_experiment.fsx",
            matrices_path / get_matrix_filename_mtx(matrix),
            matrix["algorithm"],
        ],
        cwd=inpla_bench_path,
        check=True,
    )


def convert_matrices_to_inpla(
    inpla_matrices: list[BenchMatrix],
    matrices_path: Path,
    inpla_bench_path: Path,
):

    for matrix in inpla_matrices:
        convert_matrix_to_inpla(matrix, matrices_path, inpla_bench_path)


def run_inpla(
    inpla_path: Path, inpla_bench_path: Path, thread_count: int, matrix_path: Path
) -> str:
    resource.setrlimit(
        resource.RLIMIT_STACK, (resource.RLIM_INFINITY, resource.RLIM_INFINITY)
    )
    run_res = subprocess.run(
        [inpla_path / "inpla", "-t", str(thread_count), "-f", matrix_path],
        cwd=inpla_bench_path,
        capture_output=True,
        text=True,
    )
    if run_res.returncode != 0:
        print(
            "Process",
            run_res.args,
            "exited with code",
            run_res.returncode,
            end=" ",
            flush=True,
        )
    return run_res.stdout


def run_inpla_many_times(
    inpla_path: Path,
    inpla_bench_path: Path,
    run_count: int,
    thread_count: int,
    matrix_path: Path,
) -> list[str]:
    result = []
    print("Running with", thread_count, "threads. Run: ", end="")
    for i in range(run_count):
        print(i + 1, "...", sep="", end="", flush=True)
        result.append(
            run_inpla(inpla_path, inpla_bench_path, thread_count, matrix_path)
        )
    print("")
    return result


def run_experiment(
    inpla_path: Path,
    inpla_bench_path: Path,
    run_count: int,
    thread_count: int,
    matrix_path: Path,
) -> dict[int, list[str]]:
    if thread_count <= 0:
        result = dict()

        nproc = os.cpu_count()
        if nproc is None:
            raise RuntimeError("Cannot get nproc")
        thread_counts = [1] + list(range(2, nproc + 1, 2))

        for thread_count in thread_counts:
            result[thread_count] = run_inpla_many_times(
                inpla_path, inpla_bench_path, run_count, thread_count, matrix_path
            )

        return result
    else:
        result = run_inpla_many_times(
            inpla_path, inpla_bench_path, run_count, thread_count, matrix_path
        )
        return {thread_count: result}


def run_experiments(
    inpla_path: Path,
    inpla_bench_path: Path,
    run_count: int,
    thread_count: int,
    inpla_matrices: list[BenchMatrix],
):
    results: dict[str, dict[str, dict[int, list[str]]]] = {
        "bfs": dict(),
        "sssp": dict(),
        "tc": dict(),
    }
    for matrix in inpla_matrices:
        filename_base = get_matrix_base_name(matrix)
        matrix_path = (
            inpla_bench_path
            / ("experiments_" + matrix["algorithm"])
            / get_matrix_filename_in(matrix)
        )
        print("Benchmarking", matrix["algorithm"], "on", filename_base)
        results[matrix["algorithm"]][filename_base] = run_experiment(
            inpla_path, inpla_bench_path, run_count, thread_count, matrix_path
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
    inpla_path: Annotated[
        Path,
        typer.Option(
            file_okay=False,
            dir_okay=True,
            readable=True,
            writable=True,
            resolve_path=True,
        ),
    ] = Path("dependencies") / "inpla",
    inpla_bench_path: Annotated[
        Path,
        typer.Option(
            file_okay=False,
            dir_okay=True,
            readable=True,
            writable=True,
            resolve_path=True,
        ),
    ] = Path("tools") / "QTreeInpla",
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
    run_count: Annotated[int, typer.Option] = 5,
    thread_count: Annotated[int, typer.Option] = 0,
):
    print("*** Making inpla ***")
    make_inpla(inpla_path)
    print("")
    if check:
        print("*** Checking inpla ***")
        check_inpla(inpla_path, inpla_bench_path)
        print("")

    with open(matrices_spec_path, "r", encoding="utf-8") as m_file:
        matrices: list[BenchMatrix] = yaml.safe_load(m_file)
    enabled_matrices = filter(lambda matrix: matrix["enabled"], matrices)
    inpla_matrices = list(
        filter(lambda matrix: "inpla" in matrix["tools"], enabled_matrices)
    )

    print("*** Converting matrices for inpla ***")
    convert_matrices_to_inpla(inpla_matrices, matrices_path, inpla_bench_path)
    print("")

    print("*** Running experiments ***")
    results = run_experiments(
        inpla_path, inpla_bench_path, run_count, thread_count, inpla_matrices
    )
    print("")

    print("*** Writing results ***")
    raw_results_path.mkdir(parents=True, exist_ok=True)
    results_path = raw_results_path / (
        datetime.now().astimezone().isoformat(timespec="minutes") + "_inpla.json"
    )
    with open(results_path, "w", encoding="utf-8") as r_file:
        json.dump(results, r_file)
    print("Wrote to", str(results_path))


if __name__ == "__main__":
    typer.run(main)
