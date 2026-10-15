import logging
import subprocess
from pathlib import Path
from typing import Annotated

import typer

from ..common import (
    DEFAULT_DEPENDENCIES_PATH,
    DEFAULT_MATRICES_PATH,
    DEFAULT_MATRICES_SPEC_PATH,
    DEFAULT_RAW_RESULTS_PATH,
    DEFAULT_TOOLS_PATH,
    LOGGER_NAME,
    MAKE,
    Matrix,
    Tool,
    comma_separated_str_to_int_list,
    get_enabled_matrices_for_tool,
    get_matrix_filename_mtx,
    run_benchmarks,
    write_results,
)
from ..type_aliases import DirPathOption, FilePathOption

GRAPHBLAS = "GraphBLAS"
LAGRAPH = "LAGraph"

app = typer.Typer()
logger = logging.getLogger(LOGGER_NAME)


def build_GraphBLAS(dependencies_path: Path):
    subprocess.run([MAKE], cwd=dependencies_path / GRAPHBLAS, check=True)


def check_GraphBLAS(dependencies_path: Path):
    subprocess.run([MAKE, "check"], cwd=dependencies_path / GRAPHBLAS, check=True)


def build_LAGraph(dependencies_path: Path):
    subprocess.run([MAKE], cwd=dependencies_path / LAGRAPH, check=True)


def check_LAGraph(dependencies_path: Path):
    subprocess.run([MAKE, "test"], cwd=dependencies_path / LAGRAPH, check=True)


def build_benchmarks(dependencies_path: Path, lagraph_bench_path: Path):
    (lagraph_bench_path / "build").mkdir(exist_ok=True)
    cc_common_args = [
        "-I",
        str(dependencies_path / GRAPHBLAS / "Include"),
        "-I",
        str(dependencies_path / LAGRAPH / "include"),
        "-L",
        str(dependencies_path / GRAPHBLAS / "build"),
        "-L",
        str(dependencies_path / LAGRAPH / "build" / "src"),
        "-lgraphblas",
        "-llagraph",
        "-Wl,-rpath=" + str(dependencies_path / GRAPHBLAS / "build"),
        "-Wl,-rpath=" + str(dependencies_path / LAGRAPH / "build" / "src"),
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
        check=True,
    )


@app.command()
def lagraph(
    matrices_spec_path: FilePathOption = DEFAULT_MATRICES_SPEC_PATH,
    matrices_path: DirPathOption = DEFAULT_MATRICES_PATH,
    dependencies_path: DirPathOption = DEFAULT_DEPENDENCIES_PATH,
    lagraph_bench_path: DirPathOption = DEFAULT_TOOLS_PATH / "lagraph-bench",
    raw_results_path: DirPathOption = DEFAULT_RAW_RESULTS_PATH,
    check: Annotated[bool, typer.Option()] = False,
    run_count: Annotated[int, typer.Option] = 20,
    thread_counts: Annotated[str | None, typer.Option()] = None,
):
    logger.info("Building GraphBLAS")
    build_GraphBLAS(dependencies_path)
    logger.info("Successfully built GraphBLAS")

    if check:
        logger.info("Checking GraphBLAS")
        check_GraphBLAS(dependencies_path)
        logger.info("Successfully checked GraphBLAS")

    logger.info("Building LAGraph")
    build_LAGraph(dependencies_path)
    logger.info("Successfully built LAGraph")
    if check:
        logger.info("Checking LAGraph")
        check_LAGraph(dependencies_path)
        logger.info("Successfully checked LAGraph")

    logger.info("Building benchmarks")
    build_benchmarks(dependencies_path, lagraph_bench_path)
    logger.info("Successfully built benchmarks")

    matrices = get_enabled_matrices_for_tool(matrices_spec_path, Tool.LAGRAPH)

    # See inpla.py for comments on this decision
    thread_counts_t = comma_separated_str_to_int_list(thread_counts)
    logger.info(
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
