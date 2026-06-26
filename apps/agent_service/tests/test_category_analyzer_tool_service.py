from app.services.category_analyzer_tool_service import CategoryAnalyzerToolService

svc = CategoryAnalyzerToolService()


def test_empty_peer_list_returns_none_scores():
    result = svc.analyze([])

    assert result == {"category_trend_score": None, "category_demand_change": None}


def test_all_peers_missing_data_returns_none_scores():
    peers = [
        {"trend_score": None, "interest_change_7d": None},
        {"trend_score": None, "interest_change_7d": None},
    ]
    result = svc.analyze(peers)

    assert result == {"category_trend_score": None, "category_demand_change": None}


def test_averages_only_valid_values():
    peers = [
        {"trend_score": 60.0, "interest_change_7d": 0.2},
        {"trend_score": 40.0, "interest_change_7d": None},  # interest_change_7d eksik, ortalamadan haric
        {"trend_score": None, "interest_change_7d": 0.4},  # trend_score eksik, ortalamadan haric
    ]
    result = svc.analyze(peers)

    assert result["category_trend_score"] == 50.0  # (60+40)/2
    assert result["category_demand_change"] == 0.3  # (0.2+0.4)/2
