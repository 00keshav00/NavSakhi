# Institutional Transit Partner Requirements

## Introduction
SafeShe is a safety-first multimodal planner operating across Verified Data Boundaries. We seek partnerships with organizations like the Institute for Transportation and Development Policy (ITDP), WRI, or open-data urban collaboratives to securely bridge the gap between static infrastructure and human safety in urban mobility.

## The SafeShe Architecture
- **Verified Transport Infrastructure**: We do not guess transit topology. If a route isn't proven by data, it is excluded.
- **Route-Level Safety Modelling**: Every proposed route is evaluated dynamically against physical, environmental, and temporal risk vectors.

## Required Data Types
Partners can assist SafeShe by providing or standardizing:
1. **Network Topology**: Verified, highly accurate mappings of pedestrian pathways, overpasses, underpasses, and complex station interchanges (Suburban Rail, Metro, MRTS).
2. **Transit Schedules (GTFS)**: Timetables for informal or institutional transport services not covered by official transit feeds.
3. **Fares & Access Pricing**: Verified transit pricing algorithms to eliminate "estimated" cost heuristics.
4. **Service Status**: Centralized aggregation of real-time service suspensions or route truncations.

## Integration & Format
- **Format:** GTFS for transit, GeoJSON/Shapefiles for spatial topology, RESTful JSON APIs for live feeds.
- **Authority:** Data provided by Institutional Partners will be assigned Tier-2 or Tier-3 Source Authority depending on the verification protocols enforced by the partner.
