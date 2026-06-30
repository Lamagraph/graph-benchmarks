import logging
from pathlib import Path
import subprocess
from typing import Annotated

import typer

from ..common import (
    Matrix,
    Tool,
    comma_separated_str_to_int_list,
    get_enabled_matrices_for_tool,
    get_matrix_filename_mtx,
    run_benchmarks,
    write_results,
)
from ..type_aliases import DirPathOption, FilePathOption

app = typer.Typer()
log = logging.getLogger("rich")


def build_GraphBLAS(dependencies_path: Path):
    subprocess.run(["make"], cwd=dependencies_path / "GraphBLAS", check=True)


def check_GraphBLAS(dependencies_path: Path):
    subprocess.run(["make", "check"], cwd=dependencies_path / "GraphBLAS", check=True)


def build_LAGraph(dependencies_path: Path):
    subprocess.run(["make"], cwd=dependencies_path / "LAGraph", check=True)


def check_LAGraph(dependencies_path: Path):
    subprocess.run(["make", "test"], cwd=dependencies_path / "LAGraph", check=True)


def build_benchmarks(dependencies_path: Path, lagraph_bench_path: Path):
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
    matrix: Matrix,
    thread_count: int,
    *,
    lagraph_bench_path: Path,
    matrices_path: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            Path("build") / ("lagraph_" + matrix.algorithm),
            matrices_path / get_matrix_filename_mtx(matrix),
        ],
        cwd=lagraph_bench_path,
        capture_output=True,
        text=True,
        env={"OMP_NUM_THREADS": str(thread_count)},
    )


@app.command()
def lagraph(
    matrices_spec_path: FilePathOption = Path("matrices.yaml"),
    matrices_path: DirPathOption = Path("matrices"),
    dependencies_path: DirPathOption = Path("dependencies"),
    lagraph_bench_path: DirPathOption = Path("tools/lagraph-bench"),
    raw_results_path: DirPathOption = Path("results") / "raw",
    check: Annotated[bool, typer.Option()] = False,
    run_count: Annotated[int, typer.Option] = 20,
    thread_counts: Annotated[str | None, typer.Option()] = None,
):
    log.info("Building GraphBLAS")
    build_GraphBLAS(dependencies_path)
    log.info("Successfully built GraphBLAS")

    if check:
        log.info("Checking GraphBLAS")
        check_GraphBLAS(dependencies_path)
        log.info("Successfully checked GraphBLAS")

    log.info("Building LAGraph")
    build_LAGraph(dependencies_path)
    log.info("Successfully built LAGraph")
    if check:
        log.info("Checking LAGraph")
        check_LAGraph(dependencies_path)
        log.info("Successfully checked LAGraph")

    log.info("Building benchmarks")
    build_benchmarks(dependencies_path, lagraph_bench_path)
    log.info("Successfully built LAGraph")

    matrices = get_enabled_matrices_for_tool(matrices_spec_path, Tool.LAGRAPH)

    # parser doesn't work
    # see https://github.com/fastapi/typer/discussions/1393
    thread_counts_t = comma_separated_str_to_int_list(thread_counts)
    logging.info(
        "Starting LAGraph benchmarks with thread counts: %s",
        thread_counts_t,
    )
    results = run_benchmarks(
        matrices,
        thread_counts_t,
        run_count,
        run_lagraph,
        matrices_path=matrices_path,
        lagraph_bench_path=lagraph_bench_path,
    )

    write_results(results, raw_results_path, Tool.LAGRAPH)
