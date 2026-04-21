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

    print("*** Making matrices nonnegative int ***")
    enabled_matrix_names = set(map(lambda matrix: matrix["name"], enabled_matrices))
    for matrix_name in enabled_matrix_names:
        matrix_path = matrices_path / (matrix_name + ".mtx")
        subprocess.run(
            ["uv", "run", Path("scripts") / "make_positive_int.py", matrix_path],
            check=True,
        )
        print("Made nonnegative int matrix", matrix_path)
    print("")

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


if __name__ == "__main__":
    typer.run(main)
