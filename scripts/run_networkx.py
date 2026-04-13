from pathlib import Path
import subprocess
from typing import Annotated

import typer
import yaml

from common import BenchMatrix


def prepare_environment(nx_bench_path: Path):
    subprocess.run(["uv", "sync"], cwd=nx_bench_path, check=True)


def clean_symlinks(nx_bench_path: Path):
    bfs_to_clean = (nx_bench_path / "bfs").glob("**/*.mtx")
    for file in bfs_to_clean:
        file.unlink()
    sssp_to_clean = (nx_bench_path / "sssp").glob("**/*.mtx")
    for file in sssp_to_clean:
        file.unlink()
    triangles_to_clean = (nx_bench_path / "triangles").glob("**/*.mtx")
    for file in triangles_to_clean:
        file.unlink()


def symlink_matrices(
    matrices_spec_path: Path, matrices_path: Path, nx_bench_path: Path
):
    with open(matrices_spec_path, "r", encoding="utf-8") as m_file:
        matrices: list[BenchMatrix] = yaml.safe_load(m_file)
    enabled_matrices = filter(lambda matrix: matrix["enabled"], matrices)
    networkx_matrices = filter(
        lambda matrix: "networkx" in matrix["tools"], enabled_matrices
    )
    for matrix in networkx_matrices:
        file_path = matrices_path / (matrix["name"] + ".mtx")
        dst_path = (
            nx_bench_path
            / ("triangles" if matrix["algorithm"] == "tc" else matrix["algorithm"])
            / (matrix["name"] + ".mtx")
        )
        dst_path.symlink_to(file_path)


def run_benchmarks(nx_bench_path: Path):
    subprocess.run(["uv", "run", "pytest"], cwd=nx_bench_path, check=True)


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
    nx_bench_path: Annotated[
        Path,
        typer.Option(
            file_okay=False,
            dir_okay=True,
            readable=True,
            writable=True,
            resolve_path=True,
        ),
    ] = Path("tools/nx-benchmarks"),
):
    prepare_environment(nx_bench_path)
    clean_symlinks(nx_bench_path)
    symlink_matrices(matrices_spec_path, matrices_path, nx_bench_path)
    run_benchmarks(nx_bench_path)


if __name__ == "__main__":
    typer.run(main)
