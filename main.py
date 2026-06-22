import logging

import typer
from rich.logging import RichHandler

from src.download import app as download_app

app = typer.Typer()
app.add_typer(download_app)

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
