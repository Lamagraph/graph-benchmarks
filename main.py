import logging

import typer
from rich.logging import RichHandler

from src.benchmark import app as benchmark_app
from src.common import (
    DEFAULT_LOGS_PATH,
    LOGGER_NAME,
    get_timestamp,
)
from src.download import app as download_app
from src.prepare_matrices import app as prepare_matrices_app

app = typer.Typer(no_args_is_help=True)
app.add_typer(download_app)
app.add_typer(prepare_matrices_app)
app.add_typer(benchmark_app, name="benchmark")

logger = logging.getLogger(LOGGER_NAME)
logger.setLevel(logging.INFO)

DEFAULT_LOGS_PATH.mkdir(exist_ok=True)
timestamp = get_timestamp()
log_filename = DEFAULT_LOGS_PATH / f"log_{timestamp}.log"

rich_handler = RichHandler()
file_handler = logging.FileHandler(log_filename)
file_handler.setFormatter(
    logging.Formatter("%(asctime)-15s - %(levelname)s - %(message)s")
)

logger.addHandler(rich_handler)
logger.addHandler(file_handler)


if __name__ == "__main__":
    app()
