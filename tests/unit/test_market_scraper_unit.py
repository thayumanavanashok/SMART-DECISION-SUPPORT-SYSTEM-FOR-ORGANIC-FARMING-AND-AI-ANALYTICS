from market_scraper import _parse_mandi_data


def test_parse_mandi_data_computes_min_max_avg():
    records = [
        {"modal_price": "1800"},
        {"modal_price": "2200"},
        {"modal_price": "2000"},
    ]

    result = _parse_mandi_data(records, "Onion")

    assert result is not None
    assert result["crop"] == "Onion"
    assert result["min"] == 18.0
    assert result["max"] == 22.0
    assert result["avg"] == 20.0
    assert result["source"] == "agmarknet"


def test_parse_mandi_data_returns_none_for_invalid_prices():
    records = [{"modal_price": ""}, {"modal_price": "abc"}, {"modal_price": None}]

    result = _parse_mandi_data(records, "Rice")

    assert result is None
