import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import typer

from ..common import (
    Matrix,
    Tool,
    get_enabled_matrices_for_tool,
    get_matrix_filename_mtx,
)
from ..type_aliases import DirPathOption, FilePathOption

app = typer.Typer()
logger = logging.getLogger("app")


def clean_symlinks(nx_bench_path: Path):
    matrices_to_clean = nx_bench_path.glob("**/*.mtx")
    for file in matrices_to_clean:
        logger.info("Removing %s", file)
        file.unlink()


def symlink_matrices(matrices: list[Matrix], matrices_path: Path, nx_bench_path: Path):
    for matrix in matrices:
        file_path = matrices_path / get_matrix_filename_mtx(matrix)
        dst_path = nx_bench_path / (matrix.algorithm) / get_matrix_filename_mtx(matrix)
        logger.info("Symlinking %s to %s", file_path, dst_path)
        dst_path.symlink_to(file_path)


@app.command()
def networkx(
    matrices_spec_path: FilePathOption = Path("matrices.yaml"),
    matrices_path: DirPathOption = Path("matrices"),
    nx_bench_path: DirPathOption = Path("tools/nx-benchmarks"),
    raw_results_path: DirPathOption = Path("results") / "raw",
):
    logger.info("Setting up NetworkX")
    subprocess.run(["uv", "sync"], cwd=nx_bench_path, check=True)

    logger.info("Removing matrices in NetworkX")
    clean_symlinks(nx_bench_path)

    matrices = get_enabled_matrices_for_tool(matrices_spec_path, Tool.NETWORKX)

    logger.info("Symlinking matrices to NetworkX")
    symlink_matrices(matrices, matrices_path, nx_bench_path)

    logger.info("Starting NetworkX benchmark")
    subprocess.run(["uv", "run", "pytest"], cwd=nx_bench_path, check=True)

    json_files = sorted(
        (nx_bench_path / "results").glob("**/*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    latest_json = json_files[0]
    raw_results_path.mkdir(parents=True, exist_ok=True)
    results_path = raw_results_path / (
        datetime.now().astimezone().isoformat(timespec="minutes") + "_networkx.json"
    )
    shutil.copy(latest_json, results_path)

    logger.info("Successfully wrote results to %s", results_path)
