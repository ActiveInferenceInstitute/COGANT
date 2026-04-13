"""Unit tests for protocol definitions."""

import pytest
from typing import Any, Protocol

from cogant.protocols import (
    Translatable,
    Analyzable,
    Serializable,
    Visualizable,
    Validatable,
    Exportable,
    PipelineStage,
    TranslationRule,
    GraphBackend,
)


@pytest.mark.unit
class TestProtocolChecks:
    """Test runtime checking of protocol implementations."""

    def test_translatable_protocol_checking(self) -> None:
        """Test Translatable protocol with duck typing."""

        class MinimalTranslatable:
            def translate(self, graph: Any) -> Any:
                return {"result": "translated"}

        obj = MinimalTranslatable()
        assert isinstance(obj, Translatable)

    def test_analyzable_protocol_checking(self) -> None:
        """Test Analyzable protocol with duck typing."""

        class MinimalAnalyzable:
            def analyze(self) -> dict[str, Any]:
                return {"metrics": {}}

        obj = MinimalAnalyzable()
        assert isinstance(obj, Analyzable)

    def test_serializable_protocol_checking(self) -> None:
        """Test Serializable protocol with duck typing."""

        class MinimalSerializable:
            def to_dict(self) -> dict[str, Any]:
                return {"data": "value"}

            @classmethod
            def from_dict(cls, d: dict[str, Any]) -> "MinimalSerializable":
                return cls()

        obj = MinimalSerializable()
        assert isinstance(obj, Serializable)

    def test_serializable_missing_to_dict(self) -> None:
        """Test that missing to_dict fails protocol check."""

        class IncompleteSerializable:
            @classmethod
            def from_dict(cls, d: dict[str, Any]) -> "IncompleteSerializable":
                return cls()

        obj = IncompleteSerializable()
        assert not isinstance(obj, Serializable)

    def test_visualizable_protocol_checking(self) -> None:
        """Test Visualizable protocol with duck typing."""

        class MinimalVisualizable:
            def to_mermaid(self) -> str:
                return "graph TD; A-->B"

            def to_png(self, output_path: str) -> str:
                return output_path

        obj = MinimalVisualizable()
        assert isinstance(obj, Visualizable)

    def test_visualizable_missing_to_png(self) -> None:
        """Test that missing to_png fails protocol check."""

        class IncompleteVisualizable:
            def to_mermaid(self) -> str:
                return "graph TD"

        obj = IncompleteVisualizable()
        assert not isinstance(obj, Visualizable)

    def test_validatable_protocol_checking(self) -> None:
        """Test Validatable protocol with duck typing."""

        class MinimalValidatable:
            def validate(self) -> list[str]:
                return []

        obj = MinimalValidatable()
        assert isinstance(obj, Validatable)

    def test_validatable_protocol_with_errors(self) -> None:
        """Test Validatable with validation errors."""

        class ValidatableWithErrors:
            def validate(self) -> list[str]:
                return ["error1", "error2"]

        obj = ValidatableWithErrors()
        assert isinstance(obj, Validatable)

    def test_exportable_protocol_checking(self) -> None:
        """Test Exportable protocol with duck typing."""

        class MinimalExportable:
            def export(self, output_path: str, format: str) -> str:
                return output_path

        obj = MinimalExportable()
        assert isinstance(obj, Exportable)

    def test_pipeline_stage_protocol_checking(self) -> None:
        """Test PipelineStage protocol with duck typing."""

        class MinimalPipelineStage:
            name: str = "test_stage"

            def run(self, context: Any) -> Any:
                return context

        obj = MinimalPipelineStage()
        assert isinstance(obj, PipelineStage)

    def test_pipeline_stage_missing_name(self) -> None:
        """Test that missing name attribute fails protocol check."""

        class IncompletePipelineStage:
            def run(self, context: Any) -> Any:
                return context

        obj = IncompletePipelineStage()
        # Note: missing attribute in runtime_checkable protocol
        # The check is lenient on attributes
        assert not isinstance(obj, PipelineStage)

    def test_translation_rule_protocol_checking(self) -> None:
        """Test TranslationRule protocol with duck typing."""

        class MinimalTranslationRule:
            name: str = "test_rule"
            family: str = "structural"

            def applies_to(self, node: Any, graph: Any) -> bool:
                return True

            def apply(self, node: Any, graph: Any) -> Any:
                return {"rule": self.name, "node": node}

        obj = MinimalTranslationRule()
        assert isinstance(obj, TranslationRule)

    def test_translation_rule_missing_apply(self) -> None:
        """Test that missing apply method fails protocol check."""

        class IncompleteTranslationRule:
            name: str = "test_rule"
            family: str = "structural"

            def applies_to(self, node: Any, graph: Any) -> bool:
                return True

        obj = IncompleteTranslationRule()
        assert not isinstance(obj, TranslationRule)

    def test_graph_backend_protocol_checking(self) -> None:
        """Test GraphBackend protocol with duck typing."""

        class MinimalGraphBackend:
            def add_node(self, id: str, **attrs: Any) -> None:
                pass

            def add_edge(self, src: str, dst: str, **attrs: Any) -> None:
                pass

            def nodes(self) -> list[str]:
                return []

            def edges(self) -> list[tuple[str, str]]:
                return []

        obj = MinimalGraphBackend()
        assert isinstance(obj, GraphBackend)

    def test_graph_backend_missing_edges(self) -> None:
        """Test that missing edges method fails protocol check."""

        class IncompleteGraphBackend:
            def add_node(self, id: str, **attrs: Any) -> None:
                pass

            def add_edge(self, src: str, dst: str, **attrs: Any) -> None:
                pass

            def nodes(self) -> list[str]:
                return []

        obj = IncompleteGraphBackend()
        assert not isinstance(obj, GraphBackend)


@pytest.mark.unit
class TestProtocolInstantiation:
    """Test that protocols cannot be instantiated directly."""

    def test_translatable_not_instantiable(self) -> None:
        """Test that Translatable cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Translatable()  # type: ignore

    def test_analyzable_not_instantiable(self) -> None:
        """Test that Analyzable cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Analyzable()  # type: ignore

    def test_serializable_not_instantiable(self) -> None:
        """Test that Serializable cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Serializable()  # type: ignore

    def test_visualizable_not_instantiable(self) -> None:
        """Test that Visualizable cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Visualizable()  # type: ignore

    def test_validatable_not_instantiable(self) -> None:
        """Test that Validatable cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Validatable()  # type: ignore

    def test_exportable_not_instantiable(self) -> None:
        """Test that Exportable cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Exportable()  # type: ignore

    def test_pipeline_stage_not_instantiable(self) -> None:
        """Test that PipelineStage cannot be instantiated directly."""
        with pytest.raises(TypeError):
            PipelineStage()  # type: ignore

    def test_translation_rule_not_instantiable(self) -> None:
        """Test that TranslationRule cannot be instantiated directly."""
        with pytest.raises(TypeError):
            TranslationRule()  # type: ignore

    def test_graph_backend_not_instantiable(self) -> None:
        """Test that GraphBackend cannot be instantiated directly."""
        with pytest.raises(TypeError):
            GraphBackend()  # type: ignore


@pytest.mark.unit
class TestProtocolComplexScenarios:
    """Test protocols with more complex implementations."""

    def test_multi_protocol_implementation(self) -> None:
        """Test object implementing multiple protocols."""

        class MultiProtocol:
            def translate(self, graph: Any) -> Any:
                return {"translated": True}

            def analyze(self) -> dict[str, Any]:
                return {"analyzed": True}

            def to_dict(self) -> dict[str, Any]:
                return {"data": "value"}

            @classmethod
            def from_dict(cls, d: dict[str, Any]) -> "MultiProtocol":
                return cls()

        obj = MultiProtocol()
        assert isinstance(obj, Translatable)
        assert isinstance(obj, Analyzable)
        assert isinstance(obj, Serializable)

    def test_protocol_with_inheritance(self) -> None:
        """Test protocol checking with inherited methods."""

        class BaseTranslatable:
            def translate(self, graph: Any) -> Any:
                return {"result": "base"}

        class DerivedTranslatable(BaseTranslatable):
            pass

        obj = DerivedTranslatable()
        assert isinstance(obj, Translatable)

    def test_protocol_with_optional_attributes(self) -> None:
        """Test protocol with optional attributes."""

        class PipelineWithOptional:
            name: str = "optional_stage"
            optional_attr: str = "optional"

            def run(self, context: Any) -> Any:
                return context

        obj = PipelineWithOptional()
        assert isinstance(obj, PipelineStage)

    def test_callable_protocol_methods(self) -> None:
        """Test that protocol methods are properly callable."""

        class CallableValidatable:
            def validate(self) -> list[str]:
                return ["issue1", "issue2"]

        obj = CallableValidatable()
        assert isinstance(obj, Validatable)

        # Call the validate method
        result = obj.validate()
        assert result == ["issue1", "issue2"]
        assert len(result) == 2

    def test_protocol_with_return_type_variance(self) -> None:
        """Test protocol with different return types."""

        class AnalyzableVariant:
            def analyze(self) -> dict[str, Any]:
                return {
                    "metrics": {"complexity": 10, "coverage": 0.8},
                    "timestamp": "2026-04-13",
                }

        obj = AnalyzableVariant()
        assert isinstance(obj, Analyzable)
        result = obj.analyze()
        assert "metrics" in result

    def test_serializable_roundtrip(self) -> None:
        """Test Serializable protocol with data roundtrip."""

        class SerializableData:
            def __init__(self, value: int = 42) -> None:
                self.value = value

            def to_dict(self) -> dict[str, Any]:
                return {"value": self.value}

            @classmethod
            def from_dict(cls, d: dict[str, Any]) -> "SerializableData":
                return cls(value=d.get("value", 42))

        original = SerializableData(value=100)
        assert isinstance(original, Serializable)

        serialized = original.to_dict()
        assert serialized["value"] == 100

        deserialized = SerializableData.from_dict(serialized)
        assert deserialized.value == 100
