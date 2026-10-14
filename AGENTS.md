# AGENTS.md

Benchmark infrastructure comparing Interaction Nets-based implementations of linear-algebra graph algorithms (QTreeVine, QTreeInpla) against references (QTreeFSharp, NetworkX, LAGraph). Algorithms: BFS, SSSP, Triangle Counting.

## Tools

- Main automation language: Python (>=3.13)
- Dependency management tool: uv
- Linter and formatter: ruff
- CLI parser: typer

## Commands

```console
$ git submodule update --init --recursive  # required after clone
$ uv sync
$ uv run main.py download                 # may need ALL_PROXY set (socks5) to fetch matrices
$ uv run main.py prepare-matrices
$ uv run main.py benchmark <tool>          # inpla | fsharp | lagraph | networkx
$ uv run ruff format . && uv run ruff check .
```

`uv run main.py --help` lists all subcommands; `src/` mirrors typer's subcommand hierarchy.

## Rules

- After writing a file check its formatting and code with ruff
- Always ask if you want to change formatting or linting rules
- Always use type hints
- Write comments only when it's absolutely necessary. Usually when the meaning cannot be directly inferred from the code. Comments like "We need to iterate over list" for `for` loop must be omitted.
- There is no test suite; verification is a smoke benchmark run (see above) plus ruff.

## Repository structure

- `dependencies` --- libraries or virtual machines used to write/execute algorithms, added as submodules
- `tools` --- implementations of algorithms, added as submodules
- `src` --- main storage for scripts, directory structure follows `typer`'s subcommand hierarchy
- `scripts` --- deprecated, was used before transition to `src`, usually should be ignored.
- `matrices.yaml` --- matrix/tool spec; a tool only runs matrices that list it in their `tools` entry.
- `results/raw/<timestamp>_<tool>.json` --- output of benchmarks; the file name convention is relied on by the plotting code.

## Adding a new tool

Follow `EXTENDING.md` — it documents the full workflow: `Tool` enum in `src/common.py`, `src/benchmark/<tool>.py` (Style A: subprocess/stdout parsing; Style B: custom collector), CLI registration in `src/benchmark/__init__.py`, enabling matrices in `matrices.yaml`, and writing results through `write_results`.
