# Process

Identifies workflow stages from call graphs and control flow. Extracts predecessors/successors, triggers, side effects, and compiles complete process models with connections, patterns, and timelines.

## API

ProcessExtractor analyzes the program graph to identify workflow stages and builds a ProcessModel. Initialize with program_graph and schema_name, then call extract() to get a ProcessModel containing stages, connections, entry/exit stage IDs, and metadata.

Stage represents a workflow stage with associated nodes, entry/exit points, side effects, expected duration, confidence, and pattern type (sequential, fan_out, fan_in, loop_member). ProcessConnection models the relationship between two stages with trigger, condition, and success rate.

TimelineBuilder constructs stage sequences for Gantt visualization. It produces a Timeline with ordered GanttStage objects, total duration, critical path, and parallel groups for visualization and analysis.

PolicyExtractor identifies decision points, retry logic, branching conditions, and circuit breaker patterns from graph structure. Extracts RetryPolicy (max attempts, backoff strategy), BranchingPolicy (decision points and branches), and CircuitBreakerPolicy (failure/success thresholds).

## Usage

```python
from cogant.process import ProcessExtractor, TimelineBuilder
from cogant.schemas.graph import ProgramGraph

# Create program graph
graph = ProgramGraph(...)

# Extract process model
extractor = ProcessExtractor(graph, schema_name="my_schema")
process_model = extractor.extract()

# Build timeline for visualization
timeline_builder = TimelineBuilder(process_model)
timeline = timeline_builder.build()

# Access components
print(f"Stages: {len(process_model.stages)}")
print(f"Entry: {process_model.entry_stage_id}")
print(f"Timeline duration: {timeline.total_duration}s")
```
