import typer

from .lagraph import app as lagraph_app

app = typer.Typer(no_args_is_help=True)

app.add_typer(lagraph_app)
