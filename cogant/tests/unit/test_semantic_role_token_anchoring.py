"""Regression tests pinning token-anchored semantic-role keyword matching.

These tests bind the behaviour introduced in ``semantic.py`` when role
keyword matching was changed from raw substring containment
(``kw in node.name.lower()``) to whole-token anchoring
(:func:`_matched_keywords`), plus the structural rule that a *write-bearing*
function is an ACTION even when its name lexically suggests a read.

Motivation. The manuscript's role-discrimination / role-preservation claims
rest on the rule engine assigning *distinct* roles rather than collapsing
every method onto one keyword hit. The previous substring logic produced
silent mislabels that no committed test caught:

  * ``set_target``  matched OBSERVATION keyword ``"get"``  (from ``tar*get*``)
  * ``dataset`` / ``reset``  matched ACTION keyword ``"set"``
  * ``read_sensor``  (which *writes* ``self.current_temp``) was pulled toward
    OBSERVATION by its name despite mutating state.

The ``test_negative_control_*`` case below only admits identifiers where the
offending keyword is a genuine raw substring, so the suite cannot drift into
asserting vacuous non-matches (an early draft mistakenly listed
``description`` / ``"describe"``, which is not actually a substring pair).

The tutorial test only exercises the *positive* ``get_value`` path, so a
revert to substring matching would pass the existing suite. This module is
the negative-case guard. It also asserts the genuine positives still fire,
so the anchoring fix cannot be "passed" by simply disabling keyword matching.
"""

from cogant.graph.queries import GraphQuery
from cogant.schemas.core import Edge, EdgeKind, Node, NodeKind
from cogant.schemas.graph import GraphMetadata, ProgramGraph
from cogant.translate.rules.keywords import ACTION_KEYWORDS, OBSERVATION_KEYWORDS
from cogant.translate.rules.semantic import (
    ActionRule,
    ContextRule,
    ObservationRule,
    PolicyRule,
    PreferenceRule,
    _matched_keywords,
)

# --- False-positive identifiers and the keyword that used to mis-match them. ---
# (identifier, keyword_list, offending_substring_keyword)
_SUBSTRING_FALSE_POSITIVES = [
    ("set_target", OBSERVATION_KEYWORDS, "get"),
    ("dataset", ACTION_KEYWORDS, "set"),
    ("reset", ACTION_KEYWORDS, "set"),
]


def test_negative_control_old_substring_logic_would_have_mismatched() -> None:
    """Document that each case is a *real* regression the anchoring fix guards.

    Under the previous ``kw in name.lower()`` logic every pair below matched.
    If this control ever stops holding, the chosen fixtures are no longer
    exercising the substring hazard and the asserts in the next test would
    pass vacuously.
    """
    for name, _keywords, offending in _SUBSTRING_FALSE_POSITIVES:
        assert offending in name.lower(), (
            f"{offending!r} is expected to be a raw substring of {name!r}; "
            "this fixture no longer demonstrates the substring hazard"
        )


def test_token_anchoring_rejects_substring_false_positives() -> None:
    """The anchored matcher must NOT report the offending substring keyword."""
    for name, keywords, offending in _SUBSTRING_FALSE_POSITIVES:
        matched = _matched_keywords(name, keywords)
        assert offending not in matched, (
            f"{name!r} should not match keyword {offending!r} under token "
            f"anchoring; got {matched!r}"
        )


def test_token_anchoring_preserves_true_positives() -> None:
    """Genuine token / prefix matches must still fire (no over-correction)."""
    # Whole-token match.
    assert "get" in _matched_keywords("get_value", OBSERVATION_KEYWORDS)
    # camelCase boundary split -> ``read`` token.
    assert "read" in _matched_keywords("readSensor", OBSERVATION_KEYWORDS)
    # Bare action verb as a whole token.
    assert "set" in _matched_keywords("set", ACTION_KEYWORDS)
    # Prefix-style ("get_") keyword anchored to the leading token.
    assert "get_" in _matched_keywords("get_temperature", OBSERVATION_KEYWORDS)


def _method_writing_state(name: str) -> ProgramGraph:
    """A class method that WRITES an attribute and performs no reads."""
    graph = ProgramGraph(metadata=GraphMetadata(repo_uri="test://anchoring"))
    cls = Node(id="n:Ctl", kind=NodeKind.CLASS, name="Ctl", qualified_name="Ctl")
    method = Node(
        id=f"n:{name}",
        kind=NodeKind.METHOD,
        name=name,
        qualified_name=f"Ctl.{name}",
    )
    attr = Node(
        id="n:state",
        kind=NodeKind.VARIABLE,
        name="state",
        qualified_name="Ctl.state",
    )
    for node in (cls, method, attr):
        graph.add_node(node)
    graph.add_edge(
        Edge(
            id=f"e:{name}->state",
            source_id=method.id,
            target_id=attr.id,
            kind=EdgeKind.WRITES,
        )
    )
    return graph


def test_write_bearing_read_named_method_is_not_observation() -> None:
    """``read_sensor`` that writes state must not be claimed by ObservationRule.

    The structural mutation fact outranks the lexical read hint: a function
    that writes is an ACTION even when its name starts with ``read``.
    """
    graph = _method_writing_state("read_sensor")
    matches = ObservationRule().matches(graph, GraphQuery(graph))
    assert not any(m["node_id"] == "n:read_sensor" for m in matches), (
        "read_sensor writes state and must not be matched by ObservationRule"
    )


def test_setter_is_not_observation() -> None:
    """``set_target`` (writes, contains substring 'get') is not an observation."""
    graph = _method_writing_state("set_target")
    matches = ObservationRule().matches(graph, GraphQuery(graph))
    assert not any(m["node_id"] == "n:set_target" for m in matches)


# --- Corpus-wide invariants: guard the WHOLE keyword set, not 3 fixtures. -----
# These protect against future keyword additions: any new bare keyword that
# could be a mid-token substring trap is automatically covered.

_ALL_KEYWORD_LISTS = [
    ("OBSERVATION_KEYWORDS", OBSERVATION_KEYWORDS),
    ("ACTION_KEYWORDS", ACTION_KEYWORDS),
]


def _bare_keywords(keywords: list[str]) -> list[str]:
    """Bare (non-prefix) keywords: those that match a whole token, not a stem."""
    return [kw for kw in keywords if not kw.endswith("_")]


def test_bare_keywords_are_lowercase_and_unique() -> None:
    """Keyword corpus hygiene: lowercase, stripped, no duplicates.

    Token anchoring lowercases identifiers, so an upper-case or whitespace-
    padded keyword would silently never match. A duplicate inflates the
    matched-keyword evidence list. Both are latent corpus bugs.
    """
    for label, keywords in _ALL_KEYWORD_LISTS:
        assert keywords == [k.strip() for k in keywords], f"{label} has padding"
        assert all(k == k.lower() for k in keywords), f"{label} has non-lowercase"
        assert len(keywords) == len(set(keywords)), f"{label} has duplicates"


def test_no_bare_keyword_matches_as_mid_token_substring() -> None:
    """Every bare keyword embedded mid-token must NOT match (anchoring holds).

    For keyword ``kw`` the identifier ``x{kw}y`` is a single token ``x{kw}y``
    that is not equal to ``kw``; raw substring containment WOULD have matched
    it, token anchoring must not. This is the corpus-wide generalisation of
    the ``set_target``/``dataset`` fixtures and covers keywords added later.
    """
    for label, keywords in _ALL_KEYWORD_LISTS:
        for kw in _bare_keywords(keywords):
            trap = f"x{kw}y"  # single lowercase token, kw is a strict substring
            assert kw in trap, "fixture sanity: kw must be a substring of trap"
            matched = _matched_keywords(trap, keywords)
            assert kw not in matched, (
                f"{label}: {kw!r} must not match mid-token in {trap!r}; "
                f"got {matched!r}"
            )


def test_every_bare_keyword_matches_as_a_whole_token() -> None:
    """Each bare keyword must still fire when it IS a standalone token.

    Pairs with the substring-rejection test so the anchoring fix cannot be
    "passed" by a matcher that simply never matches anything.
    """
    for label, keywords in _ALL_KEYWORD_LISTS:
        for kw in _bare_keywords(keywords):
            # ``do_<kw>`` tokenises to ["do", kw]; kw is a whole token.
            assert kw in _matched_keywords(f"do_{kw}", keywords), (
                f"{label}: bare keyword {kw!r} should match as a whole token"
            )


def test_property_random_padding_never_creates_mid_token_match() -> None:
    """Property: lowercase-letter padding around a keyword never mid-token matches.

    Uses Hypothesis when available (dev dependency); skipped otherwise. This
    fuzzes the anchoring boundary beyond the single ``x{kw}y`` witness.
    """
    import pytest

    hypothesis = pytest.importorskip("hypothesis")
    from hypothesis import strategies as st

    pad = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=6)
    all_bare = [
        (kws, kw)
        for _label, kws in _ALL_KEYWORD_LISTS
        for kw in _bare_keywords(kws)
    ]

    @hypothesis.given(prefix=pad, suffix=pad, idx=st.integers(min_value=0))
    def _check(prefix: str, suffix: str, idx: int) -> None:
        keywords, kw = all_bare[idx % len(all_bare)]
        trap = f"{prefix}{kw}{suffix}"  # one lowercase token, kw strictly inside
        assert kw not in _matched_keywords(trap, keywords)

    _check()


# --- Rule-level binding for the OTHER three rules anchored in the same fix. ---
# Policy/Preference/Context rules kept their keyword lists inline (not exported),
# so these construct a one-node graph and assert via the public ``matches`` API.
# Each pair is a substring trap (must NOT match) + a whole-token name (must match)
# that the previous ``kw in name.lower()`` logic would have conflated.


def _function_named(name: str) -> ProgramGraph:
    """A ProgramGraph with a single edge-free FUNCTION node."""
    graph = ProgramGraph(metadata=GraphMetadata(repo_uri="test://rulelevel"))
    graph.add_node(
        Node(
            id=f"n:{name}",
            kind=NodeKind.FUNCTION,
            name=name,
            qualified_name=name,
        )
    )
    return graph


def _rule_matches_name(rule: object, name: str) -> bool:
    graph = _function_named(name)
    matches = rule.matches(graph, GraphQuery(graph))  # type: ignore[attr-defined]
    return any(m["node_id"] == f"n:{name}" for m in matches)


def test_policy_rule_rejects_substring_trap_keeps_whole_token() -> None:
    """``xrouter`` must not match POLICY via 'route'; ``route_request`` must."""
    rule = PolicyRule()
    assert not _rule_matches_name(rule, "xrouter")  # 'route'/'router' substring
    assert _rule_matches_name(rule, "route_request")  # 'route' whole token


def test_preference_rule_rejects_substring_trap_keeps_whole_token() -> None:
    """``latest_value`` must not match PREFERENCE via 'test_'; ``validate_input`` must."""
    rule = PreferenceRule()
    assert not _rule_matches_name(rule, "latest_value")  # 'test_' lexical trap
    assert _rule_matches_name(rule, "validate_input")  # 'validate' whole token


def test_context_rule_rejects_substring_trap_keeps_whole_token() -> None:
    """``configure`` must not match CONTEXT via 'config'; ``load_config`` must."""
    rule = ContextRule()
    assert not _rule_matches_name(rule, "configure")  # 'config' substring of token
    assert _rule_matches_name(rule, "load_config")  # 'config' whole token


# --- The recall side of the precision/recall trade, pinned as a DECISION. -----
# Whole-token anchoring deliberately does NOT morphologically normalise: a
# prefixed or inflected form of a keyword (``reroute``, ``routing``,
# ``policies``) does not match the bare keyword. This is intentional —
# advisor-reviewed (2026-05-29). Adding prefix-stripping would recover
# ``reroute→route`` but simultaneously REOPEN the false positives the anchoring
# fix exists to kill (``reset→set``, ``managerial→manager``). The recall loss
# is partially compensated by prefix-form keywords (``route_``, ``get_``) and by
# the structural edge rules (READS/WRITES). This trade-off is disclosed in
# manuscript/08_05_threats_to_validity.md (lexical construct validity). The test
# pins the decision so any future move to morphological normalisation is a
# deliberate, red-test-visible change rather than a silent drift.

# (identifier, rule class, offending keyword). Each ``offending`` keyword is a
# REAL registered keyword for that rule AND a raw substring of ``identifier``, so
# the old substring logic matched it; whole-token anchoring does not. Asserted
# against the ACTUAL rule via ``matches()`` — NOT a stand-in keyword list — so a
# name that is in fact a whole-token keyword of the rule (e.g. ``dispatcher``,
# which IS a PolicyRule keyword) can never be miscategorised here as a "missed"
# match. Verified on the live rules 2026-05-29 (Forge cross-vendor audit caught a
# fictional-vocabulary version of this test that masked a false manuscript claim).
_MORPHOLOGICAL_NONMATCHES = [
    ("reroute", PolicyRule, "route"),  # 're' prefix; 'route' is a PolicyRule kw
    ("routes", PolicyRule, "route"),  # plural
    ("download", ActionRule, "load"),  # 'load' is an ACTION keyword
    ("environment", ContextRule, "env"),  # 'env' is a CONTEXT keyword
    ("metrics", PreferenceRule, "metric"),  # 'metric' is a PREFERENCE keyword
]


def test_morphological_variants_are_documented_nonmatches() -> None:
    """Inflected keyword forms do NOT match their REAL rule (precision choice)."""
    for name, rule_cls, offending in _MORPHOLOGICAL_NONMATCHES:
        assert offending in name, "fixture sanity: offending kw must be a substring"
        assert not _rule_matches_name(rule_cls(), name), (
            f"{name!r} matching its rule via {offending!r} would mean morphological "
            "normalisation was (re)introduced; that reopens reset->set. Update "
            "08_05 + this decision deliberately if so."
        )
    # Compensating mechanism: a real prefix/whole-token OBSERVATION keyword fires.
    assert _rule_matches_name(ObservationRule(), "get_value")  # 'get' leading token
