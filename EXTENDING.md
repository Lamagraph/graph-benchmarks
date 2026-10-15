# Extending with another tool

This document describes how to add a new tool to the benchmark suite.

A *tool* is an external program that runs one of the supported algorithms (`BFS`, `SSSP`, `TC`) on a Matrix Market file and reports its timing.
Tools are invoked through `uv run main.py benchmark <tool>`, and the results are written to `results/raw/<timestamp>_<tool>.json`.

## Data flow

```
uv run main.py download            # matrices/*.mtx
uv run main.py prepare-matrices    # matrices/*_reordered.mtx
uv run main.py benchmark <tool>    # results/raw/<timestamp>_<tool>.json
```

The benchmark command reads `matrices.yaml`, selects the entries that list your tool, prepares them (symmetric links or conversion), runs the tool, and writes the results.

## Integration styles

Two styles are already used in the repository.
Pick the one that matches how your tool reports timings.

* **Style A — subprocess and stdout parsing** (`src/benchmark/lagraph.py`, `src/benchmark/inpla.py`).
  The tool prints timings to stdout.
  Reuse `run_benchmarks` from `src/common.py` and store the raw stdout lines.
* **Style B — custom collector** (`src/benchmark/fsharp.py`, `src/benchmark/networkx.py`).
  The tool emits its own structured report (BenchmarkDotNet, pytest-benchmark, ...).
  Run the harness, transform its output into the shared `Results` shape, and store it.

## Prerequisites

### Tool repository

Place the benchmark harness and the algorithm sources in `tools/<name>`.
Upstream libraries or virtual machines that a tool is built on top of go to `dependencies/<name>`.
For example Inpla is split between `dependencies/inpla` (the interpreter) and `tools/QTreeInpla` (the benchmark programs).

Each repository must be added as a submodule.

### `--check` convention

Benchmark commands expose an optional `--check` flag that runs the tool's own test suite before benchmarking.
Follow the existing naming (`check_inpla`, `check_GraphBLAS`, `check_LAGraph`) so the flag behaves consistently.

## Step 1 — Register the tool identity

Add a variant to the `Tool` enum in `src/common.py`:

```python
class Tool(StrEnum):
    NETWORKX = auto()
    FSHARP = auto()
    INPLA = auto()
    LAGRAPH = auto()
    VINE = auto()
    MYTOOL = auto()  # TODO: your tool
```

The lowercase form of the name (`mytool`) is used in `matrices.yaml` and in the raw results file name.

## Step 2 — Implement `src/benchmark/<tool>.py`

Every benchmark module follows the same structure: a `typer.Typer` application and a logger that shares the application logger.

```python
import logging
from pathlib import Path
import subprocess
from typing import Annotated

import typer

from ..common import (
    DEFAULT_MATRICES_PATH,
    DEFAULT_MATRICES_SPEC_PATH,
    DEFAULT_RAW_RESULTS_PATH,
    DEFAULT_TOOLS_PATH,
    LOGGER_NAME,
    Matrix,
    Tool,
    comma_separated_str_to_int_list,
    get_enabled_matrices_for_tool,
    get_matrix_filename_mtx,
    run_benchmarks,
    write_results,
)
from ..type_aliases import DirPathOption, FilePathOption

app = typer.Typer()
logger = logging.getLogger(LOGGER_NAME)
```

Use the shared option aliases from `src/type_aliases.py` (`FilePathOption` for files, `DirPathOption` for directories) and keep the common command signature:

```python
@app.command()
def mytool(
    matrices_spec_path: FilePathOption = DEFAULT_MATRICES_SPEC_PATH,
    matrices_path: DirPathOption = DEFAULT_MATRICES_PATH,
    mytool_bench_path: DirPathOption = DEFAULT_TOOLS_PATH / "my-bench",
    raw_results_path: DirPathOption = DEFAULT_RAW_RESULTS_PATH,
    check: Annotated[bool, typer.Option()] = False,
    run_count: Annotated[int, typer.Option] = 5,
    thread_counts: Annotated[str | None, typer.Option()] = None,
): ...
```

`thread_counts` is passed as a comma-separated string because Typer does not parse lists from the command line; convert it with `comma_separated_str_to_int_list` from `src/common.py`.
When it is `None`, `run_benchmarks` falls back to `[1] + list(range(2, os.cpu_count() + 1, 2))`.

### Style A — subprocess and stdout parsing

Select the relevant matrices, define a runner that maps a matrix and a thread count to a process invocation, and delegate the timing loop to `run_benchmarks`.
The runner must honour the requested thread count, for example through an environment variable or a command-line flag.

```python
def run_mytool(
    matrix: Matrix,
    thread_count: int,
    *,
    mytool_bench_path: Path,
    matrices_path: Path,
) -> subprocess.CompletedProcess[str]:
    # TODO: build the command, pass thread_count and the matrix path
    return subprocess.run(
        [
            Path("build") / ("mytool_" + matrix.algorithm),
            matrices_path / get_matrix_filename_mtx(matrix),
        ],
        cwd=mytool_bench_path,
        capture_output=True,
        text=True,
        env={"OMP_NUM_THREADS": str(thread_count)},  # or an equivalent flag
        check=True,
    )
```

Then in the command body:

```python
matrices = get_enabled_matrices_for_tool(matrices_spec_path, Tool.MYTOOL)
thread_counts_t = comma_separated_str_to_int_list(thread_counts)
results = run_benchmarks(
    matrices,
    thread_counts_t,
    run_count,
    run_mytool,
    matrices_path=matrices_path,
    mytool_bench_path=mytool_bench_path,
)
write_results(results, raw_results_path, Tool.MYTOOL)
```

### Style B — custom collector

When the tool produces a structured report, build or sync the harness, clean stale artifacts, make the matrices visible to it, run it, and then map its report into `Results` before calling `write_results`.

```python
matrices = get_enabled_matrices_for_tool(matrices_spec_path, Tool.MYTOOL)

clean_artifacts(mytool_bench_path)  # remove stale symlinks / reports
symlink_matrices(matrices, matrices_path, mytool_bench_path)
run_harness(mytool_bench_path)  # uv run pytest, dotnet run, ...

results: Results = make_empty_results()
collect_results(results, mytool_bench_path)  # fill the shared shape
write_results(results, raw_results_path, Tool.MYTOOL)
```

Reuse the existing helpers as templates: `clean_symlinks` and `symlink_matrices` in `src/benchmark/networkx.py`, and `patch_benchmarks`/`collect_results` in `src/benchmark/fsharp.py`.
Besides the imports above, Style B usually needs `Results`, `make_empty_results` and `get_unique_by_name_matrices` from `src/common.py`.
Use `get_unique_by_name_matrices` when the harness must not receive the same matrix twice, and `get_matrix_filename_mtx` for the file name.

If the tool cannot be run with a different thread count, run it once and repeat its result across every requested thread count at plotting time, as NetworkX and QTreeFSharp do.

## Step 3 — Register the CLI

Add the new application to `src/benchmark/__init__.py`:

```python
from .mytool import app as mytool_app

app = typer.Typer(no_args_is_help=True)
app.add_typer(mytool_app)
```

The command name is derived from the function name, so `uv run main.py benchmark mytool` becomes available.

## Step 4 — Enable matrices

Add the tool to the `tools` list of the entries you want to benchmark in `matrices.yaml`:

```yaml
- name: gr_30_30
  enabled: true
  algorithm: bfs
  tools:
    - lagraph
    - mytool
  reorder: false
  link: https://suitesparse-collection-website.herokuapp.com/MM/HB/gr_30_30.tar.gz
```

Keep `enabled: true` and list the tool in every entry you want to run; entries with `reorder: true` produce an additional `_reordered` matrix.

## Step 5 — Results schema

`write_results` serializes a `Results` value to `results/raw/<timestamp>_<toolname>.json`:

```json
{
  "bfs": {
    "gr_30_30": {"1": ["...stdout...", "..."]},
    "gr_30_30_reordered": {"1": ["..."]}
  },
  "sssp": {},
  "tc": {}
}
```

* The outer keys are the algorithm values (`bfs`, `sssp`, `tc`).
* The inner keys are the matrix base names from `get_matrix_base_name` (`name` plus `_reordered` when the entry has `reorder: true`).
* The innermost keys are thread counts as strings, each mapped to one entry per run.
  Style A stores raw stdout; Style B stores whatever value downstream parsing expects.

Always persist through `write_results` so the file name keeps the `<timestamp>_<tool>.json` convention that the plotting code relies on.
After a run, confirm that the `<timestamp>_<tool>.json` file was created under `results/raw/` and parses as JSON.

## Checklist

* [ ] Tool repositories added under `tools/` and/or `dependencies/` as submodules.
* [ ] The `--check` path implemented (if available).
* [ ] `Tool` variant added in `src/common.py`.
* [ ] `src/benchmark/<tool>.py` implemented, using the shared options and helpers.
* [ ] Application registered in `src/benchmark/__init__.py`.
* [ ] Tool added to the relevant `tools` lists in `matrices.yaml`.
* [ ] Results written through `write_results`.
* [ ] Formatting and linting checked with `uv run ruff format .` and `uv run ruff check .`.

## Conventions

* In general, see `AGENTS.md`.
* Log progress with the module-level `logger = logging.getLogger(LOGGER_NAME)`.
