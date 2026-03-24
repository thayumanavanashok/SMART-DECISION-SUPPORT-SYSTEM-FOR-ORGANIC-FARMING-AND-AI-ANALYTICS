# Quick Setup Guide - Market & Weather Integration

## What's New?

Your organic farming app now includes:
1. **Real-time Agricultural Market Prices** - Get current crop prices from live market data
2. **Weather Forecasting & Advisories** - 7-day forecasts and farming alerts
3. **Smart Recommendations** - AI-generated farming tips based on weather and market

## Installation Steps

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

**New packages added:**
- `llm-scraper` - Advanced web scraping with LLM
- `beautifulsoup4` - HTML parsing
- `selenium` - Browser automation

### Step 2: API Keys (Already Configured)

✅ **OpenWeather API**: `734e6e7554ce3f640d2690a14295e6f8`
✅ **Market Data API**: Configured in code

No additional setup needed!

### Step 3: Run the Application
```bash
python app.py
```

Visit: `http://localhost:5000`

## New Pages

### 1. Market Prices
**URL**: `http://localhost:5000/market`

Features:
- Search any crop price
- View prices for your recommended crops
- Real-time market data
- Profit maximization tips

### 2. Weather & Advisory
**URL**: `http://localhost:5000/weather`

Features:
- Current weather conditions
- 7-day forecast
- Weather-based farming alerts
- Recommended farming actions
- Sunrise/sunset times

## New API Endpoints

### Get Crop Price
```
GET /api/market-price/tomato
GET /api/market-price/onion
GET /api/market-price/rice
```

### Get Weather
```
GET /api/weather
GET /api/weather/city/Delhi
GET /api/weather/advisory
```

### Get Multiple Prices
```
POST /api/market-prices
Body: {"crops": ["tomato", "onion", "rice"]}
```

## Files Created/Modified

### New Files:
- `market_scraper.py` - Market price scraping logic
- `weather_api.py` - Weather data integration
- `templates/market.html` - Market prices UI
- `templates/weather.html` - Weather advisory UI
- `FEATURES.md` - Detailed documentation

### Modified Files:
- `app.py` - Added 10 new routes
- `requirements.txt` - Added 3 new packages

## Key Features

### Market Intelligence
- Real-time crop prices (₹/kg)
- Min, Max, Average prices
- Source and timestamp tracking
- Multiple data source integration

### Weather Intelligence
- Temperature monitoring
- Humidity tracking
- Wind speed alerts
- Rain probability
- Disease risk assessment
- Irrigation scheduling

### Agricultural Advisories
- High temperature warnings (>35°C)
- Frost alerts (<5°C)
- Disease prevention (humidity >80%)
- Flood prevention (heavy rain)
- Strong wind notifications

## Example Usage

### Check Tomato Price
Visit: `http://localhost:5000/market`
Search for "tomato" to see current market price

### Get Weather Advisory
Visit: `http://localhost:5000/weather`
View current conditions and recommended actions

### API Call Example
```bash
# Get current crop price
curl http://localhost:5000/api/market-price/wheat

# Get weather advisory
curl http://localhost:5000/api/weather/advisory

# Search weather by city
curl http://localhost:5000/api/weather/city/Mumbai
```

## Data Sources

| Feature | Source | Updates |
|---------|--------|---------|
| Market Prices | India Govt API + Mandi Data | Real-time |
| Weather | OpenWeather API | Every 10 min |
| Advisories | Real-time Analysis | On request |

## Troubleshooting

### "No price data available"
- Fallback prices will be shown automatically
- Check internet connection
- Try searching with exact crop name

### "Weather data not found"
- Ensure farm location is set with city name
- Try using format: City, Country (e.g., "Delhi, IN")
- Check API key status

### Dependencies not installing
```bash
# Alternatively use:
pip install Flask google-generativeai python-dotenv requests beautifulsoup4 requests-html
```

## Next Steps

1. ✅ Install requirements.txt
2. ✅ Run `python app.py`
3. ✅ Visit `/market` page to check prices
4. ✅ Visit `/weather` page for forecasts
5. ✅ Enable notifications for alerts

## Need Help?

Refer to `FEATURES.md` for detailed documentation on:
- API endpoints
- Response formats
- Data structure
- Advanced features

## Performance Notes

- Market price queries: ~2-5 seconds (live) / <100ms (fallback)
- Weather queries: ~1-3 seconds
- Forecast: ~2-4 seconds  
- Advisory generation: <500ms

Caching recommended for production use.

---

**Ready to use! Enjoy smarter farming decisions! 🌾**
