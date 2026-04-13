"""COGANT static analysis pipeline: Python AST parsing and symbol extraction.

Provides tools for parsing Python source code, extracting symbols, resolving imports,
building call graphs, inferring types, and analyzing data flow.
"""

from __future__ import annotations

from cogant.static.calls import CallEdge, CallGraphBuilder
from cogant.static.complexity import ComplexityAnalyzer, ComplexityEntry, ComplexityReport
from cogant.static.coupling import CouplingAnalyzer, CouplingReport, ModuleCouplingMetrics
from cogant.static.dataflow import DataFlowAnalyzer, DataFlowEdge, DataFlowGraph
from cogant.static.dead_code import DeadCodeAnalyzer, DeadCodeEntry, DeadCodeReport
from cogant.static.imports import ImportAnalyzer, ImportEdge
from cogant.static.metrics import CodeMetrics, HalsteadMetrics, MetricsAnalyzer
from cogant.static.parser import (
    AssignmentDef,
    ClassDef,
    FunctionDef,
    ImportDef,
    PythonASTParser,
    PythonModule,
)
from cogant.static.symbols import SymbolExtractor, SymbolInfo, SymbolTable
from cogant.static.types import TypeInferencer, TypeInfo

__all__ = [
    "PythonASTParser",
    "FunctionDef",
    "ClassDef",
    "ImportDef",
    "AssignmentDef",
    "PythonModule",
    "SymbolExtractor",
    "SymbolInfo",
    "SymbolTable",
    "ImportAnalyzer",
    "ImportEdge",
    "CallGraphBuilder",
    "CallEdge",
    "TypeInferencer",
    "TypeInfo",
    "DataFlowAnalyzer",
    "DataFlowEdge",
    "DataFlowGraph",
    "ComplexityAnalyzer",
    "ComplexityEntry",
    "ComplexityReport",
    "CouplingAnalyzer",
    "CouplingReport",
    "ModuleCouplingMetrics",
    "DeadCodeAnalyzer",
    "DeadCodeEntry",
    "DeadCodeReport",
    "CodeMetrics",
    "HalsteadMetrics",
    "MetricsAnalyzer",
]
