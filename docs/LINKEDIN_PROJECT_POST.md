# LinkedIn Project Showcase Post Draft

**Copy and paste the draft below to share NavSakhi on your personal LinkedIn profile:**

---

🚆 **Building NavSakhi: Exploring Women's Safety-Aware Multimodal Transit & Spatial ML**

I'm excited to share a personal project I’ve been engineering: **NavSakhi — Safer Journeys • Stronger Women**. 

NavSakhi is an end-to-end full-stack software prototype built to explore how multimodal urban transit routing, spatial machine learning, and privacy-first UX can provide transparent, safety-aware commuting guidance for women traveling across Chennai.

### 🔍 Key Engineering Highlights:

1. **Multimodal Transit Coordinator:**
   - Unified pathfinding combining Chennai Metro Rail (CMRL), Southern Railway (SRR) suburban lines, Metropolitan Transport Corporation (MTC) buses, and pedestrian connections.
   - Strict schedule and fare integrity: official CMRL and suburban railway tariff calculations with honest disclosures where transit leg fares are unintegrated.

2. **Genuine Frozen LightGBM Route Inference:**
   - Evaluates road segments using a trained LightGBM model operating on 41 canonical OpenStreetMap and spatial infrastructure features (street lighting, police station and hospital proximity, pedestrian crossings, commercial density).
   - Serves as an environmental risk proxy with native TreeSHAP feature attribution to explain why a corridor received a particular score.
   - Preserves complete data integrity: railway tracks and metro tunnels are not road segments and remain explicitly unscored rather than fabricating numbers.

3. **Privacy-First Architecture & Public Guest Access:**
   - Anyone can plan trips, inspect transit options, check real-time Open-Meteo weather data, and review constitutional legal safeguards (Zero FIR guides) without creating an account.
   - Live location tracking and sensitive workflows require explicit runtime consent and single-use WebSocket tickets.

4. **Honest Emergency Workflow Prototype:**
   - The emergency interface is designed as an architectural simulation: it dynamically calculates nearest safe havens (police stations and hospitals via OSRM) and enables user-initiated location sharing via the browser's native share sheet (`navigator.share`) or direct 112 dialing, with clear disclosures that no automated police dispatch or cellular broadcasts take place.

5. **Modern Full-Stack Stack:**
   - **Frontend:** Next.js 16 (React 19, TypeScript, Tailwind CSS, Framer Motion, MapLibre GL).
   - **Backend:** FastAPI (Python 3.10, Motor, Pydantic v2, OSRM, LightGBM, Scikit-Learn).

Check out the full repository and architecture details on GitHub:  
🔗 `https://github.com/<your-username>/NavSakhi` *(Insert your repository URL here)*

I’d love to hear your thoughts, feedback, and questions on the architectural approach!

#WebDevelopment #MachineLearning #NextJS #FastAPI #Python #TypeScript #Geospatial #DataScience #WomenSafety #UrbanTransit #SoftwareEngineering
