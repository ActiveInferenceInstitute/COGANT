from pathlib import Path
from cogant import Session

def test_my_rule_fires_on_fixture():
    session = Session.from_target(Path("tests/fixtures/my_rule_target"))
    session.extract_static()
    session.build_graph()
    session.translate_to_gnn()
    mappings = session.semantic_mappings()
    assert any(m.rule_name == "MyRule" for m in mappings)
