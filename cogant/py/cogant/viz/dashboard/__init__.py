"""COGANT dashboard package.

The dashboard generator lives in :mod:`cogant.viz.dashboard.generator`
and its large CSS/JS constants live in :mod:`cogant.viz.dashboard.assets`.
The umbrella package re-exports :class:`DashboardGenerator` so
``from cogant.viz.dashboard import DashboardGenerator`` — and the
older ``from cogant.viz import dashboard; dashboard.DashboardGenerator``
form — both keep working.
"""

from cogant.viz.dashboard.assets import DASHBOARD_CSS, DASHBOARD_JS
from cogant.viz.dashboard.generator import DashboardGenerator

__all__ = ["DashboardGenerator", "DASHBOARD_CSS", "DASHBOARD_JS"]
