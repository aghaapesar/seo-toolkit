"""Unit tests for SearchConsoleAnalyzer."""

import pandas as pd

from src.analyzer import SearchConsoleAnalyzer


def test_identify_opportunities_filters_by_position():
    """Queries beyond min_position should be returned."""
    config = {"app": {"min_position": 10}}
    analyzer = SearchConsoleAnalyzer(config)
    df = pd.DataFrame(
        {
            "Query": ["a", "b", "c"],
            "Position": [5, 11, 20],
            "Impressions": [100, 200, 50],
            "CTR": [0.1, 0.02, 0.01],
        }
    )

    result = analyzer.identify_opportunities(df)

    assert len(result) == 2
    assert set(result["Query"]) == {"b", "c"}


def test_calculate_opportunity_score_adds_column():
    """Opportunity score column should be added and sorted."""
    config = {"app": {"min_position": 10}}
    analyzer = SearchConsoleAnalyzer(config)
    df = pd.DataFrame(
        {
            "Query": ["a", "b"],
            "Position": [12, 15],
            "Impressions": [100, 200],
            "CTR": [0.02, 0.01],
        }
    )

    scored = analyzer.calculate_opportunity_score(df)

    assert "opportunity_score" in scored.columns
    assert scored.iloc[0]["opportunity_score"] >= scored.iloc[1]["opportunity_score"]
