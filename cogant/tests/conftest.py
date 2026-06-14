"""Shared fixtures and utilities for COGANT tests."""

import sys
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

# Ensure `py/cogant` is importable when tests run without an editable install on PYTHONPATH.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_PY_ROOT = _REPO_ROOT / "py"
if _PY_ROOT.is_dir() and str(_PY_ROOT) not in sys.path:
    sys.path.insert(0, str(_PY_ROOT))


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(autouse=True)
def close_matplotlib_figures_between_tests() -> Generator[None, None, None]:
    """Keep figure-returning visualization tests isolated.

    COGANT visualization APIs intentionally return live matplotlib figures so
    callers can save or inspect them. Tests must not let those figures
    accumulate across files, because later valid renders can otherwise trip
    matplotlib's global open-figure warning.
    """
    yield
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return
    plt.close("all")


@pytest.fixture
def sample_python_code() -> str:
    """Sample Python code for parser testing."""
    return '''
"""Sample module for testing."""

import os
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class User:
    """A user entity."""
    id: int
    name: str
    email: str
    is_active: bool = True


class Database:
    """Simple database wrapper."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.users = []

    def connect(self) -> bool:
        """Connect to database."""
        return True

    def create_user(self, user: User) -> User:
        """Create a new user."""
        self.users.append(user)
        return user

    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        for user in self.users:
            if user.id == user_id:
                return user
        return None


def process_users(db: Database) -> List[str]:
    """Process all users in the database."""
    return [user.name for user in db.users]


async def fetch_and_store(url: str, db: Database) -> bool:
    """Fetch data and store in database."""
    try:
        # Simulate fetch
        user = User(id=1, name="Test", email="test@example.com")
        db.create_user(user)
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
'''


@pytest.fixture
def sample_python_service_path(temp_dir: Path) -> Path:
    """Create a sample Python service directory structure."""
    service_dir = temp_dir / "example-service"
    service_dir.mkdir()

    # Create package structure
    (service_dir / "src").mkdir()
    (service_dir / "src" / "app").mkdir()
    (service_dir / "src" / "app" / "__init__.py").touch()
    (service_dir / "src" / "app" / "main.py").write_text("""
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World"}
""")

    (service_dir / "tests").mkdir()
    (service_dir / "tests" / "__init__.py").touch()
    (service_dir / "tests" / "test_main.py").write_text("""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
""")

    return service_dir


@pytest.fixture
def sample_ast_structure() -> dict:
    """Sample AST structure for testing."""
    return {
        "type": "Module",
        "body": [
            {
                "type": "FunctionDef",
                "name": "hello_world",
                "args": {"args": [{"type": "arg", "arg": "name", "annotation": None}]},
                "body": [
                    {
                        "type": "Return",
                        "value": {
                            "type": "BinOp",
                            "left": {"type": "Constant", "value": "Hello, "},
                            "op": "Add",
                            "right": {"type": "Name", "id": "name"},
                        },
                    }
                ],
            }
        ],
    }


@pytest.fixture
def sample_graph_structure() -> dict:
    """Sample graph structure for testing."""
    return {
        "nodes": [
            {
                "id": "module:test",
                "type": "Module",
                "name": "test",
                "attributes": {"path": "test.py"},
            },
            {
                "id": "function:hello",
                "type": "Function",
                "name": "hello",
                "attributes": {
                    "parent": "module:test",
                    "arity": 1,
                },
            },
            {
                "id": "class:User",
                "type": "Class",
                "name": "User",
                "attributes": {
                    "parent": "module:test",
                    "base_classes": [],
                },
            },
        ],
        "edges": [
            {
                "source": "function:hello",
                "target": "class:User",
                "type": "uses",
                "confidence": 0.95,
            },
            {
                "source": "module:test",
                "target": "function:hello",
                "type": "defines",
                "confidence": 1.0,
            },
        ],
    }


@pytest.fixture
def sample_validation_report() -> dict:
    """Sample validation report."""
    return {
        "valid": True,
        "errors": [],
        "warnings": [
            {
                "type": "missing_docstring",
                "location": "module:test:function:hello",
                "message": "Function 'hello' has no docstring",
            }
        ],
        "statistics": {
            "total_nodes": 3,
            "total_edges": 2,
            "orphan_nodes": 0,
        },
    }


@pytest.fixture
def sample_confidence_data() -> dict:
    """Sample confidence scoring data."""
    return {
        "symbol_confidence": {
            "function:test:hello": {
                "source_evidence": 0.95,
                "type_evidence": 0.85,
                "usage_evidence": 0.9,
                "documentation": 0.5,
                "overall": 0.825,
            }
        },
        "edge_confidence": {
            "function:hello->class:User": {
                "call_evidence": 0.9,
                "type_evidence": 0.85,
                "usage_evidence": 0.88,
                "overall": 0.877,
            }
        },
    }


@pytest.fixture
def example_repo_path() -> Path:
    """Path to example Python service for integration tests."""
    return Path(__file__).parent.parent / "examples" / "python-service"


# Advanced fixtures for comprehensive unit tests


@pytest.fixture
def sample_graph():
    """Create a sample ProgramGraph with multiple nodes and edges."""

    from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
    from cogant.schemas.graph import GraphMetadata, ProgramGraph

    metadata = GraphMetadata(repo_uri="test://repo", languages={"python"}, version="1.0")
    graph = ProgramGraph(metadata=metadata)

    # Add various types of nodes
    nodes = [
        Node(
            id="repo:test",
            kind=NodeKind.REPO,
            name="test_repo",
            qualified_name="test_repo",
            path=".",
        ),
        Node(
            id="module:test.main",
            kind=NodeKind.MODULE,
            name="main",
            qualified_name="test.main",
            path="test/main.py",
        ),
        Node(
            id="class:Calculator",
            kind=NodeKind.CLASS,
            name="Calculator",
            qualified_name="test.main.Calculator",
            path="test/main.py",
            metadata={"bases": []},
        ),
        Node(
            id="function:add",
            kind=NodeKind.FUNCTION,
            name="add",
            qualified_name="test.main.Calculator.add",
            path="test/main.py",
            metadata={"arity": 2},
        ),
        Node(
            id="function:subtract",
            kind=NodeKind.FUNCTION,
            name="subtract",
            qualified_name="test.main.Calculator.subtract",
            path="test/main.py",
            metadata={"arity": 2},
        ),
        Node(
            id="variable:RESULT",
            kind=NodeKind.VARIABLE,
            name="RESULT",
            qualified_name="test.main.RESULT",
            path="test/main.py",
        ),
    ]

    for node in nodes:
        graph.add_node(node)

    # Add various types of edges
    edges = [
        Edge(
            id="edge:repo:test->module:test.main",
            source_id="repo:test",
            target_id="module:test.main",
            kind=EdgeKind.CONTAINS,
        ),
        Edge(
            id="edge:module->class",
            source_id="module:test.main",
            target_id="class:Calculator",
            kind=EdgeKind.CONTAINS,
        ),
        Edge(
            id="edge:class->add",
            source_id="class:Calculator",
            target_id="function:add",
            kind=EdgeKind.CONTAINS,
        ),
        Edge(
            id="edge:class->subtract",
            source_id="class:Calculator",
            target_id="function:subtract",
            kind=EdgeKind.CONTAINS,
        ),
        Edge(
            id="edge:add->variable",
            source_id="function:add",
            target_id="variable:RESULT",
            kind=EdgeKind.WRITES,
        ),
        Edge(
            id="edge:subtract->variable",
            source_id="function:subtract",
            target_id="variable:RESULT",
            kind=EdgeKind.WRITES,
        ),
    ]

    for edge in edges:
        graph.add_edge(edge)

    return graph


@pytest.fixture
def sample_mappings():
    """Create sample SemanticMappings for testing."""
    from cogant.schemas.semantic_mapping import SemanticMapping

    obs_mapping = SemanticMapping(
        id="mapping:obs1",
        name="counter_observation",
        category="observation",
        source_node_id="variable:counter",
        target_state_var="counter_value",
    )

    action_mapping = SemanticMapping(
        id="mapping:action1",
        name="increment_action",
        category="action",
        source_node_id="function:increment",
        target_action="increment_counter",
    )

    hidden_mapping = SemanticMapping(
        id="mapping:hidden1",
        name="internal_state",
        category="hidden_state",
        source_node_id="variable:internal",
        target_state_var="internal_state",
    )

    return {"observation": obs_mapping, "action": action_mapping, "hidden_state": hidden_mapping}


@pytest.fixture
def sample_state_space():
    """Create a sample StateSpaceModel for testing."""
    from cogant.schemas.state_space import Action, Observation, StateSpaceModel, StateVariable

    variables = [
        StateVariable(
            name="counter", dtype="int", domain_type="discrete", domain_values=[0, 1, 2, 3, 4, 5]
        ),
        StateVariable(
            name="status",
            dtype="str",
            domain_type="discrete",
            domain_values=["idle", "running", "stopped"],
        ),
    ]

    observations = [
        Observation(name="counter_obs", variable_name="counter"),
        Observation(name="status_obs", variable_name="status"),
    ]

    actions = [
        Action(
            name="increment",
            preconditions={"counter": {"type": "less_than", "value": 5}},
            effects={"counter": {"type": "add", "value": 1}},
        ),
        Action(name="reset", preconditions={}, effects={"counter": {"type": "set", "value": 0}}),
    ]

    model = StateSpaceModel(
        name="test_state_space",
        variables=variables,
        observations=observations,
        actions=actions,
        initial_state={"counter": 0, "status": "idle"},
    )

    return model


@pytest.fixture
def sample_process_model():
    """Create a sample ProcessModel for testing."""
    from cogant.schemas.process_model import ProcessModel, ProcessStage, ProcessTransition

    stages = [
        ProcessStage(id="stage:init", name="initialization", stage_type="entry_point"),
        ProcessStage(id="stage:processing", name="process_data", stage_type="processing"),
        ProcessStage(id="stage:output", name="generate_output", stage_type="processing"),
        ProcessStage(id="stage:complete", name="completion", stage_type="exit_point"),
    ]

    transitions = [
        ProcessTransition(
            id="trans:init->proc",
            source_id="stage:init",
            target_id="stage:processing",
            trigger_type="automatic",
        ),
        ProcessTransition(
            id="trans:proc->output",
            source_id="stage:processing",
            target_id="stage:output",
            trigger_type="automatic",
        ),
        ProcessTransition(
            id="trans:output->complete",
            source_id="stage:output",
            target_id="stage:complete",
            trigger_type="automatic",
        ),
    ]

    model = ProcessModel(
        id="process:test", name="test_process", stages=stages, transitions=transitions
    )

    return model


@pytest.fixture
def tmp_repo(temp_dir: Path) -> Path:
    """Create a temporary repository with sample Python files."""
    repo_dir = temp_dir / "sample_repo"
    repo_dir.mkdir()

    # Create main module
    (repo_dir / "main.py").write_text('''
"""Main module."""

import sys
from dataclasses import dataclass
from typing import List

@dataclass
class User:
    """User entity."""
    id: int
    name: str
    email: str

class Database:
    """Database manager."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    def connect(self) -> bool:
        return True

    def create_user(self, user: User) -> User:
        return user

def process_users(users: List[User]) -> int:
    """Process users."""
    return len(users)

async def fetch_data(url: str) -> dict:
    """Fetch data from URL."""
    return {"status": "ok"}
''')

    # Create utils module
    (repo_dir / "utils.py").write_text('''
"""Utility functions."""

def format_name(first: str, last: str) -> str:
    """Format full name."""
    return f"{first} {last}"

def validate_email(email: str) -> bool:
    """Validate email address."""
    return "@" in email
''')

    return repo_dir
