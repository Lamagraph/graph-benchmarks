import logging
import os
from pathlib import Path

import scipy.sparse as sp
import typer
from scipy.io import mmread, mmwrite

from .common import Matrix, get_enabled_matrices, get_unique_by_name_matrices
from .type_aliases import DirPathOption, FilePathOption

app = typer.Typer()
log = logging.getLogger("rich")


def make_coo_array_nonnegative_int(matrix):
    matrix = matrix.trunc()
    min_element = matrix.min()
    if min_element < 0:
        to_add = abs(min_element)
        matrix.data += to_add
        matrix.eliminate_zeros()
    return matrix


def make_matrix_nonnegative_int(matrices_path: Path, matrix: Matrix):
    matrix_path = matrices_path / (matrix.name + ".mtx")
    matrix_array = mmread(matrix_path, spmatrix=False)
    nonnegative_int_matrix = make_coo_array_nonnegative_int(matrix_array)
    mmwrite(matrix_path, nonnegative_int_matrix, field="integer")


# Based on https://github.com/Lamagraph/QTreeInpla/blob/main/scripts/simple_mtx_reordering.py
def reorder_rcm_array(matrix_array):
    """
    Переупорядочивание с помощью обратного алгоритма Катхилла-Макки (RCM).
    Возвращает перестановку для строк и столбцов (одна и та же).
    """
    # Симметризуем структуру ненулевых элементов
    matrix_array_bin = (matrix_array != 0).astype(int)  # type: ignore
    matrix_array_sym = (matrix_array_bin + matrix_array_bin.T) > 0
    matrix_array_sym = matrix_array_sym.tocsr()
    matrix_array_sym.setdiag(0)  # убираем петли (диагональ)
    matrix_array_sym.eliminate_zeros()

    # Вычисляем перестановку RCM
    perm = sp.csgraph.reverse_cuthill_mckee(matrix_array_sym, symmetric_mode=True)
    return perm


def reorder_rcm_matrix(matrices_path: Path, matrix: Matrix):
    matrix_path = matrices_path / (matrix.name + ".mtx")
    matrix_array = mmread(matrix_path, spmatrix=False).tocsr()
    if matrix_array.shape[0] != matrix_array.shape[1]:
        log.warning("Rectangle matrix detected. Only rows will be reordered.")
    perm = reorder_rcm_array(matrix_array)
    if matrix_array.shape[0] == matrix_array.shape[1]:
        matrix_array_reordered = matrix_array[perm, :][:, perm]
    else:
        matrix_array_reordered = matrix_array[perm, :]
    name, ext = os.path.splitext(matrix_path)
    matrix_path = name + "_reordered" + ext
    mmwrite(matrix_path, matrix_array_reordered)


@app.command()
def prepare_matrices(
    matrices_spec_path: FilePathOption = Path("matrices.yaml"),
    matrices_path: DirPathOption = Path("matrices"),
):
    log.info("Reading matrices spec from %s", matrices_spec_path)
    matrices = get_enabled_matrices(matrices_spec_path)
    matrices_unique = get_unique_by_name_matrices(matrices)

    log.info("Making matrices nonnegative int")
    for matrix in matrices_unique:
        log.info("Making %s nonnegative", matrix.name)
        make_matrix_nonnegative_int(matrices_path, matrix)

    matrices_for_reorder = list(filter(lambda matrix: matrix.reorder, matrices))
    matrices_for_reorder = get_unique_by_name_matrices(matrices_for_reorder)
    log.info("Creating reordered matrices")
    for matrix in matrices_for_reorder:
        log.info("Creating reorder of %s", matrix.name)
        reorder_rcm_matrix(matrices_path, matrix)
