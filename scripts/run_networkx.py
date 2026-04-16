from datetime import datetime
from pathlib import Path
import shutil
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
        print("Cleaned", file)
    sssp_to_clean = (nx_bench_path / "sssp").glob("**/*.mtx")
    for file in sssp_to_clean:
        file.unlink()
        print("Cleaned", file)
    tc_to_clean = (nx_bench_path / "tc").glob("**/*.mtx")
    for file in tc_to_clean:
        file.unlink()
        print("Cleaned", file)


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
        dst_path = nx_bench_path / (matrix["algorithm"]) / (matrix["name"] + ".mtx")
        dst_path.symlink_to(file_path)
        print("Symlinked", file_path, "to", dst_path)


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
):
    print("*** Preparing NetworkX ***")
    prepare_environment(nx_bench_path)
    print("")

    print("*** Cleaning symlinks ***")
    clean_symlinks(nx_bench_path)
    print("")

    print("*** Symlinking matrices ***")
    symlink_matrices(matrices_spec_path, matrices_path, nx_bench_path)
    print("")

    print("*** Running experiments ***")
    run_benchmarks(nx_bench_path)
    print("")

    print("*** Writing results ***")
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
    print("Wrote to", str(results_path))


if __name__ == "__main__":
    typer.run(main)
