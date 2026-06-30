from datetime import datetime
import logging
from pathlib import Path

import typer
from rich.logging import RichHandler

from src.download import app as download_app
from src.prepare_matrices import app as prepare_matrices_app
from src.benchmark import app as benchmark_app

app = typer.Typer(no_args_is_help=True)
app.add_typer(download_app)
app.add_typer(prepare_matrices_app)
app.add_typer(benchmark_app, name="benchmark")

logger = logging.getLogger("app")
logger.setLevel(logging.INFO)

Path("logs").mkdir(exist_ok=True)
timestamp = datetime.now().astimezone().isoformat(timespec="minutes")
log_filename = Path("logs") / f"log_{timestamp}.log"

rich_handler = RichHandler()
file_handler = logging.FileHandler(log_filename)
file_handler.setFormatter(
    logging.Formatter("%(asctime)-15s - %(levelname)s - %(message)s")
)

logger.addHandler(rich_handler)
logger.addHandler(file_handler)


if __name__ == "__main__":
    app()
