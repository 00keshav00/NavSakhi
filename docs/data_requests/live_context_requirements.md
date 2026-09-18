# Live Context Data Requirements

## Purpose
SafeShe fuses static scheduled infrastructure with dynamic, real-time operating conditions. The engine strictly follows a Live Overrides Static paradigm—meaning an officially scheduled 15:00 departure is treated as `UNAVAILABLE` if a trusted live-feed declares a suspension. This document outlines requirements for establishing Live Context feeds.

## Required Feeds
1. **GTFS-Realtime (Transit)**: `TripUpdates.pb` (delays), `VehiclePositions.pb`, and `Alerts.pb` (station closures, service suspensions).
2. **Traffic & Routing**: Live congestion and road closure feeds (WFS / WMS / GeoJSON REST APIs).
3. **Weather & Environmental Alerts**: Severe weather phenomena, flooding alerts, and real-time precipitation.

## External Data Adapter Contract
SafeShe does not integrate live APIs directly into the ML layer. All live data providers must satisfy a strict architectural interface:
- **Authority**: Is the endpoint verified?
- **Latency**: Sub-second response preferred.
- **Coverage**: Does it cover the SafeShe operational bounding box?
- **Failure Behavior**: If a feed goes down, the system must downgrade gracefully to `UNKNOWN` or fallback to Static logic. It must NEVER fabricate live states.

## Live Status Precedence
Partners should be aware of the following logic enforced by SafeShe:
- **LIVE SUSPENDED** → Overrides static AVAILABLE. Route is rejected.
- **LIVE UNKNOWN** → Does not falsely imply normal operation. Warning appended to trace.
- **STALE LIVE** → If `last_updated` exceeds the freshness threshold (e.g., 5 minutes), the data is discarded and ignored.
