import logging
from pathlib import Path
import resource
import subprocess
from typing import Annotated

import typer


from ..common import (
    Matrix,
    Tool,
    comma_separated_str_to_int_list,
    get_enabled_matrices_for_tool,
    get_matrix_filename_in,
    get_matrix_filename_mtx,
    run_benchmarks,
    write_results,
)
from ..type_aliases import DirPathOption, FilePathOption

app = typer.Typer()
log = logging.getLogger("rich")


def make_inpla(inpla_path: Path) -> None:
    subprocess.run(["make", "clean"], cwd=inpla_path, check=True)
    subprocess.run(["make"], cwd=inpla_path, check=True)
    subprocess.run(["make", "clean"], cwd=inpla_path, check=True)
    subprocess.run(["make", "thread"], cwd=inpla_path, check=True)


def check_inpla(inpla_path: Path, inpla_bench_path: Path) -> None:
    subprocess.run(
        ["dotnet", "fsi", "test.fsx", inpla_path / "inpla"],
        cwd=inpla_bench_path,
        check=True,
    )


def convert_matrices_to_inpla(
    inpla_matrices: list[Matrix],
    matrices_path: Path,
    inpla_bench_path: Path,
) -> None:
    for matrix in inpla_matrices:
        subprocess.run(
            [
                Path("scripts") / "mtx_to_experiment.fsx",
                matrices_path / get_matrix_filename_mtx(matrix),
                matrix.algorithm,
            ],
            cwd=inpla_bench_path,
            check=True,
        )


def run_inpla(
    matrix: Matrix,
    thread_count: int,
    *,
    inpla_path: Path,
    inpla_bench_path: Path,
    memory_limit_for_1_thread: int,
) -> subprocess.CompletedProcess[str]:
    resource.setrlimit(
        resource.RLIMIT_STACK, (resource.RLIM_INFINITY, resource.RLIM_INFINITY)
    )
    matrix_path = (
        inpla_bench_path
        / ("experiments_" + matrix.algorithm)
        / get_matrix_filename_in(matrix)
    )
    return subprocess.run(
        [
            inpla_path / "inpla",
            "-t",
            str(thread_count),
            "-f",
            matrix_path,
            "-Xms",
            str(memory_limit_for_1_thread // thread_count),
        ],
        cwd=inpla_bench_path,
        capture_output=True,
        text=True,
    )


@app.command()
def inpla(
    matrices_spec_path: FilePathOption = Path("matrices.yaml"),
    matrices_path: DirPathOption = Path("matrices"),
    inpla_path: DirPathOption = Path("dependencies") / "inpla",
    inpla_bench_path: DirPathOption = Path("tools") / "QTreeInpla",
    raw_results_path: DirPathOption = Path("results") / "raw",
    check: Annotated[bool, typer.Option()] = False,
    run_count: Annotated[int, typer.Option] = 5,
    thread_counts: Annotated[str | None, typer.Option()] = None,
    memory_limit_for_1_thread: Annotated[
        int,
        typer.Option(
            help="Compute by formula ((desired heap size in GiB) * 2**30 / (88+16) / 1.2), default for 128 GiB machines"
        ),
    ] = 1032444062,
):
    logging.info("Building inpla")
    make_inpla(inpla_path)
    logging.info("Successfully built inpla")

    if check:
        logging.info("Checking inpla")
        check_inpla(inpla_path, inpla_bench_path)
        logging.info("Successfully checked inpla")

    matrices = get_enabled_matrices_for_tool(matrices_spec_path, Tool.INPLA)

    logging.info("Converting matrices for inpla")
    convert_matrices_to_inpla(matrices, matrices_path, inpla_bench_path)

    # parser doesn't work
    # see https://github.com/fastapi/typer/discussions/1393
    thread_counts_t = comma_separated_str_to_int_list(thread_counts)
    logging.info(
        "Starting inpla benchmarks with thread counts: %s",
        thread_counts_t,
    )
    results = run_benchmarks(
        matrices,
        thread_counts_t,
        run_count,
        run_inpla,
        inpla_path=inpla_path,
        inpla_bench_path=inpla_bench_path,
        memory_limit_for_1_thread=memory_limit_for_1_thread,
    )
    write_results(results, raw_results_path, Tool.INPLA)
