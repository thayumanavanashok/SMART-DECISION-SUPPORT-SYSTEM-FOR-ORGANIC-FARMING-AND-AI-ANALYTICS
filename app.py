from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from gemini import get_crop_suggestions, get_chatbot_response
from farm_intelligence import get_farm_intelligence
from market_scraper import scrape_market_prices, get_multiple_crop_prices, get_price_summary
from weather_api import (
    get_weather_for_farm,
    get_weather_by_city,
    get_agricultural_weather_advisory,
    search_locations_in_india,
    get_india_states_and_districts,
)
import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        farm_data = request.form.to_dict()
        session['farm_data'] = farm_data
        return redirect(url_for('crop_suggestions'))
    return render_template('index.html')

@app.route('/suggestions', methods=['GET', 'POST'])
def crop_suggestions():
    farm_data = session.get('farm_data')
    if not farm_data:
        return redirect(url_for('index'))

    suggestions = get_crop_suggestions(farm_data)
    if not suggestions:
        return render_template(
            'crop_suggestions.html',
            farm_data=farm_data,
            suggestions=[],
            error='No real-time suggestion data available right now. Please try again later.',
        )

    print(f"Suggestions: {suggestions}")
    return render_template('crop_suggestions.html', farm_data=farm_data, suggestions=suggestions)

@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    if request.method == 'POST':
        data = request.json
        farm_data = session.get('farm_data')
        response = get_chatbot_response(data['message'], farm_data, data.get('image_url'))
        return jsonify({'response': response})
    
    now = datetime.datetime.now()
    return render_template('chatbot.html', farm_data=session.get('farm_data'), now=now)

@app.route('/farm_intelligence')
def farm_intelligence_route():
    farm_data = session.get('farm_data')
    if not farm_data:
        return redirect(url_for('index'))

    unified_context, intelligence, recommendations, decision_support, structured_recommendations = get_farm_intelligence(farm_data)

    return render_template(
        'farm_intelligence.html',
        farm_data=farm_data,
        unified_context=unified_context,
        intelligence=intelligence,
        recommendations=recommendations,
        decision_support=decision_support,
        structured_recommendations=structured_recommendations
    )


@app.route('/api/farm_intelligence', methods=['GET'])
def farm_intelligence_api():
    farm_data = session.get('farm_data')
    if not farm_data:
        return jsonify({'error': 'Farm profile not found in session'}), 400

    unified_context, intelligence, recommendations, decision_support, structured_recommendations = get_farm_intelligence(farm_data)
    return jsonify(
        {
            'unified_context': unified_context,
            'intelligence': intelligence,
            'recommendations': recommendations,
            'structured_recommendations': structured_recommendations,
            'decision_support': decision_support,
        }
    )


# Market Price Routes
@app.route('/api/market-price/<crop_name>', methods=['GET'])
def get_market_price(crop_name):
    """Get current market price for a crop"""
    try:
        price_data = scrape_market_prices(crop_name)
        if price_data:
            return jsonify(price_data)
        return jsonify({'error': f'No price data available for {crop_name}'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/market-prices', methods=['POST'])
def get_market_prices():
    """Get market prices for multiple crops"""
    try:
        data = request.json
        crops = data.get('crops', [])
        
        if not crops:
            return jsonify({'error': 'No crops specified'}), 400
        
        prices = get_multiple_crop_prices(crops)
        return jsonify({'prices': prices})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/price-summary/<crop_name>', methods=['GET'])
def price_summary(crop_name):
    """Get price summary for a crop"""
    try:
        summary = get_price_summary(crop_name)
        return jsonify(summary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/market', methods=['GET'])
def market_page():
    """Market prices page"""
    farm_data = session.get('farm_data')
    suggested_crops = farm_data.get('crops', []) if farm_data else []
    
    prices = {}
    for crop in suggested_crops:
        prices[crop] = scrape_market_prices(crop)
    
    return render_template('market.html', farm_data=farm_data, prices=prices)


# Weather Routes
@app.route('/api/weather', methods=['GET'])
def get_weather():
    """Get weather data for farm location"""
    try:
        farm_data = session.get('farm_data')
        
        if not farm_data:
            return jsonify({'error': 'Farm profile not found in session'}), 400
        
        latitude = farm_data.get('latitude')
        longitude = farm_data.get('longitude')
        
        if not latitude or not longitude:
            # Try city-based lookup
            city = farm_data.get('location') or farm_data.get('city')
            if city:
                weather_data = get_weather_by_city(city, 'IN')
            else:
                return jsonify({'error': 'No location data provided'}), 400
        else:
            weather_data = get_weather_for_farm(farm_data)
        
        if weather_data:
            return jsonify(weather_data)
        return jsonify({'error': 'Could not fetch weather data'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/weather/city/<city_name>', methods=['GET'])
def get_weather_city(city_name):
    """Get weather by city name"""
    try:
        country = request.args.get('country', 'IN')
        weather_data = get_weather_by_city(city_name, country)
        
        if weather_data:
            return jsonify(weather_data)
        return jsonify({'error': f'Weather data not found for {city_name}'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/weather/locations/india', methods=['GET'])
def get_india_locations():
    """Search available Indian locations using OpenWeather geocoding."""
    try:
        query = request.args.get('q', '').strip()
        limit_param = request.args.get('limit', '20').strip()

        if not query:
            return jsonify({'error': 'Query parameter q is required'}), 400

        try:
            limit = int(limit_param)
        except ValueError:
            return jsonify({'error': 'limit must be an integer'}), 400

        locations = search_locations_in_india(query, limit)
        return jsonify(
            {
                'query': query,
                'country': 'IN',
                'count': len(locations),
                'locations': locations,
            }
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/india/states-districts', methods=['GET'])
def get_india_states_districts():
    """Return all India states/UTs and their districts."""
    try:
        refresh = request.args.get('refresh', 'false').lower() == 'true'
        states = get_india_states_and_districts(force_refresh=refresh)
        return jsonify(
            {
                'count': len(states),
                'states': states,
            }
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/weather/advisory', methods=['GET'])
def weather_advisory():
    """Get agricultural weather advisory"""
    try:
        farm_data = session.get('farm_data')
        
        if not farm_data:
            return jsonify({'error': 'Farm profile not found in session'}), 400
        
        latitude = farm_data.get('latitude')
        longitude = farm_data.get('longitude')
        
        if latitude and longitude:
            weather_data = get_weather_for_farm(farm_data)
        else:
            city = farm_data.get('location') or farm_data.get('city')
            if city:
                weather_resp = get_weather_by_city(city, 'IN')
                weather_data = {'current': weather_resp}
            else:
                return jsonify({'error': 'No location data provided'}), 400
        
        if weather_data:
            advisory = get_agricultural_weather_advisory(weather_data)
            return jsonify(advisory)
        return jsonify({'error': 'Could not generate advisory'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/weather', methods=['GET'])
def weather_page():
    """Weather and advisory page"""
    farm_data = session.get('farm_data')
    if not farm_data:
        return redirect(url_for('index'))
    
    weather_data = None
    advisory = None
    
    latitude = farm_data.get('latitude')
    longitude = farm_data.get('longitude')
    
    if latitude and longitude:
        weather_data = get_weather_for_farm(farm_data)
    else:
        city = farm_data.get('location') or farm_data.get('city')
        if city:
            weather_response = get_weather_by_city(city, 'IN')
            weather_data = {'current': weather_response}
    
    if weather_data:
        advisory = get_agricultural_weather_advisory(weather_data)
    
    return render_template('weather.html', farm_data=farm_data, weather=weather_data, advisory=advisory)


if __name__ == '__main__':
    app.run(debug=True)

