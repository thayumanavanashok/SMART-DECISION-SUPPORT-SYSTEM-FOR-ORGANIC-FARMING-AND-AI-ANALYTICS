"""
Market price scraper for agricultural products using LLM-based scraping
"""
import requests
import logging
from typing import Dict, List, Optional
from datetime import datetime
import re
import os

logger = logging.getLogger(__name__)

DATA_GOV_DEFAULT_API_KEY = "579b464db66ec23bdd0000014ba1f00fb85709f0c9de1da0a8c3c29db7cf8"
AGMARKNET_V1_BASE = "https://api.agmarknet.gov.in/v1"

_FILTER_CACHE: Dict[str, List[Dict]] = {}
_MARKET_CACHE: List[Dict] = []
_COMMODITY_MARKET_HINT: Dict[int, Dict[str, int]] = {}


COMMODITY_ALIASES = {
    "black gram": ["black gram", "urad", "urd", "urd bean", "black gram (urd beans)(whole)"],
    "black gram (ulundu)": ["black gram", "urad", "urd", "black gram (urd beans)(whole)"],
    "urad": ["black gram", "urad", "urd", "black gram (urd beans)(whole)"],
    "green gram": ["green gram", "moong", "mung", "green gram (whole)"],
    "finger millet": ["finger millet", "ragi"],
    "finger millet (ragi)": ["finger millet", "ragi"],
    "groundnut": ["groundnut", "peanut", "ground nut"],
    "red gram": ["red gram", "tur", "arhar", "pigeon pea"],
}


def _normalize_crop_name(value: str) -> str:
    text = (value or "").strip().lower()
    if not text:
        return ""
    return re.sub(r"\s+", " ", text)


def _base_crop_name(value: str) -> str:
    text = _normalize_crop_name(value)
    return re.sub(r"\s*\(.*?\)", "", text).strip()


def _build_query_terms(crop_name: str) -> List[str]:
    normalized = _normalize_crop_name(crop_name)
    base = _base_crop_name(crop_name)

    terms = [normalized, base]
    terms.extend(COMMODITY_ALIASES.get(normalized, []))
    terms.extend(COMMODITY_ALIASES.get(base, []))

    seen = set()
    deduped_terms = []
    for term in terms:
        if term and term not in seen:
            deduped_terms.append(term)
            seen.add(term)

    return deduped_terms


def _filter_records_by_terms(records: List[Dict], terms: List[str]) -> List[Dict]:
    if not records or not terms:
        return []

    matched = []
    for record in records:
        commodity = _normalize_crop_name(record.get("commodity", ""))
        if not commodity:
            continue

        if any(term in commodity or commodity in term for term in terms):
            matched.append(record)

    return matched


def scrape_market_prices(crop_name: str) -> Optional[Dict]:
    """
    Scrape real-time market prices for agricultural crops.
    Uses LLM-based web scraping from multiple sources.
    
    Args:
        crop_name: Name of the crop to fetch prices for
        
    Returns:
        Dictionary with price information or None if scraping fails
    """
    try:
        prices = _scrape_from_agmarknet_v1_source(crop_name)
        if prices:
            return prices

        # Try to scrape from agricultural market data source.
        prices = _scrape_from_agritech_source(crop_name)
        if prices:
            return prices

    except Exception as e:
        logger.error(f"Error scraping prices for {crop_name}: {str(e)}")

    return None


def _get_agmarknet_filters() -> List[Dict]:
    if _FILTER_CACHE.get("commodities"):
        return _FILTER_CACHE["commodities"]

    try:
        response = requests.get(f"{AGMARKNET_V1_BASE}/daily-price-arrival/filters", timeout=20)
        if response.status_code != 200:
            return []
        data = response.json().get("data", {})
        commodities = data.get("cmdt_data", []) or []
        _FILTER_CACHE["commodities"] = commodities
        return commodities
    except Exception:
        return []


def _get_agmarknet_markets() -> List[Dict]:
    global _MARKET_CACHE

    if _MARKET_CACHE:
        return _MARKET_CACHE

    try:
        response = requests.get(f"{AGMARKNET_V1_BASE}/dashboard-market-filter", timeout=20)
        if response.status_code != 200:
            return []
        markets = response.json().get("data", []) or []
        _MARKET_CACHE = markets
        return markets
    except Exception:
        return []


def _resolve_commodity_id(crop_name: str, commodities: List[Dict]) -> Optional[int]:
    terms = _build_query_terms(crop_name)
    if not commodities or not terms:
        return None

    for commodity in commodities:
        name = _normalize_crop_name(commodity.get("cmdt_name", ""))
        if any(term in name or name in term for term in terms):
            return commodity.get("cmdt_id")

    return None


def _extract_numeric_prices_from_rows(rows: List[Dict]) -> Dict:
    values = []
    unit_of_price = None

    for row in rows:
        row_unit = _normalize_crop_name(row.get("unitOfPrice", ""))
        if row_unit and row_unit != "nr":
            unit_of_price = row_unit

        for key, value in row.items():
            if key in {"variety", "unitOfPrice"}:
                continue
            try:
                numeric = float(str(value).replace(",", "").strip())
                values.append(numeric)
            except Exception:
                continue

    if not values:
        return {"values": [], "unit": unit_of_price}

    # Most Agmarknet entries are INR per quintal (qtl/qtal).
    if unit_of_price and ("qtl" in unit_of_price or "quintal" in unit_of_price or "qtal" in unit_of_price):
        values = [round(v / 100.0, 2) for v in values]
        return {"values": values, "unit": "kg"}

    return {"values": values, "unit": "kg"}


def _fetch_lastweek_prices(state_id: int, market_id: int, commodity_id: int) -> Optional[Dict]:
    try:
        response = requests.get(
            f"{AGMARKNET_V1_BASE}/prices-and-arrivals/commodity-price/lastweek",
            params={"stateId": state_id, "marketId": market_id, "commodityId": commodity_id},
            timeout=15,
        )
        if response.status_code != 200:
            return None

        payload = response.json()
        rows = payload.get("data", []) or []
        extracted = _extract_numeric_prices_from_rows(rows)
        values = extracted.get("values", [])
        if not values:
            return None

        values.sort()
        return {
            "min": values[0],
            "max": values[-1],
            "avg": round(sum(values) / len(values), 2),
            "currency": "INR",
            "unit": extracted.get("unit", "kg"),
            "source": "agmarknet-v1",
            "updated_at": datetime.now().isoformat(),
            "data_points": len(values),
        }
    except Exception:
        return None


def _scrape_from_agmarknet_v1_source(crop_name: str) -> Optional[Dict]:
    commodities = _get_agmarknet_filters()
    markets = _get_agmarknet_markets()
    commodity_id = _resolve_commodity_id(crop_name, commodities)

    if not commodity_id or not markets:
        return None

    # Use previous successful market hint for this commodity first.
    hint = _COMMODITY_MARKET_HINT.get(commodity_id)
    if hint:
        hinted = _fetch_lastweek_prices(hint.get("state_id"), hint.get("market_id"), commodity_id)
        if hinted:
            hinted["crop"] = crop_name
            return hinted

    api_allowed_markets = [m for m in markets if m.get("api_allowed_market")]
    candidate_markets = api_allowed_markets if api_allowed_markets else markets

    for market in candidate_markets[:150]:
        state_id = market.get("state_id")
        market_id = market.get("id")
        if state_id is None or market_id is None:
            continue

        prices = _fetch_lastweek_prices(state_id, market_id, commodity_id)
        if prices:
            _COMMODITY_MARKET_HINT[commodity_id] = {"state_id": state_id, "market_id": market_id}
            prices["crop"] = crop_name
            return prices

    return None


def _scrape_from_agritech_source(crop_name: str) -> Optional[Dict]:
    """
    Scrape from agricultural data APIs
    """
    # Example: Using a public agricultural API
    url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a5c0-3b405fcc2f43"

    api_key = os.getenv("DATA_GOV_API_KEY") or DATA_GOV_DEFAULT_API_KEY

    base_params = {
        "format": "json",
        "limit": 100,
    }
    if api_key:
        base_params["api-key"] = api_key

    def _fetch_records(params: Dict) -> List[Dict]:
        try:
            response = requests.get(url, params=params, timeout=12)
            if response.status_code != 200:
                if response.status_code == 403 and "api-key" in params:
                    # Retry without API key if key is blocked/expired.
                    no_key_params = dict(params)
                    no_key_params.pop("api-key", None)
                    retry_response = requests.get(url, params=no_key_params, timeout=12)
                    if retry_response.status_code == 200:
                        retry_data = retry_response.json()
                        return retry_data.get("records", []) or []

                logger.warning("Agmarknet responded with status %s for params %s", response.status_code, params)
                return []
            data = response.json()
            return data.get("records", []) or []
        except Exception as e:
            logger.warning("Agmarknet request failed for params %s: %s", params, str(e))
            return []

    terms = _build_query_terms(crop_name)
    for term in terms:
        query = term.title()
        params = dict(base_params)
        params["filters[commodity]"] = query
        records = _fetch_records(params)
        if records:
            prices = _parse_mandi_data(records, crop_name)
            if prices:
                return prices

    # Broad fallback search: fetch latest rows and match commodity aliases locally.
    broad_params = dict(base_params)
    broad_params["limit"] = 800
    records = _fetch_records(broad_params)
    if records:
        matched = _filter_records_by_terms(records, terms)
        if matched:
            prices = _parse_mandi_data(matched, crop_name)
            if prices:
                return prices
    
    return None


def _scrape_from_mandi_source(crop_name: str) -> Optional[Dict]:
    """
    Placeholder for future mandi scraping implementation.

    This intentionally returns None to avoid synthetic/static prices.
    """
    logger.info("Mandi scraping not implemented for crop: %s", crop_name)
    return None


def _parse_mandi_data(records: List[Dict], crop_name: str) -> Optional[Dict]:
    """
    Parse mandi data from API response
    """
    try:
        prices = []
        
        for record in records:
            try:
                modal_price = str(record.get("modal_price", "0")).replace(",", "").strip()
                # Agmarknet modal_price is typically INR per quintal.
                price_per_quintal = float(modal_price)
                price_per_kg = round(price_per_quintal / 100.0, 2)
                if price_per_kg > 0:
                    prices.append(price_per_kg)
            except (ValueError, TypeError):
                continue
        
        if prices:
            prices.sort()
            return {
                "crop": crop_name,
                "min": prices[0],
                "max": prices[-1],
                "avg": sum(prices) / len(prices),
                "currency": "INR",
                "unit": "kg",
                "source": "agmarknet",
                "updated_at": datetime.now().isoformat(),
                "data_points": len(prices)
            }
    except Exception as e:
        logger.error(f"Error parsing mandi data: {str(e)}")
    
    return None


def get_multiple_crop_prices(crops: List[str]) -> Dict[str, Dict]:
    """
    Get prices for multiple crops
    
    Args:
        crops: List of crop names
        
    Returns:
        Dictionary with crop prices
    """
    results = {}
    
    for crop in crops:
        prices = scrape_market_prices(crop)
        if prices:
            results[crop] = prices
    
    return results


def get_price_summary(crop_name: str) -> Dict:
    """
    Get a summary of crop pricing information
    """
    price_data = scrape_market_prices(crop_name)
    
    if not price_data:
        return {"error": f"No price data available for {crop_name}"}
    
    return {
        "crop": crop_name,
        "current_price_range": {
            "min": price_data.get("min"),
            "max": price_data.get("max"),
            "avg": price_data.get("avg"),
            "currency": price_data.get("currency", "INR"),
            "unit": price_data.get("unit", "kg")
        },
        "source": price_data.get("source"),
        "updated_at": price_data.get("updated_at"),
        "last_updated_seconds_ago": _get_seconds_ago(price_data.get("updated_at"))
    }


def _get_seconds_ago(timestamp_str: str) -> Optional[int]:
    """Calculate seconds since timestamp"""
    try:
        if not timestamp_str:
            return None
        updated = datetime.fromisoformat(timestamp_str)
        now = datetime.now()
        delta = (now - updated).total_seconds()
        return int(delta)
    except:
        return None
