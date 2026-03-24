import os
import json
import requests
from dotenv import load_dotenv
from market_scraper import scrape_market_prices

load_dotenv()


def _safe_float(value, fallback=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _normalize_suggestions(raw_suggestions):
    """Normalize Gemini response into a strict list schema expected by templates."""
    if not isinstance(raw_suggestions, list):
        return []

    normalized = []
    for item in raw_suggestions[:3]:
        if not isinstance(item, dict):
            continue

        organic_guide = item.get("organicGuide") if isinstance(item.get("organicGuide"), dict) else {}
        normalized.append(
            {
                "name": str(item.get("name") or "").strip(),
                "confidence": int(_safe_float(item.get("confidence"), 0)),
                "waterNeeds": str(item.get("waterNeeds") or "").strip(),
                "sunlight": str(item.get("sunlight") or "").strip(),
                "temperature": str(item.get("temperature") or "").strip(),
                "description": str(item.get("description") or "").strip(),
                "organicGuide": {
                    "preparation": organic_guide.get("preparation") if isinstance(organic_guide.get("preparation"), list) else [],
                    "planting": organic_guide.get("planting") if isinstance(organic_guide.get("planting"), list) else [],
                    "maintenance": organic_guide.get("maintenance") if isinstance(organic_guide.get("maintenance"), list) else [],
                    "harvesting": organic_guide.get("harvesting") if isinstance(organic_guide.get("harvesting"), list) else [],
                },
            }
        )

    return normalized


def _attach_market_prices(suggestions):
    """Attach current market prices for each recommended crop."""
    enriched = []

    for crop in suggestions:
        crop_name = crop.get("name")
        market = scrape_market_prices(crop_name or "") if crop_name else None

        if market:
            crop["marketPrice"] = {
                "min": market.get("min"),
                "max": market.get("max"),
                "avg": market.get("avg"),
                "unit": market.get("unit", "kg"),
                "currency": market.get("currency", "INR"),
                "source": market.get("source", "unknown"),
                "updated_at": market.get("updated_at"),
            }

        else:
            crop["marketPrice"] = None

        enriched.append(crop)

    return enriched


def _build_fallback_chatbot_response(user_input, farm_data):
    return "Real-time AI response unavailable. Please configure Gemini API and retry."


def _get_gemini_api_key():
    return os.getenv("VITE_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")


def _generate_gemini_text(prompt):
    api_key = _get_gemini_api_key()
    if not api_key:
        return None

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_name}:generateContent"
    )
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt,
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.4,
            "responseMimeType": "text/plain",
        },
    }

    try:
        response = requests.post(url, params={"key": api_key}, json=payload, timeout=25)
        response.raise_for_status()
        data = response.json()
        candidates = data.get("candidates") or []
        if not candidates:
            return None

        parts = (((candidates[0] or {}).get("content") or {}).get("parts")) or []
        if not parts:
            return None

        return parts[0].get("text")
    except Exception as e:
        print(f"Error calling Gemini REST API: {e}")
        return None

def get_crop_suggestions(farm_data):
    if not _get_gemini_api_key():
        return []

    try:
        prompt = f"""As an Indian farming expert, suggest 3 best crops to grow. Use simple language.
    Respond ONLY with a valid JSON array of objects and no extra text.
    Each object must match this strict schema and data types:
    - name: string
    - confidence: integer (0 to 100)
    - waterNeeds: string (Low|Medium|High)
    - sunlight: string (Full Sun|Partial Shade|Full Shade)
    - temperature: string (temperature range in C)
    - description: string
    - organicGuide: object with arrays of strings (preparation, planting, maintenance, harvesting)

    Expected JSON shape:
[{{
  "name": "Crop Name",
  "confidence": 95,
  "waterNeeds": "Low|Medium|High",
  "sunlight": "Full Sun|Partial Shade|Full Shade",
  "temperature": "Temperature range in C",
  "description": "Why this crop is suitable (use simple Indian English)",
  "organicGuide": {{
    "preparation": ["Simple step 1", "Simple step 2", "Simple step 3"],
    "planting": ["Simple step 1", "Simple step 2", "Simple step 3"],
    "maintenance": ["Simple step 1", "Simple step 2", "Simple step 3"],
    "harvesting": ["Simple step 1", "Simple step 2", "Simple step 3"]
  }}
}}]

Farm data:
- Soil Type: {farm_data.get('soilType')}
- Land Size: {farm_data.get('landSize')} acres
- Location: {farm_data.get('location')}
- Water Availability: {farm_data.get('waterAvailability')}
- Previous Crops: {farm_data.get('previousCrops')}"""

        text = _generate_gemini_text(prompt)
        if not text:
            return []
        
        try:
            clean_text = text.replace('```json', '').replace('```', '').strip()
            suggestions = _normalize_suggestions(json.loads(clean_text))
            
            if not suggestions:
                raise ValueError('Response is not a list')

            return _attach_market_prices(suggestions)
        except (json.JSONDecodeError, ValueError) as e:
            print(f'Failed to parse AI response: {text}')
            return []
    except Exception as e:
        print(f'Error in get_crop_suggestions: {e}')
        return []

def get_chatbot_response(user_input, farm_data, image_url=None):
    if not _get_gemini_api_key():
        return _build_fallback_chatbot_response(user_input, farm_data or {})

    try:
        prompt = f"""You are a friendly Indian farming expert who speaks in simple, clear language. Your goal is to help farmers understand organic farming methods easily.

When answering questions:
1. Start with "Namaste! 🙏" to make farmers feel welcome
2. Break down complex farming terms into simple words
3. Use short, clear sentences
4. Give practical examples that Indian farmers can relate to
5. Focus only on organic methods - no chemicals
6. End with a simple tip or encouragement

If an image is provided, first analyze it for:
1. Plant health issues
2. Disease symptoms
3. Pest damage
4. Growth problems
Then provide organic solutions.

If farmer mentions a problem:
1. First explain the problem in simple words
2. Then give 2-3 easy organic solutions
3. Tell how to prevent this problem
4. Suggest local materials they can use
5. Add one traditional farming wisdom if relevant

Keep responses friendly but structured like this:
- Problem (if any): [simple explanation]
- Solution steps: [numbered list]
- Prevention: [bullet points]
- Quick tip: [one practical advice]

User question: {user_input}"""

        if image_url:
            prompt += f"\nImage URL: {image_url}"

        if farm_data:
            prompt += f"""

Farmer's details:
- Soil Type: {farm_data.get('soilType')}
- Land Size: {farm_data.get('landSize')} acres
- Location: {farm_data.get('location')}
- Water Available: {farm_data.get('waterAvailability')}
- Previous Crops: {farm_data.get('previousCrops')}
- Current Problems: {farm_data.get('issues')}

Use this information to give personalized advice."""

        prompt += '\n\nRemember to use simple Indian English and give practical solutions that farmers can easily follow.'

        text = _generate_gemini_text(prompt)
        return text or _build_fallback_chatbot_response(user_input, farm_data or {})
    except Exception as e:
        print(f'Error in get_chatbot_response: {e}')
        return _build_fallback_chatbot_response(user_input, farm_data or {})