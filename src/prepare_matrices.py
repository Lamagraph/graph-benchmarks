import logging
import os
from pathlib import Path

import scipy.sparse as sp
import typer
from scipy.io import mmread, mmwrite

from .common import (
    DEFAULT_MATRICES_PATH,
    DEFAULT_MATRICES_SPEC_PATH,
    LOGGER_NAME,
    MTX_EXTENSION,
    REORDERED_SUFFIX,
    Matrix,
    get_enabled_matrices,
    get_unique_by_name_matrices,
)
from .type_aliases import DirPathOption, FilePathOption

app = typer.Typer()
logger = logging.getLogger(LOGGER_NAME)


def make_coo_array_nonnegative_int(matrix):
    matrix = matrix.trunc()
    min_element = matrix.min()
    if min_element < 0:
        to_add = abs(min_element)
        matrix.data += to_add
        matrix.eliminate_zeros()
    return matrix


def make_matrix_nonnegative_int(matrices_path: Path, matrix: Matrix):
    matrix_path = matrices_path / (matrix.name + MTX_EXTENSION)
    matrix_array = mmread(matrix_path, spmatrix=False)
    nonnegative_int_matrix = make_coo_array_nonnegative_int(matrix_array)
    mmwrite(matrix_path, nonnegative_int_matrix, field="integer")


# Based on https://github.com/Lamagraph/QTreeInpla/blob/main/scripts/simple_mtx_reordering.py
def reorder_rcm_array(matrix_array):
    """
    Reorder with the Reverse Cuthill-McKee (RCM) algorithm.
    Returns the permutation for rows and columns (the same one for both).
    """
    matrix_array_bin = (matrix_array != 0).astype(int)  # type: ignore
    matrix_array_sym = (matrix_array_bin + matrix_array_bin.T) > 0
    matrix_array_sym = matrix_array_sym.tocsr()
    matrix_array_sym.setdiag(0)  # remove self-loops (diagonal)
    matrix_array_sym.eliminate_zeros()

    perm = sp.csgraph.reverse_cuthill_mckee(matrix_array_sym, symmetric_mode=True)
    return perm


def reorder_rcm_matrix(matrices_path: Path, matrix: Matrix):
    matrix_path = matrices_path / (matrix.name + MTX_EXTENSION)
    matrix_array = mmread(matrix_path, spmatrix=False).tocsr()
    if matrix_array.shape[0] != matrix_array.shape[1]:
        logger.warning("Rectangle matrix detected. Only rows will be reordered.")
    perm = reorder_rcm_array(matrix_array)
    if matrix_array.shape[0] == matrix_array.shape[1]:
        matrix_array_reordered = matrix_array[perm, :][:, perm]
    else:
        matrix_array_reordered = matrix_array[perm, :]
    name, ext = os.path.splitext(matrix_path)
    matrix_path = name + REORDERED_SUFFIX + ext
    mmwrite(matrix_path, matrix_array_reordered)


@app.command()
def prepare_matrices(
    matrices_spec_path: FilePathOption = DEFAULT_MATRICES_SPEC_PATH,
    matrices_path: DirPathOption = DEFAULT_MATRICES_PATH,
):
    logger.info("Reading matrices spec from %s", matrices_spec_path)
    matrices = get_enabled_matrices(matrices_spec_path)
    matrices_unique = get_unique_by_name_matrices(matrices)

    logger.info("Making matrices nonnegative int")
    for matrix in matrices_unique:
        logger.info("Making %s nonnegative", matrix.name)
        make_matrix_nonnegative_int(matrices_path, matrix)

    matrices_for_reorder = list(filter(lambda matrix: matrix.reorder, matrices))
    matrices_for_reorder = get_unique_by_name_matrices(matrices_for_reorder)
    logger.info("Creating reordered matrices")
    for matrix in matrices_for_reorder:
        logger.info("Creating reorder of %s", matrix.name)
        reorder_rcm_matrix(matrices_path, matrix)
