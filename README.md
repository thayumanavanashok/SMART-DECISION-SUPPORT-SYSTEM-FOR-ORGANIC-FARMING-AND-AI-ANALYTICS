# Organic Farming Intelligence Platform

Flask-based decision support platform for organic farming.

It combines farm profile input, weather data, live market prices, and Gemini-powered crop suggestions into a single workflow.

## What This App Does

- Captures farm profile details (soil, land size, location, water, previous crops, issues).
- Generates crop suggestions using Gemini and enriches each suggestion with live market price data.
- Builds a farm intelligence dashboard with unified context, risks, weather, and recommendation actions.
- Provides weather endpoints and advisories for Indian farm locations.
- Supports state and district selection for India via local location metadata.

## Tech Stack

- Backend: Flask
- AI: Gemini REST API
- Weather: OpenWeather (UI/weather routes) and Open-Meteo (farm intelligence metrics)
- Market data: Agmarknet v1 + Data.gov fallback path
- Frontend styles: Tailwind CSS (local build, no CDN dependency)
- Testing: Pytest

## Project Structure

- app.py: Flask routes and page rendering
- gemini.py: Crop suggestions and chatbot generation through Gemini REST
- farm_intelligence.py: Unified analysis and decision support payload
- market_scraper.py: Live market price retrieval and normalization
- weather_api.py: Weather and India location metadata helpers
- templates/: HTML templates
- static/css/: Tailwind input and generated CSS
- tests/: Unit, integration, API, and UI tests

## Prerequisites

- Python 3.10+
- Node.js 18+ (for Tailwind build)

## Setup

1. Create and activate a virtual environment.

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install Python dependencies.

```bash
pip install -r requirements.txt
```

3. Install frontend build dependencies.

```bash
npm install
```

4. Configure environment variables in .env.

```env
VITE_GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
DATA_GOV_API_KEY=optional_data_gov_key
```

Notes:
- VITE_GEMINI_API_KEY or GEMINI_API_KEY is required for crop suggestions.
- If Gemini is not configured, suggestions endpoint/page returns a real-time data unavailable message.

## Run

Start Flask app:

```bash
python app.py
```

Build Tailwind CSS once:

```bash
npm run build:css
```

Watch Tailwind during development:

```bash
npm run watch:css
```

Default app URL: http://localhost:5000

## Main Pages

- /: Farm profile form
- /suggestions: Gemini crop suggestions with live market values
- /farm_intelligence: Unified dashboard and decision support
- /market: Market price lookup view
- /weather: Weather and advisory page
- /chatbot: AI farming assistant

## API Endpoints

Farm intelligence:
- GET /api/farm_intelligence

Market data:
- GET /api/market-price/<crop_name>
- POST /api/market-prices
- GET /api/price-summary/<crop_name>

Weather and location:
- GET /api/weather
- GET /api/weather/city/<city_name>
- GET /api/weather/advisory
- GET /api/weather/locations/india?q=<query>&limit=<n>
- GET /api/india/states-districts

## Test

Run all tests:

```bash
pytest
```

## Data Behavior

- The app is configured for live-data-first behavior.
- Market prices are fetched from external public APIs and can be unavailable intermittently.
- When live sources are unavailable, endpoints return explicit no-data/error responses instead of synthetic values.
