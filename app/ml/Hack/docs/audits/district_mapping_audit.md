# SafeShe — District Mapping Audit Report

**Generated:** 2026-07-31
**Auditor:** Antigravity AI
**Scope:** All crime datasets under `ml/datasets/raw/crime/`
**Method:** Read-only inspection — no data was modified

---

## 1. Dataset Overview

Five files exist under `ml/datasets/raw/crime/`:

| # | Filename | Size | Has District Column | Unit of Observation |
|---|---|---|---|---|
| D1 | `tamil_nadu_crime_stats_2014_2024.csv` | 1,013 B | ❌ No | State-level yearly aggregate (Tamil Nadu) |
| D2 | `7c1dfb74-70a9-45a3-939b-1f5bf949c10a.csv` | 3,915 B | ✅ Yes (`District`) | District-level complaint volumes |
| D3 | `tn_2023_crimes_against_women.csv` | 6,445 B | ✅ Yes (`Districts/City`) | District-level crimes against women |
| D4 | `NCRB_CII_2023_Table_5A.4A_0.csv` | 5,815 B | ❌ No | All-India crime category × age group |
| D5 | `NCRB_CII_2023_Table_5A.4B_0.csv` | 7,441 B | ❌ No | All-India SLL crime × age group |

**Datasets with geographically meaningful district data: D2 and D3 only.**

D1 is a single time-series with no district breakdown.
D4 and D5 are structured by crime category, not by geography — they are all-India national-level tables.

---

## 2. District Verification

### 2.1 D1 — `tamil_nadu_crime_stats_2014_2024.csv`

- **District column:** NONE
- **Unique districts:** 0
- **Note:** This dataset contains 11 rows (one per year, 2014–2024) of Tamil Nadu state-level crime totals. It has no geographic dimension below the state level. It cannot contribute district records.

---

### 2.2 D2 — `7c1dfb74-70a9-45a3-939b-1f5bf949c10a.csv` (District Complaint Reports)

- **District column:** `District`
- **Total rows (data):** 47
- **Aggregate rows:** 1 (`TOTAL`)
- **Unique district values:** 47

All values extracted from D2:

| Sl. No | Raw Value |
|---|---|
| 1 | Ariyalur |
| 2 | Chennai |
| 3 | Coimbatore |
| 4 | Coimbatore  City *(double space)* |
| 5 | Cuddalore |
| 6 | Dharmapuri |
| 7 | Dindigul |
| 8 | Erode |
| 9 | Kanchipuram |
| 10 | Kanyakumari |
| 11 | Karur |
| 12 | Krishnagiri |
| 13 | Madurai |
| 14 | Madurai City |
| 15 | Nagapattinam |
| 16 | Namakkal |
| 17 | Nilgiris |
| 18 | Perambalur |
| 19 | Pudukottai |
| 20 | Ramnathapuram |
| 21 | Railway Chennai |
| 22 | Railway Trichy |
| 23 | Salem |
| 24 | Salem City |
| 25 | Sivagangai |
| 26 | Thanjavur |
| 27 | Theni |
| 28 | Thirunelveli |
| 29 | Thirunelveli City |
| 30 | Thiruvallur |
| 31 | Thiruvannamalai |
| 32 | Thiruvarur |
| 33 | Thoothukudi |
| 34 | Tiruppur |
| 35 | Tiruppur City |
| 36 | Trichy |
| 37 | Trichy City |
| 38 | Vellore |
| 39 | Villupuram |
| 40 | Virudhunagar |
| 41 | Cyber Cell |
| 42 | Other Units |
| 43 | Chengalpattu |
| 44 | Kallakurichi |
| 45 | Ranipet |
| 46 | Tiruppattur |
| 47 | Tenkasi |

---

### 2.3 D3 — `tn_2023_crimes_against_women.csv` (TN Women Crime 2023)

- **District column:** `Districts/City`
- **Total rows (data):** 50
- **Aggregate rows:** 1 (`TOTAL DISTRICT(S)`)
- **Unique district values:** 50

All values extracted from D3:

| Sl. No | Raw Value |
|---|---|
| 1 | Ariyalur |
| 2 | Chennai |
| 3 | Coimbatore |
| 4 | Coimbatore City |
| 5 | Cuddalore |
| 6 | Dharmapuri |
| 7 | Dindigul |
| 8 | Erode |
| 9 | Kanchipuram |
| 10 | Kanyakumari |
| 11 | Karur |
| 12 | Krishnagiri |
| 13 | Madurai |
| 14 | Madurai City |
| 15 | Nagapattinam |
| 16 | Namakkal |
| 17 | Nilgiris |
| 18 | Perambalur |
| 19 | Pudukottai |
| 20 | Ramnathapuram |
| 21 | Railway Chennai |
| 22 | Railway Trichy |
| 23 | Salem |
| 24 | Salem City |
| 25 | Sivagangai |
| 26 | Thanjavur |
| 27 | Theni |
| 28 | Thirunelveli |
| 29 | Thirunelveli City |
| 30 | Thiruvallur |
| 31 | Thiruvannamalai |
| 32 | Thiruvarur |
| 33 | Thoothukudi |
| 34 | Tiruppur |
| 35 | Tiruppur City |
| 36 | Trichy |
| 37 | Trichy City |
| 38 | Vellore |
| 39 | Villupuram |
| 40 | Virudhunagar |
| 41 | Cyber Cell |
| 42 | Other Units |
| 43 | Chengalpattu |
| 44 | Kallakurichi |
| 45 | Ranipet |
| 46 | Tiruppattur |
| 47 | Tenkasi |
| 48 | Mayiladuthurai |
| 49 | Avadi |
| 50 | Tambaram |

---

### 2.4 D4 — `NCRB_CII_2023_Table_5A.4A_0.csv`

- **District column:** NONE
- **Unique districts:** 0
- **Note:** 62 rows of IPC crime categories broken down by juvenile offender age groups. The entire table represents all-India totals. There is no geographic granularity. No district records can be extracted.

---

### 2.5 D5 — `NCRB_CII_2023_Table_5A.4B_0.csv`

- **District column:** NONE
- **Unique districts:** 0
- **Note:** 82 rows of Special and Local Law (SLL) crime categories broken down by juvenile offender age groups. Same structure as D4 — all-India, no geographic dimension.

---

### 2.6 District Summary Table

| Dataset | District Column | Data Rows | Non-geographic Rows | Geographic Rows |
|---|---|---|---|---|
| D1 | NONE | 11 (years) | 11 | 0 |
| D2 | `District` | 47 + 1 total | 3 (Railway ×2, Cyber Cell, Other Units) | 43 |
| D3 | `Districts/City` | 50 + 1 total | 5 (Railway ×2, Cyber Cell, Other Units, _Avadi_, _Tambaram_*) | 45 or 47 |
| D4 | NONE | 62 (crime categories) | 62 | 0 |
| D5 | NONE | 82 (crime categories) | 82 | 0 |

*Avadi and Tambaram are Police Commissionerates, not revenue districts — see Section 3.

---

## 3. Canonical District Mapping

### 3.1 Background: Tamil Nadu's District Structure

Tamil Nadu has **38 official revenue districts** as of 2024. Tamil Nadu Police additionally reports crime data through **Police Commissionerates** (urban city police units) and **Railway Police** units. NCRB Crime in India tables mix both revenue districts and commissionerates in the same column, which is the source of most naming complexity in these datasets.

**Key distinction:**
- A **revenue district** (e.g., Coimbatore) is administered by a District Collector and corresponds to official Census geography.
- A **police commissionerate** (e.g., Coimbatore City) is a separate police jurisdiction covering the urban core of the same named city, administered by a Commissioner of Police.
- They are **not duplicates** — they represent overlapping but distinct geographic and institutional units.

---

### 3.2 Canonical Mapping Table

The table below maps every raw district-like value found in D2 and D3 to its canonical form, with classification and rationale.

| Raw Value (D2/D3) | Canonical Name | Record Type | Canonical Spelling Basis | Rationale |
|---|---|---|---|---|
| Ariyalur | Ariyalur | Revenue District | Official | Matches official GoTN name |
| Chennai | Chennai | Revenue District | Official | Matches official GoTN name |
| Coimbatore | Coimbatore | Revenue District | Official | Matches official GoTN name |
| Coimbatore  City *(D2 — double space)* | Coimbatore City | Police Commissionerate | Corrected | Whitespace typo; same entity as D3 "Coimbatore City" |
| Coimbatore City *(D3)* | Coimbatore City | Police Commissionerate | Official | City police jurisdiction separate from Coimbatore District |
| Cuddalore | Cuddalore | Revenue District | Official | Matches official GoTN name |
| Dharmapuri | Dharmapuri | Revenue District | Official | Matches official GoTN name |
| Dindigul | Dindigul | Revenue District | Official | Matches official GoTN name |
| Erode | Erode | Revenue District | Official | Matches official GoTN name |
| Kanchipuram | Kancheepuram | Revenue District | Corrected | Official GoTN/TNPSC spelling is "Kancheepuram"; "Kanchipuram" is a common variant; canonical = "Kancheepuram" |
| Kanyakumari | Kanniyakumari | Revenue District | Corrected | Official GoTN/Census spelling is "Kanniyakumari"; "Kanyakumari" is a widely used colloquial variant |
| Karur | Karur | Revenue District | Official | Matches official GoTN name |
| Krishnagiri | Krishnagiri | Revenue District | Official | Matches official GoTN name |
| Madurai | Madurai | Revenue District | Official | Matches official GoTN name |
| Madurai City | Madurai City | Police Commissionerate | Official | Separate commissionerate for Madurai urban core |
| Nagapattinam | Nagapattinam | Revenue District | Official | Matches official GoTN name |
| Namakkal | Namakkal | Revenue District | Official | Matches official GoTN name |
| Nilgiris | The Nilgiris | Revenue District | Corrected | Official GoTN name includes the article "The"; "Nilgiris" is the truncated form |
| Perambalur | Perambalur | Revenue District | Official | Matches official GoTN name |
| Pudukottai | Pudukkottai | Revenue District | Corrected | Official GoTN/Census spelling is "Pudukkottai"; "Pudukottai" is a phonetic approximation |
| Ramnathapuram | Ramanathapuram | Revenue District | Corrected | Official GoTN/Census spelling is "Ramanathapuram"; "Ramnathapuram" drops a syllable |
| Railway Chennai | Railway Chennai | Railway Police Unit | — | Not a revenue district; Southern Railway/Chennai Division police reporting unit |
| Railway Trichy | Railway Trichy | Railway Police Unit | — | Not a revenue district; Southern Railway/Trichy Division police reporting unit |
| Salem | Salem | Revenue District | Official | Matches official GoTN name |
| Salem City | Salem City | Police Commissionerate | Official | Separate city commissionerate |
| Sivagangai | Sivaganga | Revenue District | Corrected | Official GoTN name is "Sivaganga"; "Sivagangai" is the colloquial form |
| Thanjavur | Thanjavur | Revenue District | Official | Matches official GoTN name |
| Theni | Theni | Revenue District | Official | Matches official GoTN name |
| Thirunelveli | Tirunelveli | Revenue District | Corrected | Official GoTN/Census spelling is "Tirunelveli"; "Thirunelveli" is an alternate transliteration |
| Thirunelveli City | Tirunelveli City | Police Commissionerate | Corrected | Commissionerate counterpart; corrected to match district spelling |
| Thiruvallur | Tiruvallur | Revenue District | Corrected | Official GoTN/Census spelling is "Tiruvallur"; "Thiruvallur" is alternate transliteration |
| Thiruvannamalai | Tiruvannamalai | Revenue District | Corrected | Official GoTN/Census spelling is "Tiruvannamalai" |
| Thiruvarur | Tiruvarur | Revenue District | Corrected | Official GoTN/Census spelling is "Tiruvarur" |
| Thoothukudi | Thoothukudi | Revenue District | Official | Matches official GoTN name (also known as Tuticorin) |
| Tiruppur | Tiruppur | Revenue District | Official | Matches official GoTN name |
| Tiruppur City | Tiruppur City | Police Commissionerate | Official | Separate city commissionerate |
| Trichy | Tiruchirappalli | Revenue District | Corrected | "Trichy" is the informal abbreviation; official GoTN/Census name is "Tiruchirappalli" |
| Trichy City | Tiruchirappalli City | Police Commissionerate | Corrected | Commissionerate counterpart; official name uses full spelling |
| Vellore | Vellore | Revenue District | Official | Matches official GoTN name |
| Villupuram | Viluppuram | Revenue District | Corrected | Official GoTN/Census spelling is "Viluppuram"; "Villupuram" is a common variant |
| Virudhunagar | Virudhunagar | Revenue District | Official | Matches official GoTN name |
| Cyber Cell | Cyber Cell | Special Unit | — | Not a geographic unit; a functional cyber crime reporting cell |
| Other Units | Other Units | Aggregate Catch-all | — | Not a geographic unit; administrative remainder |
| Chengalpattu | Chengalpattu | Revenue District (New) | Official | Created 2019 by bifurcating Kancheepuram |
| Kallakurichi | Kallakurichi | Revenue District (New) | Official | Created 2019 by bifurcating Villupuram |
| Ranipet | Ranipet | Revenue District (New) | Official | Created 2019 by trifurcating Vellore |
| Tiruppattur | Tirupattur | Revenue District (New) | Corrected | Official GoTN name is "Tirupattur" (one 'p'); "Tiruppattur" has double 'p' — phonetic variant |
| Tenkasi | Tenkasi | Revenue District (New) | Official | Created 2019 by bifurcating Tirunelveli |
| Mayiladuthurai | Mayiladuthurai | Revenue District (New) | Official | Created Dec 2020 by bifurcating Nagapattinam; TN's 38th district |
| Avadi | Avadi | Police Commissionerate | — | Not a revenue district; police commissionerate carved from Greater Chennai / Tiruvallur areas |
| Tambaram | Tambaram | Police Commissionerate | — | Not a revenue district; police commissionerate covering areas in Chengalpattu / Chennai suburbs |

---

### 3.3 Spelling Variant Summary

The following 12 district names appear in datasets with non-standard spellings that must be corrected before any merge or model training:

| Raw Spelling | Canonical Spelling | Datasets Affected | Error Type |
|---|---|---|---|
| Coimbatore  City | Coimbatore City | D2 only | Double space (whitespace typo) |
| Kanchipuram | Kancheepuram | D2, D3 | Simplified/colloquial transliteration |
| Kanyakumari | Kanniyakumari | D2, D3 | Simplified/colloquial transliteration |
| Nilgiris | The Nilgiris | D2, D3 | Missing article |
| Pudukottai | Pudukkottai | D2, D3 | Missing double consonant |
| Ramnathapuram | Ramanathapuram | D2, D3 | Dropped syllable |
| Sivagangai | Sivaganga | D2, D3 | Extra suffix |
| Thirunelveli | Tirunelveli | D2, D3 | Alternative transliteration |
| Thiruvallur | Tiruvallur | D2, D3 | Alternative transliteration |
| Thiruvannamalai | Tiruvannamalai | D2, D3 | Alternative transliteration |
| Thiruvarur | Tiruvarur | D2, D3 | Alternative transliteration |
| Trichy | Tiruchirappalli | D2, D3 | Informal abbreviation |
| Trichy City | Tiruchirappalli City | D2, D3 | Informal abbreviation |
| Tiruppattur | Tirupattur | D2, D3 | Extra consonant variant |
| Villupuram | Viluppuram | D2, D3 | Alternative spelling |

---

## 4. Invalid Geographic Records

The following rows appear in D2 and D3 but should **not** be used as district-level training samples for ML models. They represent non-geographic or special reporting units.

### 4.1 Classification of Non-Geographic Rows

| Raw Name | Present In | Record Type | Disposition | Reason |
|---|---|---|---|---|
| TOTAL | D2 | State aggregate | **Remove** from training | Sum row — not a location |
| TOTAL DISTRICT(S) | D3 | State aggregate | **Remove** from training | Sum row — not a location |
| Cyber Cell | D2, D3 | Functional unit | **Store separately** | A cyber crime reporting cell, not a geographic area; may be useful for cyber crime signal analysis but cannot be spatially joined |
| Other Units | D2, D3 | Administrative catch-all | **Remove** from training | No geographic identity; remainder bucket for unclassified complaints |
| Railway Chennai | D2, D3 | Railway Police unit | **Store separately** | Southern Railway Chennai Division police; covers rail stations across multiple districts; no unique centroid |
| Railway Trichy | D2, D3 | Railway Police unit | **Store separately** | Southern Railway Trichy Division police; same reasoning as above |
| Avadi | D3 only | Police Commissionerate | **Store separately** | Urban commissionerate, not a revenue district; spans portions of Tiruvallur and former Kancheepuram; no stable single centroid |
| Tambaram | D3 only | Police Commissionerate | **Store separately** | Urban commissionerate, not a revenue district; covers southern Chennai suburbs across Chengalpattu |

### 4.2 Disposition Rationale

**Remove (drop):**
- `TOTAL`, `TOTAL DISTRICT(S)`, `Other Units` — these are administrative artifacts with no geographic identity and contain only aggregated or residual values.

**Store separately (do not merge into district training data; preserve for analysis):**
- `Cyber Cell` — useful as a total-state cyber crime indicator; not spatial.
- `Railway Chennai` and `Railway Trichy` — the data is real and geographically meaningful at the station level, but the station network spans multiple districts. Preserving these allows future rail-corridor analysis if station locations are added.
- `Avadi` and `Tambaram` — these are real commissionerates with genuine crime counts. They overlap revenue district boundaries. Preserving them enables future disaggregation once boundary shapefiles are available.

---

## 5. Merge Validation

### 5.1 Cross-Dataset District Comparison (D2 vs D3)

Using exact case-insensitive string matching after stripping whitespace:

**Districts present in D2 but NOT in D3 (1 record):**

| Raw Value (D2) | Issue |
|---|---|
| `Coimbatore  City` | Double space — does not match D3's `Coimbatore City`. Same unit, different string. |

**Districts present in D3 but NOT in D2 (3 records):**

| Raw Value (D3) | Issue |
|---|---|
| `Mayiladuthurai` | D3 includes this as TN's newest district (Dec 2020). D2 predates or omits it. |
| `Avadi` | D3 includes Avadi Commissionerate. D2 does not. |
| `Tambaram` | D3 includes Tambaram Commissionerate. D2 does not. |

**Districts present in both (after exact match): 46 values**

All 46 shared values match exactly (case-insensitively, single-space normalized) between D2 and D3, with the single exception of the `Coimbatore  City` double-space issue.

### 5.2 Known Merge Conflicts

| Conflict | Root Cause | Impact |
|---|---|---|
| `Coimbatore  City` (D2) vs `Coimbatore City` (D3) | Extra whitespace in D2 | Join will fail if using raw string equality; deduplicated after strip() |
| `Mayiladuthurai` absent from D2 | D2 was compiled before Mayiladuthurai was formally established as a district | D3 rows for Mayiladuthurai cannot be joined to D2 data |
| `Avadi` absent from D2 | D2 does not include Avadi Commissionerate | No D2 counterpart for D3 Avadi rows |
| `Tambaram` absent from D2 | D2 does not include Tambaram Commissionerate | No D2 counterpart for D3 Tambaram rows |
| `Kanchipuram` vs `Kancheepuram` (canonical) | Transliteration variant | If any future dataset uses canonical spelling, these will not match |
| All `Thi-` prefix variants | Alternative transliteration convention across sources | Any new dataset using `Tiru-` prefix will not match existing rows |
| `Trichy` vs `Tiruchirappalli` | Abbreviation vs official name | Future NCRB/Census data will use full name; current data uses abbreviation |

### 5.3 D1 Merge Assessment

D1 (`tamil_nadu_crime_stats_2014_2024.csv`) has no district column and cannot be joined to D2 or D3 by geography. Its data (state-level rates from 2014–2024) can only be joined by **year** to produce a TN-wide crime rate signal.

### 5.4 D4 and D5 Merge Assessment

D4 and D5 have no district column. They represent all-India national totals. They **cannot be merged** with D2 or D3 on any geographic key. They could only be used as national-level crime-category reference values.

---

## 6. Geographic Recommendation

### 6.1 Recommended Canonical District Set

The project should adopt the following canonical universe of **38 revenue districts** as the authoritative geographic reference, aligned with the Government of Tamil Nadu's official district list (2024):

```
1.  Ariyalur
2.  Chengalpattu         ← New (2019), bifurcated from Kancheepuram
3.  Chennai
4.  Coimbatore
5.  Cuddalore
6.  Dharmapuri
7.  Dindigul
8.  Erode
9.  Kallakurichi          ← New (2019), bifurcated from Viluppuram
10. Kancheepuram         ← Canonical spelling (not "Kanchipuram")
11. Kanniyakumari        ← Canonical spelling (not "Kanyakumari")
12. Karur
13. Krishnagiri
14. Madurai
15. Mayiladuthurai        ← New (Dec 2020), bifurcated from Nagapattinam
16. Nagapattinam
17. Namakkal
18. Perambalur
19. Pudukkottai          ← Canonical spelling (not "Pudukottai")
20. Ramanathapuram       ← Canonical spelling (not "Ramnathapuram")
21. Ranipet               ← New (2019), trifurcated from Vellore
22. Salem
23. Sivaganga            ← Canonical spelling (not "Sivagangai")
24. Tenkasi               ← New (2019), bifurcated from Tirunelveli
25. Thanjavur
26. Theni
27. The Nilgiris          ← Canonical name (not "Nilgiris")
28. Thoothukudi
29. Tiruchirappalli       ← Canonical spelling (not "Trichy")
30. Tirunelveli           ← Canonical spelling (not "Thirunelveli")
31. Tirupattur            ← New (2019), trifurcated from Vellore; one 'p'
32. Tiruppur
33. Tiruvallur            ← Canonical spelling (not "Thiruvallur")
34. Tiruvannamalai        ← Canonical spelling (not "Thiruvannamalai")
35. Tiruvarur             ← Canonical spelling (not "Thiruvarur")
36. Vellore
37. Viluppuram            ← Canonical spelling (not "Villupuram")
38. Virudhunagar
```

### 6.2 Recommended Treatment for Non-Revenue-District Rows

| Entity | Recommended Treatment |
|---|---|
| Coimbatore City | Keep in a separate `commissionerates` table; do not merge into district table |
| Madurai City | Keep in a separate `commissionerates` table |
| Salem City | Keep in a separate `commissionerates` table |
| Tirunelveli City | Keep in a separate `commissionerates` table |
| Tiruchirappalli City | Keep in a separate `commissionerates` table (raw: "Trichy City") |
| Tiruppur City | Keep in a separate `commissionerates` table |
| Avadi | Keep in a separate `commissionerates` table |
| Tambaram | Keep in a separate `commissionerates` table |
| Railway Chennai | Keep in a separate `railway_police` table |
| Railway Trichy | Keep in a separate `railway_police` table |
| Cyber Cell | Keep as a state-level functional unit record |
| Other Units | Discard — no geographic or analytical value |
| TOTAL / TOTAL DISTRICT(S) | Discard — aggregate artifact |

### 6.3 Recommended Normalisation Rules for the Crime Loader

The following normalisation rules should be applied (in order) by the Crime Loader before any district name is emitted:

1. **Strip** all leading and trailing whitespace.
2. **Collapse** all internal runs of multiple spaces to a single space.
3. **Apply Unicode NFKC** normalization.
4. **Apply spelling corrections** from the canonical mapping table (Section 3.2).
5. **Classify** the result as one of: `revenue_district`, `commissionerate`, `railway_police`, `special_unit`, `aggregate_total`.
6. **Emit** only `revenue_district` rows to the main crime_score output.
7. **Emit** `commissionerate` rows to a separate commissionerates table.
8. **Emit** `railway_police` rows to a separate railway_police table.
9. **Discard** `special_unit` and `aggregate_total` rows.

### 6.4 District Coverage Gap

The current datasets cover **47 distinct raw district-like values** across D2 and D3. After removing non-geographic entries and correcting spellings, **37 of the 38 canonical revenue districts** are covered.

**Missing district: `Tirupattur`** (officially created 2019 from Vellore trifurcation) — this district appears as `Tiruppattur` in both D2 and D3. After canonical spelling correction, it resolves to `Tirupattur`. However, the data prior to 2019 for this area would still fall under `Vellore`.

**Missing district: `Mayiladuthurai`** — present in D3 only (not in D2). D2 appears to predate or exclude this district's establishment (December 2020).

---

## 7. Summary Statistics

| Metric | Value |
|---|---|
| Total datasets inspected | 5 |
| Datasets with geographic district data | 2 (D2, D3) |
| Total raw district-like values (D2) | 47 |
| Total raw district-like values (D3) | 50 |
| Unique combined district-like values | 50 |
| Canonical revenue districts covered | 37 of 38 |
| Police Commissionerates | 8 |
| Railway Police Units | 2 |
| Special/Functional Units | 1 (Cyber Cell) |
| Aggregate/Total Rows | 2 (TOTAL, TOTAL DISTRICT(S)) |
| Administrative Catch-alls | 1 (Other Units) |
| Spelling variants requiring correction | 15 |
| Merge conflicts between D2 and D3 | 4 (whitespace + 3 absent entries) |

---

*End of district mapping audit. No datasets were modified.*
*Reference the companion canonical mapping at `docs/data/canonical_district_mapping.md`.*
