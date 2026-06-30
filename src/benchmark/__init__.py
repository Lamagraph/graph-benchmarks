import typer

from .lagraph import app as lagraph_app
from .fsharp import app as fsharp_app
from .networkx import app as networkx_app
from .inpla import app as inpla_app

app = typer.Typer(no_args_is_help=True)

app.add_typer(lagraph_app)
app.add_typer(fsharp_app)
app.add_typer(networkx_app)
app.add_typer(inpla_app)
