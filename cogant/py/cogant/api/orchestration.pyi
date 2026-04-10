from typing import Any

from _typeshed import Incomplete

from cogant.graph.builder import ProgramGraphBuilder as ProgramGraphBuilder
from cogant.ingest.repo import RepoIngester as RepoIngester
from cogant.ingest.repo import RepoSnapshot as RepoSnapshot
from cogant.normalize.canonical import CanonicalNormalizer as CanonicalNormalizer
from cogant.normalize.canonical import LanguageFact as LanguageFact
from cogant.process.extractor import ProcessExtractor as ProcessExtractor
from cogant.schemas.core import EdgeKind as EdgeKind
from cogant.schemas.core import NodeKind as NodeKind
from cogant.schemas.graph import ProgramGraph as ProgramGraph
from cogant.schemas.semantic import SemanticMapping as SemanticMapping
from cogant.statespace.compiler import StateSpaceCompiler as StateSpaceCompiler
from cogant.static.parser import PythonASTParser as PythonASTParser
from cogant.translate.confidence import ConfidenceModel as ConfidenceModel
from cogant.translate.engine import TranslationEngine as TranslationEngine
from cogant.translate.review import ReviewManager as ReviewManager
from cogant.translate.rules import ActionRule as ActionRule
from cogant.translate.rules import CircuitBreakerRule as CircuitBreakerRule
from cogant.translate.rules import ConfigRule as ConfigRule
from cogant.translate.rules import ContainmentRule as ContainmentRule
from cogant.translate.rules import ContextRule as ContextRule
from cogant.translate.rules import DataPipelineRule as DataPipelineRule
from cogant.translate.rules import ErrorBoundaryRule as ErrorBoundaryRule
from cogant.translate.rules import EventBusRule as EventBusRule
from cogant.translate.rules import FeatureFlagRule as FeatureFlagRule
from cogant.translate.rules import InheritanceRule as InheritanceRule
from cogant.translate.rules import MutatingSubsystemRule as MutatingSubsystemRule
from cogant.translate.rules import ObservationRule as ObservationRule
from cogant.translate.rules import OrchestratorRule as OrchestratorRule
from cogant.translate.rules import PolicyRule as PolicyRule
from cogant.translate.rules import PreferenceRule as PreferenceRule
from cogant.translate.rules import ReadOnlyInputRule as ReadOnlyInputRule
from cogant.translate.rules import RetryPatternRule as RetryPatternRule
from cogant.translate.rules import SingletonAccessRule as SingletonAccessRule
from cogant.translate.rules import TestAssertionRule as TestAssertionRule
from cogant.validate.schema_check import SchemaValidator as SchemaValidator

logger: Incomplete

def program_graph_to_dict(pg: ProgramGraph, statistics: dict[str, Any] | None = None) -> dict[str, Any]: ...
def run_ingest(bundle_target: str, bundle: Any) -> dict[str, Any]: ...
def run_static(bundle: Any) -> dict[str, Any]: ...
def run_normalize(bundle: Any) -> dict[str, Any]: ...
def run_graph(bundle: Any, target: str) -> dict[str, Any]: ...
def run_translate(bundle: Any) -> dict[str, Any]: ...
def run_statespace(bundle: Any, target: str) -> dict[str, Any]: ...
def run_process(bundle: Any, target: str) -> dict[str, Any]: ...
def run_export(bundle: Any, output_dir: str) -> dict[str, Any]: ...
def run_validate(bundle: Any) -> dict[str, Any]: ...
def run_dynamic(bundle: Any, coverage_path: str | None = None, trace_path: str | None = None) -> dict[str, Any]: ...
