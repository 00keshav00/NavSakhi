# MTC Chennai GTFS Data Partnership Request

## Purpose
SafeShe is a safety-first multimodal mobility planner. To provide women in Chennai with mathematically validated, accurate bus routing, SafeShe requires verifiable public transit data. SafeShe currently explicitly rejects bus routing proposals rather than guessing unverified schedules or hallucinating geometries. This document outlines the technical requirements to light up the MTC bus network inside the SafeShe application safely.

## Required Fields
We require a valid **GTFS Static** feed covering the Chennai Metropolitan Transport Corporation (MTC) network, strictly adhering to standard GTFS specifications.
The feed must include:
- `stops.txt` (including precise geographic coordinates)
- `routes.txt` (service identifiers and colors/branding)
- `trips.txt` (mapping route IDs to physical vehicular paths and directions)
- `stop_times.txt` (accurate temporal arrival/departure matrices)
- `calendar.txt` & `calendar_dates.txt` (holidays, weekends, and operating constraints)

**Optional but Highly Preferred:**
- `shapes.txt` (verified road alignments to prevent straight-line routing artifacts)
- `fare_attributes.txt` & `fare_rules.txt` (for precise affordability modelling)

## Preferred Format
- Standard `.zip` archive containing standard UTF-8 encoded comma-separated (CSV) GTFS files.

## Update Frequency & Freshness
- A minimum update cadence of **30 days** is required to reflect route realignments, timetable adjustments, and temporary construction detours accurately. 
- SafeShe enforces strict freshness policies. Feeds older than 90 days will be flagged to users as `STALE`, and potentially trigger `INSUFFICIENT_BUS_DATA` fallback behavior.

## Licensing & Privacy
- **License:** Open Government Data (OGDL) or equivalent open-source public transit license.
- **Privacy:** No personally identifiable information (PII) is expected or accepted in this feed.

## Contact & Authentication
- If this dataset is protected via an API gateway, SafeShe requests formal authentication credentials (API Keys, OAuth2).
- We ask the issuing authority to designate a technical point-of-contact for dataset anomalies and schema transitions.

## Live Feed Requirements (Future Expansion)
- SafeShe's architecture is capable of ingesting GTFS-Realtime (`TripUpdates.pb`, `VehiclePositions.pb`, `Alerts.pb`). We invite discussions on provisioning access to GTFS-RT to communicate live suspensions or delays to users directly.
