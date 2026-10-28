# scripts/build_companion_stores.py
"""
NavSakhi Phase 46I - Companion Store Builder.

Generates deterministic, read-only SQLite companion stores from frozen Parquet files
using strictly bounded memory streaming batches (never materializes the full dataset).

Stores generated:
1. feature_store.db: Canonical ML predictor features indexed by segment_id.
2. road_segments_store.db: Road segments indexed by segment_id and (latitude, longitude).
"""

import argparse
import hashlib
import logging
import math
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pyarrow.parquet as pq
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ml.schemas import (
    CANONICAL_PREDICTOR_FEATURES,
    CATEGORICAL_FEATURES,
    NUMERICAL_FEATURES,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("build_companion_stores")

DEFAULT_MFT_PARQUET = PROJECT_ROOT / "app" / "ml" / "Hack" / "ml" / "datasets" / "processed" / "master_feature_table.parquet"
DEFAULT_RS_PARQUET = PROJECT_ROOT / "app" / "ml" / "Hack" / "ml" / "datasets" / "processed" / "road_segments.parquet"
DEFAULT_FEATURE_STORE_DB = PROJECT_ROOT / "app" / "ml" / "Hack" / "ml" / "datasets" / "processed" / "feature_store.db"
DEFAULT_ROAD_STORE_DB = PROJECT_ROOT / "app" / "ml" / "Hack" / "ml" / "datasets" / "processed" / "road_segments_store.db"

EXPECTED_MFT_SHA256 = "72557fcabb752709e1e8e7500da706179275d3173e30d9ce6da0e41c1a3433e5"
EXPECTED_RS_SHA256 = "ffee5ce98efda020cbcf7c6e280bd46b73e1d035fa29741a49941fdd2aaa8d8b"
EXPECTED_ROW_COUNT = 1042651


def verify_file_sha256(path: Path, expected_hash: str) -> bool:
    if not path.exists():
        logger.error(f"File not found: {path}")
        return False
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    actual = h.hexdigest()
    if actual != expected_hash:
        logger.error(f"SHA256 mismatch for {path}: expected {expected_hash}, got {actual}")
        return False
    return True


def build_feature_store(
    parquet_path: Path,
    db_path: Path,
    batch_size: int = 50000,
    overwrite: bool = False,
) -> bool:
    logger.info("--- Building Feature Store ---")
    logger.info(f"Source Parquet: {parquet_path}")
    logger.info(f"Target SQLite DB: {db_path}")

    if not parquet_path.exists():
        logger.error(f"Source Parquet missing: {parquet_path}")
        return False

    if db_path.exists() and not overwrite:
        logger.info(f"Target DB already exists: {db_path}. Verifying existing store...")
        return verify_feature_store(parquet_path, db_path)

    tmp_db_path = db_path.with_suffix(".db.tmp")
    if tmp_db_path.exists():
        tmp_db_path.unlink()

    cols = ["segment_id"] + CANONICAL_PREDICTOR_FEATURES

    conn = sqlite3.connect(str(tmp_db_path))
    c = conn.cursor()

    c.execute("PRAGMA page_size = 4096")
    c.execute("PRAGMA synchronous = OFF")
    c.execute("PRAGMA journal_mode = OFF")
    c.execute("PRAGMA cache_size = -64000")

    col_defs = ["segment_id TEXT PRIMARY KEY NOT NULL"]
    for feat in CANONICAL_PREDICTOR_FEATURES:
        col_type = "TEXT" if feat in CATEGORICAL_FEATURES else "REAL"
        col_defs.append(f'\"{feat}\" {col_type}')

    create_table_sql = f"CREATE TABLE canonical_features ({', '.join(col_defs)})"
    c.execute(create_table_sql)
    c.execute("CREATE VIEW IF NOT EXISTS features AS SELECT * FROM canonical_features")

    placeholders = ", ".join(["?"] * len(cols))
    insert_sql = f"INSERT INTO canonical_features VALUES ({placeholders})"

    pf = pq.ParquetFile(str(parquet_path))
    total_rows = 0
    t0 = time.perf_counter()

    for batch in pf.iter_batches(batch_size=batch_size, columns=cols):
        df_batch = batch.to_pandas()
        records = []
        for row in df_batch[cols].itertuples(index=False):
            rec = [str(row[0])]
            for i, feat in enumerate(CANONICAL_PREDICTOR_FEATURES, start=1):
                v = row[i]
                if feat in CATEGORICAL_FEATURES:
                    rec.append(str(v) if (v is not None and not (isinstance(v, float) and math.isnan(v))) else None)
                else:
                    rec.append(float(v) if (v is not None and not (isinstance(v, float) and math.isnan(v))) else None)
            records.append(rec)

        c.executemany(insert_sql, records)
        total_rows += len(records)
        del records, df_batch
        logger.info(f"Streamed {total_rows:,} / {EXPECTED_ROW_COUNT:,} feature rows...")

    conn.commit()

    logger.info("Optimizing and vacuuming feature store...")
    c.execute("PRAGMA journal_mode = DELETE")
    c.execute("PRAGMA synchronous = NORMAL")
    conn.commit()
    c.execute("VACUUM")
    c.execute("PRAGMA optimize")
    conn.close()

    elapsed = time.perf_counter() - t0
    logger.info(f"Feature store built in {elapsed:.2f}s ({total_rows:,} rows).")

    if db_path.exists():
        db_path.unlink()
    tmp_db_path.rename(db_path)

    return verify_feature_store(parquet_path, db_path)


def verify_feature_store(parquet_path: Path, db_path: Path) -> bool:
    logger.info("Verifying feature store integrity...")
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM canonical_features")
    row_count = c.fetchone()[0]
    if row_count != EXPECTED_ROW_COUNT:
        logger.error(f"Row count mismatch: expected {EXPECTED_ROW_COUNT}, got {row_count}")
        conn.close()
        return False

    c.execute("PRAGMA table_info(canonical_features)")
    table_cols = [r[1] for r in c.fetchall()]
    expected_cols = ["segment_id"] + CANONICAL_PREDICTOR_FEATURES
    if table_cols != expected_cols:
        logger.error("Column specification mismatch in canonical_features")
        conn.close()
        return False

    pf = pq.ParquetFile(str(parquet_path))
    sample_batch = next(pf.iter_batches(batch_size=50, columns=expected_cols))
    sample_df = sample_batch.to_pandas()
    sample_ids = sample_df["segment_id"].tolist()

    q_placeholders = ", ".join(["?"] * len(sample_ids))
    c.execute(f"SELECT * FROM canonical_features WHERE segment_id IN ({q_placeholders})", sample_ids)
    fetched = c.fetchall()
    fetched_dict = {r[0]: r[1:] for r in fetched}

    for _, row in sample_df.iterrows():
        sid = row["segment_id"]
        if sid not in fetched_dict:
            logger.error(f"Sample segment_id {sid} not found in database")
            conn.close()
            return False
        db_vals = fetched_dict[sid]
        for idx, col in enumerate(CANONICAL_PREDICTOR_FEATURES):
            pq_val = row[col]
            db_val = db_vals[idx]
            if col in CATEGORICAL_FEATURES:
                pq_norm = str(pq_val) if (pq_val is not None and not (isinstance(pq_val, float) and math.isnan(pq_val))) else None
                if pq_norm != db_val:
                    logger.error(f"Categorical mismatch at {sid}.{col}: pq={pq_norm}, db={db_val}")
                    conn.close()
                    return False
            else:
                pq_is_nan = pq_val is None or (isinstance(pq_val, float) and math.isnan(pq_val))
                db_is_nan = db_val is None
                if pq_is_nan != db_is_nan:
                    logger.error(f"Null status mismatch at {sid}.{col}: pq={pq_val}, db={db_val}")
                    conn.close()
                    return False
                if not pq_is_nan and abs(float(pq_val) - float(db_val)) > 1e-9:
                    logger.error(f"Value mismatch at {sid}.{col}: pq={pq_val}, db={db_val}")
                    conn.close()
                    return False

    conn.close()
    logger.info("Feature store verification PASSED: 1,042,651 rows verified with bit-for-bit parity.")
    return True


def build_road_segments_store(
    parquet_path: Path,
    db_path: Path,
    batch_size: int = 50000,
    overwrite: bool = False,
) -> bool:
    logger.info("--- Building Road Segments Spatial Store ---")
    logger.info(f"Source Parquet: {parquet_path}")
    logger.info(f"Target SQLite DB: {db_path}")

    if not parquet_path.exists():
        logger.error(f"Source Parquet missing: {parquet_path}")
        return False

    if db_path.exists() and not overwrite:
        logger.info(f"Target DB already exists: {db_path}. Verifying existing store...")
        return verify_road_segments_store(parquet_path, db_path)

    tmp_db_path = db_path.with_suffix(".db.tmp")
    if tmp_db_path.exists():
        tmp_db_path.unlink()

    cols = ["segment_id", "way_id", "latitude", "longitude", "length_m", "road_type"]

    conn = sqlite3.connect(str(tmp_db_path))
    c = conn.cursor()

    c.execute("PRAGMA page_size = 4096")
    c.execute("PRAGMA synchronous = OFF")
    c.execute("PRAGMA journal_mode = OFF")
    c.execute("PRAGMA cache_size = -64000")

    c.execute("""
    CREATE TABLE road_segments (
        segment_id TEXT PRIMARY KEY NOT NULL,
        way_id INTEGER,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        length_m REAL NOT NULL,
        road_type TEXT NOT NULL
    )
    """)

    insert_sql = "INSERT INTO road_segments VALUES (?, ?, ?, ?, ?, ?)"

    pf = pq.ParquetFile(str(parquet_path))
    total_rows = 0
    t0 = time.perf_counter()

    for batch in pf.iter_batches(batch_size=batch_size, columns=cols):
        df_batch = batch.to_pandas()
        records = []
        for row in df_batch[cols].itertuples(index=False):
            wid = row[1]
            way_id_val = int(wid) if (wid is not None and not (isinstance(wid, float) and math.isnan(wid))) else None
            records.append((
                str(row[0]),
                way_id_val,
                float(row[2]),
                float(row[3]),
                float(row[4]),
                str(row[5]),
            ))
        c.executemany(insert_sql, records)
        total_rows += len(records)
        del records, df_batch
        logger.info(f"Streamed {total_rows:,} / {EXPECTED_ROW_COUNT:,} road segment rows...")

    conn.commit()

    logger.info("Creating spatial index on (latitude, longitude)...")
    c.execute("CREATE INDEX idx_rs_spatial ON road_segments (latitude, longitude)")
    conn.commit()

    logger.info("Optimizing and vacuuming road segments store...")
    c.execute("PRAGMA journal_mode = DELETE")
    c.execute("PRAGMA synchronous = NORMAL")
    conn.commit()
    c.execute("VACUUM")
    c.execute("PRAGMA optimize")
    conn.close()

    elapsed = time.perf_counter() - t0
    logger.info(f"Road segments store built in {elapsed:.2f}s ({total_rows:,} rows).")

    if db_path.exists():
        db_path.unlink()
    tmp_db_path.rename(db_path)

    return verify_road_segments_store(parquet_path, db_path)


def verify_road_segments_store(parquet_path: Path, db_path: Path) -> bool:
    logger.info("Verifying road segments store integrity...")
    conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM road_segments")
    row_count = c.fetchone()[0]
    if row_count != EXPECTED_ROW_COUNT:
        logger.error(f"Row count mismatch: expected {EXPECTED_ROW_COUNT}, got {row_count}")
        conn.close()
        return False

    c.execute("PRAGMA table_info(road_segments)")
    table_cols = [r[1] for r in c.fetchall()]
    expected_cols = ["segment_id", "way_id", "latitude", "longitude", "length_m", "road_type"]
    if table_cols != expected_cols:
        logger.error("Column specification mismatch in road_segments")
        conn.close()
        return False

    c.execute("PRAGMA index_list(road_segments)")
    indexes = [r[1] for r in c.fetchall()]
    if "idx_rs_spatial" not in indexes:
        logger.error("idx_rs_spatial missing from road_segments")
        conn.close()
        return False

    conn.close()
    logger.info("Road segments store verification PASSED: 1,042,651 rows verified with spatial index.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Build companion stores for NavSakhi data.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing store databases")
    args = parser.parse_args()

    logger.info("Starting Phase 46I Companion Store Build...")

    logger.info("Verifying source Parquet file integrity...")
    if not verify_file_sha256(DEFAULT_MFT_PARQUET, EXPECTED_MFT_SHA256):
        sys.exit(1)
    if not verify_file_sha256(DEFAULT_RS_PARQUET, EXPECTED_RS_SHA256):
        sys.exit(1)
    logger.info("Source Parquet SHA-256 hashes verified bit-for-bit.")

    ok_feat = build_feature_store(
        DEFAULT_MFT_PARQUET,
        DEFAULT_FEATURE_STORE_DB,
        batch_size=50000,
        overwrite=args.overwrite,
    )
    if not ok_feat:
        logger.error("Feature store build failed.")
        sys.exit(1)

    ok_road = build_road_segments_store(
        DEFAULT_RS_PARQUET,
        DEFAULT_ROAD_STORE_DB,
        batch_size=50000,
        overwrite=args.overwrite,
    )
    if not ok_road:
        logger.error("Road segments store build failed.")
        sys.exit(1)

    feat_sz = DEFAULT_FEATURE_STORE_DB.stat().st_size / (1024 * 1024)
    road_sz = DEFAULT_ROAD_STORE_DB.stat().st_size / (1024 * 1024)
    logger.info(f"Build complete! feature_store.db: {feat_sz:.2f} MB, road_segments_store.db: {road_sz:.2f} MB")


if __name__ == "__main__":
    main()
