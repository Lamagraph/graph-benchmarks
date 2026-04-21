`uv` must be installed in the system (see https://docs.astral.sh/uv/getting-started/installation/)

```console
$ git submodule update --init --recursive
$ uv sync
$ set -x ALL_PROXY "socks5h://127.0.0.1:12334" # Or something like this may be required to download matrices
$ uv run scripts/download_matrices.py
$ uv run scripts/prepare_matrices.py
$ # In arbitrary order
$ uv run scripts/run_networkx.py
$ uv run scripts/run_lagraph.py
$ uv run scripts/run_fsharp.py
$ uv run scripts/run_inpla.py
$ # Now get raw results from `results/raw` or run
$ uv run scripts/plot_experiments.py
```
