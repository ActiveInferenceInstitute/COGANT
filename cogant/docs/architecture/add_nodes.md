## Add nodes
class_node = builder.add_node(
    kind=NodeKind.CLASS,
    name="DataProcessor",
    qualified_name="app.core.DataProcessor",
    path="src/app/core.py",
    language="python"
)

func_node = builder.add_node(
    kind=NodeKind.FUNCTION,
    name="process_data",
    qualified_name="app.processing.process_data",
    path="src/app/processing.py",
    language="python"
)
