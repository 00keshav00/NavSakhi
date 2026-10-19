# SafeShe Canonical District Mapping

**Version:** 1.0.0
**Effective Date:** 2026-07-31
**Authority:** Based on Government of Tamil Nadu official district list (38 districts, 2024) and Tamil Nadu Police administrative structure.
**Status:** Recommended — not yet implemented in code.

> This document is the **single source of truth** for how district names from crime datasets should be normalized before any merge, join, or model training operation.

---

## Section 1 — Revenue Districts (38 Canonical Districts)

These are the 38 official revenue districts of Tamil Nadu. Only rows that resolve to one of these canonical names should be used as district-level ML training samples.

| Canonical Name | Raw Names Found in Datasets | District Type | Year Created | Parent District(s) |
|---|---|---|---|---|
| Ariyalur | Ariyalur | Original | Pre-2004 reorganization | — |
| Chengalpattu | Chengalpattu | New (2019) | 2019 | Kancheepuram |
| Chennai | Chennai | Original | Historic | — |
| Coimbatore | Coimbatore | Original | Historic | — |
| Cuddalore | Cuddalore | Original | Historic | — |
| Dharmapuri | Dharmapuri | Original | Historic | — |
| Dindigul | Dindigul | Original | Historic | — |
| Erode | Erode | Original | Historic | — |
| Kallakurichi | Kallakurichi | New (2019) | 2019 | Viluppuram |
| Kancheepuram | Kanchipuram | Original | Historic | — |
| Kanniyakumari | Kanyakumari | Original | Historic | — |
| Karur | Karur | Original | Historic | — |
| Krishnagiri | Krishnagiri | Original | Historic | — |
| Madurai | Madurai | Original | Historic | — |
| Mayiladuthurai | Mayiladuthurai | New (2020) | Dec 2020 | Nagapattinam |
| Nagapattinam | Nagapattinam | Original | Historic | — |
| Namakkal | Namakkal | Original | Historic | — |
| Perambalur | Perambalur | Original | Historic | — |
| Pudukkottai | Pudukottai | Original | Historic | — |
| Ramanathapuram | Ramnathapuram | Original | Historic | — |
| Ranipet | Ranipet | New (2019) | 2019 | Vellore |
| Salem | Salem | Original | Historic | — |
| Sivaganga | Sivagangai | Original | Historic | — |
| Tenkasi | Tenkasi | New (2019) | 2019 | Tirunelveli |
| Thanjavur | Thanjavur | Original | Historic | — |
| Theni | Theni | Original | Historic | — |
| The Nilgiris | Nilgiris | Original | Historic | — |
| Thoothukudi | Thoothukudi | Original | Historic | — |
| Tiruchirappalli | Trichy | Original | Historic | — |
| Tirunelveli | Thirunelveli | Original | Historic | — |
| Tirupattur | Tiruppattur | New (2019) | 2019 | Vellore |
| Tiruppur | Tiruppur | Original | Historic | — |
| Tiruvallur | Thiruvallur | Original | Historic | — |
| Tiruvannamalai | Thiruvannamalai | Original | Historic | — |
| Tiruvarur | Thiruvarur | Original | Historic | — |
| Vellore | Vellore | Original | Historic | — |
| Viluppuram | Villupuram | Original | Historic | — |
| Virudhunagar | Virudhunagar | Original | Historic | — |

---

## Section 2 — Police Commissionerates

These are police jurisdictions that cover the urban cores of major Tamil Nadu cities. They are reported separately from the surrounding revenue district in NCRB data.

**Key rule:** Commissionerate rows must NOT be merged with their parent revenue district rows. They must be stored in a separate table and handled explicitly.

| Canonical Commissionerate Name | Raw Names Found in Datasets | Approximate Geographic Coverage | Parent Revenue District |
|---|---|---|---|
| Coimbatore City | Coimbatore City; Coimbatore  City *(double space — D2 typo)* | Urban Coimbatore | Coimbatore |
| Madurai City | Madurai City | Urban Madurai | Madurai |
| Salem City | Salem City | Urban Salem | Salem |
| Tirunelveli City | Thirunelveli City | Urban Tirunelveli | Tirunelveli |
| Tiruchirappalli City | Trichy City | Urban Tiruchirappalli | Tiruchirappalli |
| Tiruppur City | Tiruppur City | Urban Tiruppur | Tiruppur |
| Avadi | Avadi | Northern Chennai suburbs (parts of Tiruvallur) | Tiruvallur / Chennai |
| Tambaram | Tambaram | Southern Chennai suburbs | Chengalpattu / Chennai |

**Note on Avadi and Tambaram:** These two commissionerates were established to cover rapidly urbanising areas adjacent to Chennai. They do not correspond to any revenue district boundary. Their crime data in D3 cannot be spatially assigned to a single revenue district without boundary shapefiles.

---

## Section 3 — Railway Police Units

Railway Police report crime statistics that cover offences occurring on railway premises across multiple geographic districts. Their data cannot be spatially joined to a single revenue district centroid.

| Canonical Name | Raw Names Found in Datasets | Coverage |
|---|---|---|
| Railway Chennai | Railway Chennai | Chennai division of Southern Railway — multiple districts |
| Railway Trichy | Railway Trichy | Tiruchirappalli division of Southern Railway — multiple districts |

**Recommended treatment:** Store in a separate `railway_police` table. May be used as a supplementary safety signal for route segments that pass through railway stations, once station-level geocoordinates are added.

---

## Section 4 — Special / Functional Units

These appear in the datasets as district-like rows but represent functional reporting cells rather than geographic units.

| Raw Name | Classification | Action |
|---|---|---|
| Cyber Cell | Functional unit (cyber crime reporting cell) | Store separately as a state-level cyber crime indicator; do not use for spatial features |

---

## Section 5 — Aggregate / Total Rows

These rows must be removed before any ML processing.

| Raw Name | Dataset | Action |
|---|---|---|
| TOTAL | D2 | Remove — sum row |
| TOTAL DISTRICT(S) | D3 | Remove — sum row |
| Other Units | D2, D3 | Remove — administrative remainder with no geographic identity |

---

## Section 6 — Normalisation Rules (Implementation Reference)

The following rules must be applied in order by the Crime Loader (or any future data loading component) before a district name is emitted:

```
Step 1: Unicode NFKC normalization
Step 2: Strip leading and trailing whitespace
Step 3: Collapse internal multiple spaces to single space
Step 4: Apply canonical spelling map (Section 6.1 below)
Step 5: Classify using record type map (Section 6.2 below)
Step 6: Route to appropriate output based on classification
```

### Section 6.1 — Spelling Correction Map

```python
SPELLING_CORRECTIONS = {
    "Kanchipuram":     "Kancheepuram",
    "Kanyakumari":     "Kanniyakumari",
    "Nilgiris":        "The Nilgiris",
    "Pudukottai":      "Pudukkottai",
    "Ramnathapuram":   "Ramanathapuram",
    "Sivagangai":      "Sivaganga",
    "Thirunelveli":    "Tirunelveli",
    "Thiruvallur":     "Tiruvallur",
    "Thiruvannamalai": "Tiruvannamalai",
    "Thiruvarur":      "Tiruvarur",
    "Trichy":          "Tiruchirappalli",
    "Trichy City":     "Tiruchirappalli City",
    "Villupuram":      "Viluppuram",
    "Tiruppattur":     "Tirupattur",
    "Thirunelveli City": "Tirunelveli City",
    # Whitespace-only fix (already handled by Step 3):
    # "Coimbatore  City" -> "Coimbatore City"
}
```

### Section 6.2 — Record Type Classification Map

```python
RECORD_TYPE = {
    # Revenue Districts (38)
    "Ariyalur":          "revenue_district",
    "Chengalpattu":      "revenue_district",
    "Chennai":           "revenue_district",
    "Coimbatore":        "revenue_district",
    "Cuddalore":         "revenue_district",
    "Dharmapuri":        "revenue_district",
    "Dindigul":          "revenue_district",
    "Erode":             "revenue_district",
    "Kallakurichi":      "revenue_district",
    "Kancheepuram":      "revenue_district",
    "Kanniyakumari":     "revenue_district",
    "Karur":             "revenue_district",
    "Krishnagiri":       "revenue_district",
    "Madurai":           "revenue_district",
    "Mayiladuthurai":    "revenue_district",
    "Nagapattinam":      "revenue_district",
    "Namakkal":          "revenue_district",
    "Perambalur":        "revenue_district",
    "Pudukkottai":       "revenue_district",
    "Ramanathapuram":    "revenue_district",
    "Ranipet":           "revenue_district",
    "Salem":             "revenue_district",
    "Sivaganga":         "revenue_district",
    "Tenkasi":           "revenue_district",
    "Thanjavur":         "revenue_district",
    "Theni":             "revenue_district",
    "The Nilgiris":      "revenue_district",
    "Thoothukudi":       "revenue_district",
    "Tiruchirappalli":   "revenue_district",
    "Tirunelveli":       "revenue_district",
    "Tirupattur":        "revenue_district",
    "Tiruppur":          "revenue_district",
    "Tiruvallur":        "revenue_district",
    "Tiruvannamalai":    "revenue_district",
    "Tiruvarur":         "revenue_district",
    "Vellore":           "revenue_district",
    "Viluppuram":        "revenue_district",
    "Virudhunagar":      "revenue_district",
    # Police Commissionerates
    "Coimbatore City":       "commissionerate",
    "Madurai City":          "commissionerate",
    "Salem City":            "commissionerate",
    "Tirunelveli City":      "commissionerate",
    "Tiruchirappalli City":  "commissionerate",
    "Tiruppur City":         "commissionerate",
    "Avadi":                 "commissionerate",
    "Tambaram":              "commissionerate",
    # Railway Police
    "Railway Chennai":       "railway_police",
    "Railway Trichy":        "railway_police",
    # Special / Functional Units
    "Cyber Cell":            "special_unit",
    # Aggregate Totals / Catch-alls
    "TOTAL":                 "aggregate_total",
    "TOTAL DISTRICT(S)":     "aggregate_total",
    "Other Units":           "aggregate_total",
}
```

### Section 6.3 — Output Routing

| Classification | Output Destination |
|---|---|
| `revenue_district` | `datasets/processed/crime_score.csv` — primary output |
| `commissionerate` | `datasets/processed/crime_score_commissionerates.csv` — separate table |
| `railway_police` | `datasets/processed/crime_score_railway.csv` — separate table |
| `special_unit` | `datasets/processed/crime_score_special_units.csv` — separate table |
| `aggregate_total` | Discarded — not written to any output |

---

## Section 7 — Coverage Notes for ML Pipeline

### Districts with incomplete historical coverage

The six new districts (Chengalpattu, Kallakurichi, Ranipet, Tirupattur, Tenkasi, Mayiladuthurai) were created between 2019 and 2020. Crime data prior to their creation is reported under their parent districts. The ML pipeline must be aware of this bifurcation history when assembling time-series crime features:

| New District | Parent | Created | Data Before Creation |
|---|---|---|---|
| Chengalpattu | Kancheepuram | 2019 | Reported under Kancheepuram |
| Kallakurichi | Viluppuram | 2019 | Reported under Viluppuram |
| Ranipet | Vellore | 2019 | Reported under Vellore |
| Tirupattur | Vellore | 2019 | Reported under Vellore |
| Tenkasi | Tirunelveli | 2019 | Reported under Tirunelveli |
| Mayiladuthurai | Nagapattinam | Dec 2020 | Reported under Nagapattinam |

### Districts missing from D2

`Mayiladuthurai` is present in D3 but absent from D2. The project should treat any D2 join on `Mayiladuthurai` as a null join until a newer version of D2 is available.

### Schema version

This canonical mapping is version `1.0.0`. It must be incremented in the dataset schema whenever:
- A new district is created by administrative bifurcation
- A new commissionerate is established by Tamil Nadu Police
- A spelling correction is revised based on authoritative government notification

---

*End of canonical district mapping. Do not modify datasets directly — apply these rules in the Crime Loader configuration.*
