from pathlib import Path
import shutil
from typing import Annotated

import requests
import typer
import yaml


def get_matrices(path: Path) -> dict[str, str]:
    with open(path, "r", encoding="utf-8") as m_file:
        matrices = yaml.safe_load(m_file)
    enabled_matrices = filter(lambda matrix: matrix["enabled"], matrices)
    return dict(
        map(
            lambda matrix: ((matrix["name"], matrix["link"])),
            enabled_matrices,
        )
    )


def download_matrix(tmp_path: Path, url: str) -> Path:
    matrix = requests.get(url, allow_redirects=True)
    filename = url.split("/")[-1]
    full_path = tmp_path / filename
    with open(full_path, "wb+") as f:
        f.write(matrix.content)
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
        print("Wrote", output)


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
    tmp_path: Annotated[
        Path,
        typer.Option(
            file_okay=False,
            dir_okay=True,
            readable=True,
            writable=True,
            resolve_path=True,
        ),
    ] = Path("tmp"),
):
    print("Reading matrices spec from", matrices_spec_path)
    matrices = get_matrices(matrices_spec_path)
    print("Enabled matrices:", ", ".join(matrices.keys()))

    tmp_path.mkdir(exist_ok=True)
    matrices_path.mkdir(exist_ok=True)

    temp_paths = []
    for name, link in matrices.items():
        print("Downloading", name)
        downloaded_path = download_matrix(tmp_path, link)
        temp_paths.append(downloaded_path)
    for matrix in temp_paths:
        unpack_matrix(matrix, matrices_path)


if __name__ == "__main__":
    typer.run(main)
