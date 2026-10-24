"""Text rules for names, codes and search (design §3 search_text; edge cases #10, #11)."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from domain.text import InvalidCode, clean_name, employee_code, fold


@pytest.mark.parametrize(
    ("raw", "folded"),
    [
        ("José Núñez", "jose nunez"),
        ("  Åsa\tLund  ", "asa lund"),
        ("Straße", "strasse"),
        ("\uff21\uff22\uff23", "abc"),  # full-width ABC
        ("O'Brien-Smith", "o'brien-smith"),
        ("山田 太郎", "山田 太郎"),
        ("E00042", "e00042"),
    ],
)
def test_folds_case_accents_width_and_spacing(raw: str, folded: str) -> None:
    assert fold(raw) == folded


def test_a_folded_query_finds_a_folded_name() -> None:
    assert fold("jose") in fold("José Núñez")


@given(st.text())
def test_folding_twice_changes_nothing(text: str) -> None:
    assert fold(fold(text)) == fold(text)


def test_a_name_is_stored_in_one_unicode_form_with_single_spaces() -> None:
    composed, decomposed = "Jos\u00e9", "Jose\u0301"  # the same name, typed two ways
    assert clean_name(f"  {decomposed}   Núñez ") == f"{composed} Núñez"
    assert clean_name(decomposed) == clean_name(composed)


def test_names_keep_their_case_punctuation_and_script() -> None:
    for name in ["O'Brien-Smith", "山田 太郎", "Madonna", "de la Cruz"]:
        assert clean_name(name) == name


@pytest.mark.parametrize(("raw", "code"), [("e00042", "E00042"), (" QA-7.b_1 ", "QA-7.B_1")])
def test_employee_codes_are_trimmed_and_upper_case(raw: str, code: str) -> None:
    assert employee_code(raw) == code


@pytest.mark.parametrize("raw", ["", "   ", "E 42", "=SUM(A1)", "-42", "x" * 33, "É42"])
def test_employee_codes_with_odd_characters_are_refused(raw: str) -> None:
    with pytest.raises(InvalidCode):
        employee_code(raw)
