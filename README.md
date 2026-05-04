This repository contains infrastructure for comparison of different Interaction Nets based implementations of linear-algebra-based graph analysis including implemented in
* [Vine](https://github.com/Lamagraph/QTreeVine)
* [Inpla](https://github.com/Lamagraph/QTreeInpla)

As reference we use
* Single thread [F# implementation](https://github.com/Lamagraph/QTreeFSharp) that is a prototype for Vina and Inpla.
* [NetworkX](https://networkx.org/en/) --- well-known Python package for graph analysis.
* [LAGraph](https://github.com/GraphBLAS/LAGraph) --- collection of linear algebra based graph analysis algorithms implemented using SuiteSparse:GraphBLAS.

## Algorithms

* Level-BFS
* SSSP
* triangle counting (Sandia)

# How to run

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

# Results

Brief results are presented below.
Full report can be found [here](https://github.com/YaccConstructor/articles/blob/master/InProgress/GraphBLAS_in_InteractionNets/GraphBLAS_in_Interaction_Nets.pdf).

### Graphs

| Graph              | \|V\|   | \|E\|   |
|--------------------|---------|---------|
| boneS01            | 127,224 | 5,516,602 |
| usroads-48         | 126,146 | 323,900   |
| Trefethen_2000     | 2,000   | 41,906    |
| gr_30_30           | 900     | 7,744     |

We use both original matrices and reordered using reverse Cuthill–McKee algorithm.

### Evaluation Results

![bfs for bone and usroads](/figures/usroads_and_bone_all.svg)
![bfs for Trefethen_2000](/figures/bfs_trefethen_2000.svg)
![sssp for Trefethen_2000](/figures/sssp_trefethen_2000.svg)
![tc for gr_30_30](/figures/tc_gr_30_30.svg)