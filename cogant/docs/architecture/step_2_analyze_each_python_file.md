## Step 2: Analyze each Python file
symbol_extractor = SymbolExtractor(snapshot.root_path)
import_analyzer = ImportAnalyzer(snapshot.root_path)
call_builder = CallGraphBuilder(snapshot.root_path)
type_inferencer = TypeInferencer(snapshot.root_path)
dataflow_analyzer = DataFlowAnalyzer(snapshot.root_path)

all_symbols = []
all_imports = []
all_calls = []
all_types = []
all_flows = []

for file_info in snapshot.files:
    if file_info.language != "python":
        continue

    # Extract symbols
    symbols = symbol_extractor.extract_from_file(file_info.path)
    all_symbols.extend(symbols.symbols)

    # Analyze imports
    imports = import_analyzer.analyze_file(file_info.path)
    all_imports.extend(imports)

    # Extract calls
    calls = call_builder.extract_calls_from_file(file_info.path)
    all_calls.extend(calls)

    # Infer types
    types = type_inferencer.infer_types_from_file(file_info.path)
    all_types.extend(types)

    # Analyze data flow
    flows = dataflow_analyzer.analyze_file(file_info.path)
    all_flows.extend(flows)
