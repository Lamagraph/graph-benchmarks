from pathlib import Path
from typing import Annotated

import typer


FilePathOption = Annotated[
    Path,
    typer.Option(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
]

DirPathOption = Annotated[
    Path,
    typer.Option(
        file_okay=False,
        dir_okay=True,
        readable=True,
        writable=True,
        resolve_path=True,
    ),
]
