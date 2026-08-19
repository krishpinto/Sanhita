import pytest

from app.engine.expr import evaluate, extract_var_paths, is_determinable


def test_literal_passthrough():
    assert evaluate("hello", {}) == "hello"
    assert evaluate(True, {}) is True
    assert evaluate(["a", "b"], {}) == ["a", "b"]


def test_var_lookup_dotted_path():
    ns = {"core": {"ecg": {"rhythm": "af"}}}
    assert evaluate({"var": "core.ecg.rhythm"}, ns) == "af"


def test_var_missing_raises():
    with pytest.raises(KeyError):
        evaluate({"var": "core.missing"}, {})


def test_equality_and_membership():
    ns = {"a": "x", "b": ["x", "y"]}
    assert evaluate({"==": [{"var": "a"}, "x"]}, ns) is True
    assert evaluate({"!=": [{"var": "a"}, "y"]}, ns) is True
    assert evaluate({"in": [{"var": "a"}, {"var": "b"}]}, ns) is True
    assert evaluate({"in": [{"var": "a"}, ["p", "q"]]}, ns) is False


def test_comparators():
    ns = {"hr": 120}
    assert evaluate({">": [{"var": "hr"}, 110]}, ns) is True
    assert evaluate({"<": [{"var": "hr"}, 50]}, ns) is False
    assert evaluate({">=": [{"var": "hr"}, 120]}, ns) is True
    assert evaluate({"<=": [{"var": "hr"}, 119]}, ns) is False


def test_and_or_not():
    ns = {"a": True, "b": False}
    assert evaluate({"and": [{"var": "a"}, {"not": [{"var": "b"}]}]}, ns) is True
    assert evaluate({"or": [{"var": "b"}, {"var": "a"}]}, ns) is True
    assert evaluate({"and": [{"var": "a"}, {"var": "b"}]}, ns) is False


def test_angina_gate0_fire_when_reproduces_source_rule():
    fire_when = {
        "or": [
            {"==": [{"var": "rest_pain"}, True]},
            {"==": [{"var": "duration"}, "over_20_min"]},
            {"==": [{"var": "g02"}, True]},
            {"==": [{"var": "g03"}, True]},
            {"==": [{"var": "g04"}, True]},
        ]
    }
    fires = {"rest_pain": True, "duration": "1_to_20_min", "g02": False, "g03": False, "g04": False}
    no_fire = {"rest_pain": False, "duration": "1_to_20_min", "g02": False, "g03": False, "g04": False}
    assert evaluate(fire_when, fires) is True
    assert evaluate(fire_when, no_fire) is False


def test_extract_var_paths_nested():
    expr = {
        "and": [
            {"in": [{"var": "a1"}, ["above_jaw", "below_epigastrium", "finger_point"]]},
            {"==": [{"var": "a2"}, "neck_arm_or_respiration"]},
        ]
    }
    assert extract_var_paths(expr) == {"a1", "a2"}


def test_is_determinable():
    expr = {"and": [{"==": [{"var": "a1"}, "x"]}, {"==": [{"var": "a2"}, "y"]}]}
    assert is_determinable(expr, {"a1": "x"}) is False
    assert is_determinable(expr, {"a1": "x", "a2": "y"}) is True


def test_count_true():
    ns = {"a": True, "b": False, "c": True, "d": True}
    expr = {"count_true": [{"var": "a"}, {"var": "b"}, {"var": "c"}, {"var": "d"}]}
    assert evaluate(expr, ns) == 3
    assert extract_var_paths(expr) == {"a", "b", "c", "d"}


def test_count_true_threshold_pattern():
    ns = {"major1": True, "major2": True, "major3": False}
    expr = {">=": [{"count_true": [{"var": "major1"}, {"var": "major2"}, {"var": "major3"}]}, 2]}
    assert evaluate(expr, ns) is True


def test_or_short_circuits_determinability_on_true_branch():
    # second operand references a var that's genuinely absent (e.g. a field
    # that was skipped and will never be answered) -- the "or" must still be
    # determinable because the first branch alone already makes it true.
    expr = {"or": [{"==": [{"var": "echo_status"}, "not_performed"]}, {"var": "mitral_stenosis_severity"}]}
    ns = {"echo_status": "not_performed"}
    assert is_determinable(expr, ns) is True
    assert evaluate(expr, ns) is True


def test_or_not_determinable_when_no_branch_settles_it():
    expr = {"or": [{"==": [{"var": "echo_status"}, "not_performed"]}, {"var": "mitral_stenosis_severity"}]}
    ns = {"echo_status": "lesions_present"}  # first branch false, second branch missing -> can't tell yet
    assert is_determinable(expr, ns) is False


def test_and_short_circuits_determinability_on_false_branch():
    expr = {"and": [{"==": [{"var": "a"}, "x"]}, {"var": "b"}]}
    ns = {"a": "y"}  # first branch already false -> whole and is false regardless of b
    assert is_determinable(expr, ns) is True
    assert evaluate(expr, ns) is False


def test_evaluating_undeterminable_expression_raises_caller_should_check_first():
    expr = {"==": [{"var": "not_answered_yet"}, "x"]}
    with pytest.raises(KeyError):
        evaluate(expr, {})
