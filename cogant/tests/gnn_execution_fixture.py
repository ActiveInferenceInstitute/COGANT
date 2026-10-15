from pathlib import Path

from cogant.gnn.runner import ExecutionTrace, GNNModelRunner

MODEL = """## ModelName
MatrixRunner

## StateSpaceBlock
s_f0[2,1,type=int]
o_m0[2,1,type=float]
u_c0[2,1,type=int]

## ActInfOntologyAnnotation
s_f0=HiddenState
o_m0=Observation
u_c0=Action

## State Space
```gnn-matrices
A[[rows=2][cols=2]]
0.9 0.2
0.1 0.8
B[[rows=2][cols=2][depth=2]]
# action=0
1.0 0.0
0.0 1.0
# action=1
0.0 0.0
1.0 1.0
C[[rows=2][cols=1]]
0.0
4.0
D[[rows=2][cols=1]]
0.75
0.25
```
"""


def package(path: Path, text: str = MODEL) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "manifest.json").write_text('{"version":"1.0","name":"matrix_runner"}')
    (path / "model.gnn.md").write_text(text)
    return path


def runner(path: Path, text: str = MODEL) -> GNNModelRunner:
    result = GNNModelRunner()
    result.load_package(str(package(path, text)))
    return result


def trace(path: Path) -> ExecutionTrace:
    result = runner(path)
    result.run(1)
    return result.traces[0]
