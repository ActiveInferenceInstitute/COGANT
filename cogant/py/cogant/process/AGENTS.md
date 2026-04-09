# Agents — py/cogant/process

## Owner
Process Architecture Lead

## Responsibilities
Identify workflow stages from call graphs and control flow. Extract process connections, patterns, and entry/exit points. Build process models and timelines for analysis. Extract policies including retry, branching, and circuit breaker patterns.

## Key Responsibilities
- Run ProcessExtractor to identify stages from connected components and modules
- Detect workflow patterns (sequential, fan_out, fan_in, loop_member)
- Identify entry and exit stages through topological analysis
- Extract policies (RetryPolicy, BranchingPolicy, CircuitBreakerPolicy)
- Build Timeline with GanttStage objects for visualization

## How to Extend
Add new pattern types by extending _detect_patterns() in ProcessExtractor. Create new policy classes inheriting from policy base structures. Extend TimelineBuilder to support new scheduling algorithms (critical path, resource-aware, etc.).

## Coordination
- Consumes: ProgramGraph from graph/
- Produces: ProcessModel consumed by export/, validate/, viz/
- Works with: statespace/ for cross-model consistency, viz/ for timeline visualization
