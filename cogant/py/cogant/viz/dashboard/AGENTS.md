# Agents — py/cogant/viz/dashboard

## Owner

Visualization and User Interface Lead

## Responsibilities

Interactive HTML dashboard generation: `DashboardGenerator` plus embedded `DASHBOARD_CSS` and `DASHBOARD_JS` constants. Large layout lives in `generator.py`; assets module holds static bundles.

## Coordination

Consumes bundle/report types from export and validate; output is self-contained HTML for browsers.

## Files

- `generator.py` — `DashboardGenerator`.
- `assets.py` — `DASHBOARD_CSS`, `DASHBOARD_JS`.
- `__init__.py` — re-exports.
