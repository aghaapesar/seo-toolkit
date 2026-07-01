"""Tests for form bool parsing."""

from web.app.form_utils import parse_form_bool


def test_parse_form_bool_false_strings():
    """Form false values should not be treated as True."""
    assert parse_form_bool("false") is False
    assert parse_form_bool("0") is False
    assert parse_form_bool("") is False


def test_parse_form_bool_true_strings():
    """Form true values should parse as True."""
    assert parse_form_bool("true") is True
    assert parse_form_bool("1") is True
    assert parse_form_bool(True) is True
