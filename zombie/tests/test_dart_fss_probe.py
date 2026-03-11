from __future__ import annotations

import math

from zombie.dart_fss_probe import extract_concept_value, select_best_context_value


class FakeStatement:
    def __init__(self, mapping):
        self.mapping = mapping

    def get_value_by_concept_id(self, concept_id, lang="en"):
        return self.mapping[concept_id]


def test_select_best_context_value_prefers_exact_consolidated() -> None:
    amount, label = select_best_context_value(
        {
            ("20230101-20231231", ("DX division", "Separate")): 10.0,
            ("20230101-20231231", ("Consolidated",)): 20.0,
            ("20230101-20231231", ("Consolidated", "Disclosed Amount")): 30.0,
        },
        separate=False,
    )

    assert amount == 20.0
    assert label == "Consolidated"


def test_select_best_context_value_returns_none_when_all_nan() -> None:
    amount, label = select_best_context_value(
        {
            ("20230101-20231231", ("Consolidated",)): math.nan,
            ("20230101-20231231", ("Separate",)): math.nan,
        },
        separate=False,
    )

    assert amount is None
    assert label == ""


def test_extract_concept_value_returns_first_matching_concept() -> None:
    statement = FakeStatement(
        {
            "ifrs-full_InterestExpense": {
                ("20230101-20231231", ("Consolidated",)): math.nan,
            },
            "ifrs-full_FinanceCosts": {
                ("20230101-20231231", ("Consolidated",)): 123.0,
            },
        }
    )

    amount, concept_id, label = extract_concept_value(
        statement,
        ("ifrs-full_InterestExpense", "ifrs-full_FinanceCosts"),
        separate=False,
    )

    assert amount == 123.0
    assert concept_id == "ifrs-full_FinanceCosts"
    assert label == "Consolidated"
