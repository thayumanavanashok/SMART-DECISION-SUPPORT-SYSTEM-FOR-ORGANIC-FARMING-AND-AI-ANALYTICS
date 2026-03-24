# Organic Farming Intelligence Platform

This project provides an integrated intelligence workflow for organic farming decisions.

## Core Modules

1. Data Acquisition
- Captures farm profile from user input (soil type, pH, nutrients, land size, location, water, historical crops, issues).
- Fetches location-aware weather conditions and 5-day forecast from Open-Meteo.
- Estimates crop-health signals from reported issues and farm constraints.

2. AI-Based Analysis and Intelligence Generation
- Builds a unified context from all available data streams.
- Performs AI-assisted analysis (Gemini, when API key is available) with robust local fallback logic.
- Produces interpretable outputs: patterns, risks, opportunities, and priority actions.

3. Smart Recommendation Engine
- Recommends suitable crops based on soil and water conditions.
- Generates organic pest and disease management actions.
- Suggests harvesting and selling timing aligned with weather and seasonal demand hints.

4. Decision Support and Farm Management Optimization
- Computes readiness and risk indicators.
- Surfaces priority actions for proactive farm operations.
- Emphasizes sustainability and resource-efficiency under organic farming principles.

5. User Interface and Visualization Layer
- Dashboard view consolidates all outputs into a single decision interface.
- Includes weather forecast table, intelligence summaries, recommendation cards, and optimization metrics.

## Capability Mapping (Implemented)

1. Data Acquisition and Consolidation
- Input layer captures soil, location, nutrients, water availability, and field issues.
- Weather data is fetched via Open-Meteo geocoding + forecast APIs.
- Crop health is estimated through field issue and constraint-based screening.
- Source status and completeness metrics are shown in the intelligence dashboard.

2. AI-Based Analysis and Intelligence Generation
- Unified context combines all available farm signals into one analysis object.
- Gemini analysis is used when configured; robust local fallback analysis always runs.
- Intelligence output includes patterns, risks, opportunities, and explainability notes.

3. Smart Recommendation Engine
- Recommends crops based on soil suitability and water constraints.
- Provides organic pest and disease management steps.
- Suggests harvesting and selling timing based on weather and seasonal logic.

4. Decision Support and Farm Management Optimization
- Decision readiness and operational risk scores are computed automatically.
- Priority actions are surfaced for proactive farm operations.
- Resource efficiency hints enforce low-input, organic-first practices.

5. User Interface and Visualization Layer
- Dedicated Farm Intelligence Dashboard presents all modules in one flow.
- Structured recommendation blocks and 5-day weather table improve interpretability.
- JSON API endpoint enables external monitoring and integration use cases.

## API Endpoint

- `GET /api/farm_intelligence`
	- Returns unified context, AI intelligence, recommendations, and decision-support payload from the current farm session.
	- Use this endpoint for integrating mobile apps, reporting tools, or external dashboards.

## Run Locally

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Add Gemini API key to `.env` (optional but recommended):

```env
VITE_GEMINI_API_KEY=your_key_here
```

3. Start the app:

```bash
python app.py
```
