# SafeShe Data Partnership Tracker

This tracker monitors the status of formal requests for authorized external data. Speculative or unauthorized sources must not be placed into the production registry until they reach `APPROVED` and `ACTIVE` status here.

| Partner | Organization | Data Requested | Contact Status | Request Date | Response Status | Authorization Status | Dataset Status | Next Action | Owner |
|---------|--------------|----------------|----------------|--------------|-----------------|----------------------|----------------|-------------|-------|
| MTC Chennai | Metropolitan Transport Corporation | Bus Network GTFS (Static & RT) | NOT_CONTACTED | TBD | AWAITING_RESPONSE | PENDING | UNAVAILABLE | Dispatch Request Package | Data Ops |
| GCC | Greater Chennai Corporation | Infrastructure / Topology geo-data | NOT_CONTACTED | TBD | AWAITING_RESPONSE | PENDING | UNAVAILABLE | Define required geo-bounds | Data Ops |
| TN Police | Tamil Nadu Police (SCRB) | Aggregated Crime/Safety Indicators | NOT_CONTACTED | TBD | AWAITING_RESPONSE | PENDING | UNAVAILABLE | Dispatch Privacy/Safety Req | Data Ops |
| ITDP India | Institute for Transportation & Dev Policy | Transit & Pedestrian Network topology | NOT_CONTACTED | TBD | AWAITING_RESPONSE | PENDING | UNAVAILABLE | Outreach | Data Ops |
| IMD | Indian Meteorological Dept | Severe Weather & Flood Alerts | NOT_CONTACTED | TBD | AWAITING_RESPONSE | PENDING | UNAVAILABLE | Review API specs | Data Ops |

## Allowed Status Values
- **Contact Status:** NOT_CONTACTED, CONTACTED
- **Response Status:** AWAITING_RESPONSE, DATA_REVIEW, LEGAL_REVIEW
- **Authorization Status:** PENDING, APPROVED, REJECTED, EXPIRED
- **Dataset Status:** UNAVAILABLE, RAW_INGESTED, VALIDATED, NORMALIZED, ACTIVE
