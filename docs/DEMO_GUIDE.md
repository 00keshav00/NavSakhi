# NavSakhi — Portfolio Demonstration Guide (2–3 Minute Walkthrough)

This guide provides a structured, concise demonstration script designed for recording a portfolio video walkthrough or conducting a live technical walkthrough on LinkedIn.

---

## Pre-Demo Checklist (30 seconds)
1. **Start Backend:**
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
2. **Start Frontend:**
   ```bash
   cd frontend && npm run dev
   ```
3. Open browser at `http://localhost:3000`.

---

## Step-by-Step Demonstration Flow (2 to 3 Minutes)

### Minute 0:00 – 0:45: Landing Page & Design System
- **Action:** Open `http://localhost:3000`. Show the clean, editorial split layout and official branding: *NavSakhi — Safer Journeys • Stronger Women*.
- **Talking Points:**
  - *"NavSakhi is a personal-interest software project and working prototype built to explore women's safety-aware journey planning, multimodal urban transit routing, and privacy-conscious location features."*
  - *"The interface features a custom blush-pink, rose, lavender, and deep-plum design system with smooth micro-animations and zero layout shifts."*
  - Point to the light/dark theme toggle and responsive typography.

### Minute 0:45 – 1:30: Guest Workspace & Real Multimodal Routing
- **Action:** Click **"Plan a Safe Journey"** or **"Open Workspace"** to enter the workspace without registering.
- **Talking Points:**
  - *"Public guest access is a core architectural feature. Commuters can evaluate routes and inspect safety indicators without mandatory account creation or tracking."*
  - Search a sample trip across Chennai (e.g., Origin: `Chennai Central`, Destination: `Guindy`).
  - Demonstrate multimodal route generation:
    - Route 1: Direct CMRL Metro Rail (Blue Line) with official tariff (₹40) and transit duration.
    - Route 2: Southern Railway Suburban line from Chennai Central Suburban to Guindy.
    - Route 3: MTC Bus Feeder network with verified route stops.
  - Highlight data honesty: show that while CMRL and SRR have statutory tariffs, MTC buses clearly show `Fare unavailable` because bus fare ticketing APIs are unintegrated.

### Minute 1:30 – 2:15: Frozen Machine Learning & Environmental Risk Scoring
- **Action:** Click on the primary walking or road segment of the route to inspect the route score badge and TreeSHAP feature breakdown.
- **Talking Points:**
  - *"NavSakhi integrates a genuine frozen LightGBM regressor trained on 41 canonical OpenStreetMap and spatial infrastructure features."*
  - *"The model evaluates environmental risk proxies: street lighting, proximity to police stations and hospitals, human activity indicators, and pedestrian crossing infrastructure."*
  - *"Critically, this is an environmental risk proxy, not a crime prediction model or personal safety guarantee."*
  - Note transit leg integrity: subway tunnels and railway tracks are unscored (`null`), because the trained model only scores physical road segments.

### Minute 2:15 – 2:45: Meteorological Context & Account Boundaries
- **Action:** Navigate to `/home` to highlight the live Weather card, then click on the Sign In / Register flow.
- **Talking Points:**
  - *"The weather module fetches live meteorological observations from Open-Meteo, providing real-time ambient temperature, UV index, and precipitation forecasts."*
  - Click **"Create one"** on `/login` to show the full registration page.
  - Explain that account creation collects personal credentials, designated emergency contact information, and explicit prototype limitation consent.
  - Note database architecture: if MongoDB is not connected, the registration API returns an informative configuration-unavailable notice while guest exploration remains unrestricted.

### Minute 2:45 – 3:00: Emergency SOS & Honest Prototype Boundaries
- **Action:** Navigate to `/emergency` to display the simulated SOS workflow and safety architecture modal.
- **Talking Points:**
  - *"The emergency workflow is clearly disclosed as a simulation. It does not contact police dispatch or transmit cellular messages."*
  - *"Instead, it demonstrates nearest safe haven routing (police stations and hospitals via OSRM) and user-initiated location sharing via the browser's native share sheet or direct 112 dialing."*
  - Conclude with project purpose: *"A complete, evidence-based prototype exploring how transit data, spatial machine learning, and privacy-first UX can make daily commuting safer and more transparent."*
