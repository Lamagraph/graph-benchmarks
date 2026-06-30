import logging

import typer
from rich.logging import RichHandler

from src.download import app as download_app
from src.prepare_matrices import app as prepare_matrices_app
from src.benchmark import app as benchmark_app

app = typer.Typer(no_args_is_help=True)
app.add_typer(download_app)
app.add_typer(prepare_matrices_app)
app.add_typer(benchmark_app, name="benchmark")

log_file_handler = logging.FileHandler("log.txt")

FORMAT = "%(message)s"
logging.basicConfig(
    level="NOTSET",
    format=FORMAT,
    datefmt="[%X]",
    handlers=[RichHandler(), log_file_handler],
)

log = logging.getLogger("rich")


if __name__ == "__main__":
    app()
