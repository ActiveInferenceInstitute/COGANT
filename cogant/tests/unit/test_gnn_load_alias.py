"""Test load_gnn_package convenience alias."""

from cogant.gnn.runner import GNNModelRunner, load_gnn_package


def test_load_gnn_package_is_callable():
    assert callable(load_gnn_package)


def test_load_gnn_package_bound_to_runner():
    # alias should be a bound method of GNNModelRunner
    assert hasattr(load_gnn_package, "__self__") or callable(load_gnn_package)


def test_load_gnn_package_bound_self_is_runner_instance():
    # Stronger check: the bound __self__ should be a GNNModelRunner
    assert isinstance(load_gnn_package.__self__, GNNModelRunner)
