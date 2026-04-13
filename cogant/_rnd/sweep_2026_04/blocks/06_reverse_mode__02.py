from cogant.reverse import build_package_plan, PackagePlan

plan: PackagePlan = build_package_plan(
    gnn=gnn,
    package_name="calculator_synth",
    output_root=Path("output/reverse/"),
)

print(plan.directory_layout())
# calculator_synth/
#   __init__.py
#   hidden_state.py    # class Display, Accumulator, HistoryLen
#   observations.py    # def get_display, get_history, assert_display
#   actions.py         # def execute_operation
#   model.py           # A, B, C, D as module-level constants
