from enum import Enum, StrEnum, auto
from pathlib import Path
import subprocess
from typing import Annotated

import typer
import yaml


class BenchmarkType(StrEnum):
    BFS = auto()
    SSSP = auto()
    TC = auto()


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


def run_benchmark(
    matrices_spec_path: Path,
    matrices_path: Path,
    lagraph_bench_path: Path,
    type: BenchmarkType,
    run_count: int,
):
    with open(matrices_spec_path, "r", encoding="utf-8") as m_file:
        matrices = yaml.safe_load(m_file)
    enabled_matrices = filter(lambda matrix: matrix["enabled"], matrices)
    matrices_for_type = filter(
        lambda matrix: matrix["algorithm"] == type, enabled_matrices
    )

    for matrix in matrices_for_type:
        result = subprocess.run(
            ["build/lagraph" + type, matrices_path / (matrix["name"] + ".mtx")],
            cwd=lagraph_bench_path,
            check=True,
        )


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
    check: Annotated[bool, typer.Option()] = False,
    run_count: Annotated[int, typer.Option] = 20,
):
    make_GraphBLAS(dependencies_path)
    if check:
        check_GraphBLAS(dependencies_path)

    make_LAGraph(dependencies_path)
    if check:
        check_LAGraph(dependencies_path)

    make_benchmarks(dependencies_path, lagraph_bench_path)


if __name__ == "__main__":
    typer.run(main)
