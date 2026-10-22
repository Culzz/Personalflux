import pytest
from adaptive import long_term_weight, blend


def test_fixed_ignores_shift():
    assert long_term_weight(0.5, shift=1.0, adaptive=False) == 0.5


def test_adaptive_turns_long_term_down_on_strong_shift():
    assert long_term_weight(0.5, 1.0, True) == pytest.approx(0.0)
    assert long_term_weight(0.5, 0.0, True) == pytest.approx(0.5)


def test_weak_shift_keeps_most_of_long_term():
    assert long_term_weight(0.5, 0.1, True) == pytest.approx(0.45)


def test_blend_adds_weighted_long_term():
    out = blend({1: 1.0, 2: 0.5}, {2: 1.0, 3: 1.0}, weight=0.5)
    assert out == {1: 1.0, 2: 1.0, 3: 0.5}