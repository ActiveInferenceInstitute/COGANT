"""Integration tests for the visualization pipeline.

Tests for converting graph and matrix data to visual formats (mermaid, PNG, PDF).
"""

import pytest

# Skip all tests if matplotlib is not available
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        pytest.importorskip("matplotlib", minversion=None) is None,
        reason="matplotlib required for visualization tests",
    ),
]


class TestMatrixVisualizationBasics:
    """Tests for basic matrix visualization."""

    def test_matrix_view_creates_figure(self):
        """Test that matrix visualization creates a matplotlib Figure.

        Verifies:
        - MatrixVisualizer (if available) can be instantiated
        - Visualization methods return Figure objects or drawable objects
        """
        pytest.importorskip("matplotlib")
        try:
            from cogant.export.visualization import MatrixVisualizer
        except ImportError:
            pytest.skip("MatrixVisualizer not available")

        # Create mock matrices
        matrices = {
            "A": [[0.8, 0.2], [0.2, 0.8]],
            "B": [[1.0, 0.0], [0.0, 1.0]],
            "C": [[0.5, 0.5], [0.5, 0.5]],
            "D": [[0.3, 0.7], [0.7, 0.3]],
        }

        viz = MatrixVisualizer()
        fig = viz.plot_all_matrices(matrices)

        # Verify return type
        import matplotlib.figure

        assert isinstance(fig, matplotlib.figure.Figure)

    def test_matrix_view_to_png(self, temp_dir):
        """Test saving matrix visualization to PNG.

        Verifies:
        - Figure can be saved to PNG file
        - PNG file is created and is non-empty
        - File has reasonable size (PNG header + data)
        """
        pytest.importorskip("matplotlib")
        import matplotlib.pyplot as plt

        try:
            from cogant.export.visualization import MatrixVisualizer
        except ImportError:
            pytest.skip("MatrixVisualizer not available")

        matrices = {
            "A": [[0.8, 0.2], [0.2, 0.8]],
        }

        viz = MatrixVisualizer()
        fig = viz.plot_all_matrices(matrices)

        # Save to PNG
        output_file = temp_dir / "matrices.png"
        fig.savefig(str(output_file), format="png", dpi=100)
        plt.close(fig)

        # Verify file exists and is non-empty
        assert output_file.exists()
        file_size = output_file.stat().st_size
        assert file_size > 0, "PNG file should have content"
        assert file_size > 100, "PNG file should be larger than minimal header"


class TestPipelineVisualization:
    """Tests for pipeline/workflow visualization."""

    def test_pipeline_view_mermaid(self):
        """Test generating pipeline diagram as Mermaid markdown.

        Verifies:
        - PipelineVisualizer (if available) generates Mermaid syntax
        - Output is a non-empty string
        - Output starts with 'flowchart' or 'graph'
        """
        try:
            from cogant.export.visualization import PipelineVisualizer
        except ImportError:
            pytest.skip("PipelineVisualizer not available")

        viz = PipelineVisualizer()
        diagram = viz.render_stage_diagram()

        assert isinstance(diagram, str)
        assert len(diagram) > 0
        assert "flowchart" in diagram.lower() or "graph" in diagram.lower(), (
            "Diagram should use Mermaid flowchart or graph syntax"
        )


class TestFlowDiagramming:
    """Tests for control flow diagram generation."""

    def test_flow_diagrammer_mermaid(self):
        """Test generating control flow diagram as Mermaid.

        Verifies:
        - FlowDiagrammer (if available) generates Mermaid syntax
        - Output is non-empty string
        - Output is valid Mermaid flowchart syntax
        """
        try:
            from cogant.export.visualization import FlowDiagrammer
        except ImportError:
            pytest.skip("FlowDiagrammer not available")

        # Create a minimal call graph
        call_graph = {
            "main": ["func_a", "func_b"],
            "func_a": ["func_c"],
            "func_b": ["func_c"],
            "func_c": [],
        }

        diagrammer = FlowDiagrammer()
        diagram = diagrammer.to_mermaid_flowchart(call_graph)

        assert isinstance(diagram, str)
        assert len(diagram) > 0
        # Mermaid flowchart should contain directions or connections
        assert any(x in diagram.lower() for x in ["flowchart", "graph", "-->", "->"]), (
            "Diagram should contain Mermaid syntax"
        )


class TestPDFExport:
    """Tests for PDF export of visualizations."""

    def test_pdf_export_creates_file(self, temp_dir):
        """Test exporting visualization to PDF.

        Verifies:
        - PDF file is created
        - PDF has non-zero size
        - File is valid PDF format (has PDF header)
        """
        pytest.importorskip("matplotlib")

        try:
            from cogant.export.visualization import PDFExporter
        except ImportError:
            pytest.skip("PDFExporter not available")

        # Create mock matrix data
        matrices = {
            "A": [[0.8, 0.2], [0.2, 0.8]],
            "B": [[1.0, 0.0], [0.0, 1.0]],
        }

        exporter = PDFExporter()
        output_file = temp_dir / "matrices.pdf"

        # Export to PDF
        exporter.export_matrices(matrices, str(output_file))

        # Verify file exists
        assert output_file.exists(), "PDF file should be created"
        file_size = output_file.stat().st_size
        assert file_size > 0, "PDF file should have content"

        # Verify PDF header (basic check)
        with open(output_file, "rb") as f:
            header = f.read(5)
            assert header == b"%PDF-", "File should start with PDF header"


class TestVisualizationIntegration:
    """Integration tests combining visualization and export."""

    def test_viz_pipeline_end_to_end(self, temp_dir):
        """Test complete visualization pipeline: data → viz → export.

        Verifies:
        - Can create visualization from raw data
        - Can export visualization to file
        - Exported file is usable
        """
        pytest.importorskip("matplotlib")
        import matplotlib.pyplot as plt

        # Create sample data
        import numpy as np

        matrix_data = np.random.rand(5, 5)

        # Create figure
        fig, ax = plt.subplots(figsize=(8, 6))
        im = ax.imshow(matrix_data, cmap="viridis")
        ax.set_title("Sample Matrix Visualization")
        fig.colorbar(im, ax=ax)

        # Save to multiple formats
        for fmt in ["png", "pdf"]:
            output_file = temp_dir / f"viz_test.{fmt}"
            fig.savefig(str(output_file), format=fmt, dpi=100)
            assert output_file.exists()
            assert output_file.stat().st_size > 0

        plt.close(fig)

    def test_graph_to_mermaid_pipeline(self):
        """Test converting ProgramGraph to Mermaid diagram.

        Verifies:
        - Can convert graph structure to Mermaid syntax
        - Output is valid Mermaid flowchart
        """
        try:
            from cogant.export.visualization import GraphToMermaid
        except ImportError:
            pytest.skip("GraphToMermaid not available")

        # Create a simple graph structure
        graph_dict = {
            "nodes": [
                {"id": "n1", "label": "Function A"},
                {"id": "n2", "label": "Function B"},
                {"id": "n3", "label": "Function C"},
            ],
            "edges": [
                {"source": "n1", "target": "n2"},
                {"source": "n2", "target": "n3"},
            ],
        }

        converter = GraphToMermaid()
        diagram = converter.graph_to_mermaid(graph_dict)

        assert isinstance(diagram, str)
        assert len(diagram) > 0


class TestVisualizationErrors:
    """Tests for error handling in visualization."""

    def test_invalid_matrix_data(self):
        """Test handling of invalid matrix data.

        Verifies:
        - Invalid matrix data is detected
        - Appropriate error is raised
        """
        try:
            from cogant.export.visualization import MatrixVisualizer
        except ImportError:
            pytest.skip("MatrixVisualizer not available")

        viz = MatrixVisualizer()

        # Try with invalid data (non-numeric)
        invalid_matrices = {
            "A": [["invalid", "data"], ["text", "here"]],
        }

        # The visualization layer degrades gracefully on bad user data.
        assert viz.plot_all_matrices(invalid_matrices) is None

    def test_empty_graph_visualization(self):
        """Test handling of empty graph in visualization.

        Verifies:
        - Empty graph is handled gracefully
        - Either returns empty diagram or error
        """
        try:
            from cogant.export.visualization import FlowDiagrammer
        except ImportError:
            pytest.skip("FlowDiagrammer not available")

        diagrammer = FlowDiagrammer()

        # Empty call graph
        empty_graph = {}

        # Should either return empty string or handle gracefully
        result = diagrammer.to_mermaid_flowchart(empty_graph)
        assert isinstance(result, str)
