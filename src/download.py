import logging
import shutil
from pathlib import Path

import requests
import typer

from .common import Matrix, get_enabled_matrices, get_unique_by_name_matrices
from .type_aliases import DirPathOption, FilePathOption

app = typer.Typer()
logger = logging.getLogger("app")


def download_matrix(matrix: Matrix, tmp_path: Path) -> Path:
    matrix_resp = requests.get(matrix.link, allow_redirects=True)
    filename = matrix.link.split("/")[-1]
    full_path = tmp_path / filename
    with open(full_path, "wb+") as f:
        f.write(matrix_resp.content)
    return full_path


def unpack_matrix(matrix_archive_path: Path, matrices_path: Path) -> None:
    shutil.unpack_archive(matrix_archive_path, matrix_archive_path.parent)
    paths_to_copy = list(
        Path(matrix_archive_path.parent).glob(
            f"**/{matrix_archive_path.name.split('.')[0]}.mtx"
        )
    )
    for path in paths_to_copy:
        output = shutil.copy(path, matrices_path)
        logger.info("Unpacked to %s", output)


@app.command()
def download(
    matrices_spec_path: FilePathOption = Path("matrices.yaml"),
    matrices_path: DirPathOption = Path("matrices"),
    tmp_path: DirPathOption = Path("tmp"),
):
    logger.info("Reading matrices spec from %s", matrices_spec_path)
    matrices = get_enabled_matrices(matrices_spec_path)
    matrices = get_unique_by_name_matrices(matrices)
    matrix_names = [matrix.name for matrix in matrices]
    logger.info("Enabled matrices: %s", matrix_names)

    logger.info("Creating %s", tmp_path)
    tmp_path.mkdir(exist_ok=True)
    logger.info("Creating %s", tmp_path)
    matrices_path.mkdir(exist_ok=True)

    for matrix in matrices:
        if (matrices_path / (matrix.name + ".mtx")).exists():
            logger.info("%s already downloaded, skipping", matrix.name)
            continue

        logger.info("Downloading %s", matrix.name)
        matrix_archive_path = download_matrix(matrix, tmp_path)
        logger.info("Unpacking %s", matrix_archive_path)
        unpack_matrix(matrix_archive_path, matrices_path)
