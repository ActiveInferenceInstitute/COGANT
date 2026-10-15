import math
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from cogant.simulate.runner import ModelRunner
from cogant.simulate.visualization import SimulationVisualizer
from cogant.statespace.compiler import Action, ObservationModality, StateSpaceModel
from cogant.statespace.temporal import TimeRegime
from cogant.statespace.variables import StateVariable, StateVariableType


def _runner() -> tuple[ModelRunner, StateSpaceModel]:
    model = StateSpaceModel(
        id="observed",
        schema_name="observed",
        time_regime=TimeRegime.SYNCHRONOUS,
        variables={
            s: StateVariable(id=s, name=s, node_id=s, var_type=StateVariableType.CATEGORICAL)
            for s in ("s0", "s1")
        },
        observations={
            o: ObservationModality(id=o, name=o, source_node_id=o, modality_type="categorical")
            for o in ("o0", "o1")
        },
        actions={"stay": Action(id="stay", name="stay", controller_id="stay")},
        transitions={},
        likelihoods={},
        preferences={},
    )
    return ModelRunner(
        model=model,
        A=[[1.0, 0.0], [0.0, 1.0]],
        B=[[[1.0], [0.0]], [[0.0], [1.0]]],
        C=[0.0, 0.0],
        D=[0.5, 0.5],
    ), model


def test_one_observation_report_and_plot_exclude_initial_prior(tmp_path: Path) -> None:
    runner, model = _runner()
    trace = runner.run_active_inference(model, steps=1)
    expected = math.log(2.0)
    assert trace[1]["free_energy"] == pytest.approx(expected)
    report = runner.generate_report(trace)
    (tmp_path / "one-observation.md").write_text(report)
    assert "Total steps: 1\n" in report
    for statistic in ("Mean", "Min", "Max"):
        assert f"{statistic} VFE: {expected:.4f}" in report
    assert trace[0]["phase"] == "initial"
    assert trace[0]["free_energy"] is None
    assert "### Initial prior" in report
    visualizer = SimulationVisualizer()
    svg = visualizer.plot_free_energy_trajectory(trace)
    (tmp_path / "one-observation.svg").write_text(svg)
    points = ET.fromstring(svg).findall("{http://www.w3.org/2000/svg}circle")
    assert len(points) == 1
    assert points[0].attrib["data-step"] == "1"
    assert float(points[0].attrib["data-free-energy"]) == pytest.approx(expected)
    html = visualizer.generate_html_report(trace, model)
    (tmp_path / "one-observation.html").write_text(html)
    assert "<div class='stat-value'>1</div><div class='stat-label'>Steps" in html
    assert (
        f"<div class='stat-value'>{expected:.3f}</div><div class='stat-label'>Mean Free Energy"
        in html
    )


def test_zero_observations_retain_prior_without_energy_statistics(tmp_path: Path) -> None:
    runner, model = _runner()
    trace = runner.run_active_inference(model, steps=0)
    assert len(trace) == 1
    assert trace[0]["beliefs"] == {"s0": 0.5, "s1": 0.5}
    report = runner.generate_report(trace)
    (tmp_path / "zero-observations.md").write_text(report)
    assert "Total steps: 0\n" in report
    assert "Mean VFE:" not in report
    assert "No observed inference updates" in report
    visualizer = SimulationVisualizer()
    svg = visualizer.plot_free_energy_trajectory(trace)
    (tmp_path / "zero-observations.svg").write_text(svg)
    assert "No free energy data" in svg
    assert not ET.fromstring(svg).findall("{http://www.w3.org/2000/svg}circle")
    html = visualizer.generate_html_report(trace, model)
    (tmp_path / "zero-observations.html").write_text(html)
    assert "<div class='stat-value'>0</div><div class='stat-label'>Steps" in html
    assert "stat-label'>Mean Free Energy" not in html


@pytest.mark.parametrize("value", [None, math.nan, math.inf, -math.inf, "bad", True])
def test_executed_observation_rejects_invalid_energy(value: float | str | bool | None) -> None:
    runner, model = _runner()
    trace = [{"step": 1, "phase": "observation", "free_energy": value}]
    visualizer = SimulationVisualizer()
    with pytest.raises(ValueError, match="finite numeric free_energy"):
        runner.generate_report(trace)
    with pytest.raises(ValueError, match="finite numeric free_energy"):
        visualizer.plot_free_energy_trajectory(trace)
    with pytest.raises(ValueError, match="finite numeric free_energy"):
        visualizer.generate_html_report(trace, model)


def test_executed_observation_rejects_missing_energy() -> None:
    runner, model = _runner()
    trace = [{"step": 1, "phase": "observation"}]
    visualizer = SimulationVisualizer()
    with pytest.raises(ValueError, match="finite numeric free_energy"):
        runner.generate_report(trace)
    with pytest.raises(ValueError, match="finite numeric free_energy"):
        visualizer.plot_free_energy_trajectory(trace)
    with pytest.raises(ValueError, match="finite numeric free_energy"):
        visualizer.generate_html_report(trace, model)
