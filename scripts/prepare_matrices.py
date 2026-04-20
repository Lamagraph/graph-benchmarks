from pathlib import Path
import subprocess
from typing import Annotated

import typer
import yaml

from common import BenchMatrix, BenchmarkType


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
):
    with open(matrices_spec_path, "r", encoding="utf-8") as m_file:
        matrices: list[BenchMatrix] = yaml.safe_load(m_file)
    enabled_matrices = list(filter(lambda matrix: matrix["enabled"], matrices))

    print("*** Reordering matrices ***")
    matrices_to_reorder = list(
        filter(lambda matrix: matrix["reorder"], enabled_matrices)
    )
    for matrix in matrices_to_reorder:
        subprocess.run(
            [
                "uv",
                "run",
                inpla_bench_path / "scripts" / "simple_mtx_reordering.py",
                matrices_path / (matrix["name"] + ".mtx"),
            ],
            check=True,
        )
    print("")

    print("*** Making matrices for SSSP positive ***")
    matrices_to_make_positive = list(
        filter(
            lambda matrix: matrix["algorithm"] == BenchmarkType.SSSP, enabled_matrices
        )
    )
    for matrix in matrices_to_make_positive:
        subprocess.run(
            [
                inpla_bench_path / "scripts" / "make_positive.fsx",
                matrices_path
                / (
                    matrix["name"]
                    + ("_reordered" if matrix["reorder"] else "")
                    + ".mtx"
                ),
            ],
            check=True,
        )


if __name__ == "__main__":
    typer.run(main)
