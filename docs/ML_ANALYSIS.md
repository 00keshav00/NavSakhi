# SafeShe Machine Learning Analysis

This document outlines the current state, architecture, and implementation details of the Machine Learning pipeline located in `app/ml/`.

## 1. Architectural Overview

The ML directory represents the boundary between deterministic software engineering and statistical modeling. It provides an abstraction layer so that the Agentic AI (Decision Engine) does not need to know whether the model is a massive Deep Learning network or a simple heuristic.

The pipeline consists of three stages:
1. **Normalization**: `DataNormalizer` standardizes arbitrary JSON payloads from external APIs into a uniform schema.
2. **Feature Engineering**: `FeatureEngineer` extracts a numerical vector from the normalized schema.
3. **Inference**: A subclass of `BaseSafetyModel` or `DummyMLPredictor` takes the feature vector and predicts a score.

## 2. File Analysis

### `app/ml/normalizer.py`
- **Class**: `DataNormalizer`
- **Purpose**: Takes raw provider dictionary outputs (e.g., from `RoutingAgent`, `WeatherAgent`) and normalizes them into a flat dictionary.
- **Implementation Status**: **Stubbed/Mocked**. It extracts some real data (e.g. `weather_data.get("condition")`), but hardcodes routing outputs (`distance_km = 2.1`, `eta_mins = 14`) as placeholders.
- **Technical Debt**: Needs to dynamically parse exact OSRM geometry payloads instead of returning static `2.1` floats.

### `app/ml/features.py`
- **Class**: `FeatureEngineer`
- **Purpose**: Converts the normalized dictionary into a `List[float]` tensor suitable for XGBoost or a PyTorch model.
- **Implementation Status**: **Partially Implemented**. It extracts 4 features (Distance, ETA, Weather Weight, and Community Reports) and appends a bias term (`1.0`).
- **Logic Details**: It uses a simple ternary operator to map "Clear" weather to a weight of `24.0`, otherwise `12.0`. 

### `app/ml/models.py`
- **Classes**: `BaseSafetyModel`, `XGBoostSafetyModel`
- **Purpose**: Defines the abstract interface and a concrete simulated XGBoost model for safety scoring.
- **Implementation Status**: **Mock Implementation (Heuristic)**. 
- **Business Logic**: 
  - Expects a 4-element feature array: `[time_feat, weather_feat, crowd_feat, police_feat]`.
  - Simulates XGBoost feature importance: Police adds up to +0.3, Weather adds up to +0.2.
  - Implements a complex heuristic for time/crowd interaction (if `is_night`, high crowds receive a lower safety multiplier than during the day).
  - Returns a clamped 0-100 float.
- **TODOs**: `TODO: Replace the heuristic below with actual model inference.` (Line 28). Indicates that `joblib.load("safety_xgboost.pkl")` should be used in production.

### `app/ml/predictor.py`
- **Class**: `DummyMLPredictor`
- **Purpose**: A legacy or test harness class.
- **Implementation Status**: **Mocked**. 
- **Business Logic**: Completely ignores the feature vector and deterministically returns a static JSON payload: `{"safety_score": 98.0, "confidence": 96.0, "risk_level": "low"}`.

## 3. Current Implementation Status

**Status: MOCKED**
The ML pipeline architecture is structurally sound and ready for a real model, but the actual inference weights and calculations are purely heuristic/simulated. There is no `.pkl`, `.onnx`, or `.pt` file loaded in the current codebase.
