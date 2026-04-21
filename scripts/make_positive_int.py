from pathlib import Path
from typing import Annotated

from scipy.sparse import coo_array
from scipy.io import mmread, mmwrite
import typer


def make_nonnegative_int(matrix: coo_array):
    matrix = matrix.trunc()
    min_element = matrix.min()
    if min_element < 0:
        to_add = abs(min_element)
        matrix.data += to_add
        matrix.eliminate_zeros()
    return matrix


def main(
    matrix_path: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            writable=True,
            resolve_path=True,
        ),
    ],
):
    matrix = mmread(matrix_path, spmatrix=True)
    nonnegative_int_matrix = make_nonnegative_int(matrix)
    mmwrite(matrix_path, nonnegative_int_matrix, field="integer")


if __name__ == "__main__":
    typer.run(main)
