import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
from pyrosm import OSM

def run_validation():
    print("--- 1. Segment ID Validation ---")
    segments = pd.read_parquet("ml/datasets/processed/road_segments.parquet")
    total = len(segments)
    unique = segments["segment_id"].nunique()
    duplicates = total - unique
    max_dup = segments["segment_id"].value_counts().max()
    collision_rate = (duplicates / total) * 100
    
    print(f"Total road segments: {total}")
    print(f"Unique segment_ids: {unique}")
    print(f"Duplicate segment_ids: {duplicates}")
    print(f"Maximum duplicate count: {max_dup}")
    print(f"Hash collision count: {duplicates}")
    print(f"Collision rate: {collision_rate:.4f}%")
    
    print("\n--- 2 & 4. OSM Feature Extraction & Spatial Validation ---")
    print("Loading OSM data to compute POI matching statistics...")
    osm = OSM("ml/datasets/raw/osm/chennai_v1.osm.pbf")
    custom_filter = {
        'amenity': True, 
        'shop': True, 
        'tourism': True, 
        'leisure': True, 
        'railway': True, 
        'highway': ['bus_stop', 'crossing'],
        'landuse': ['commercial']
    }
    pois = osm.get_pois(custom_filter=custom_filter)
    if pois is not None and not pois.empty:
        pois = pois.to_crs(epsg=3857)
        pois['geometry'] = pois.geometry.centroid
    
    segments_gdf = gpd.GeoDataFrame(
        segments, 
        geometry=gpd.points_from_xy(segments.longitude, segments.latitude),
        crs="EPSG:4326"
    ).to_crs(epsg=3857)

    # Categories to check
    categories = [
        ('restaurant', 'amenity', 'restaurant'),
        ('cafe', 'amenity', 'cafe'),
        ('hotel', 'tourism', 'hotel'),
        ('hospital', 'amenity', ['hospital', 'clinic']),
        ('pharmacy', 'amenity', 'pharmacy'),
        ('school', 'amenity', 'school'),
        ('college', 'amenity', ['college', 'university']),
        ('bus_stop', 'highway', 'bus_stop'),
        ('metro', 'railway', 'station'),
        ('police', 'amenity', 'police'),
        ('atm', 'amenity', 'atm'),
        ('bank', 'amenity', 'bank'),
        ('fuel', 'amenity', 'fuel'),
        ('park', 'leisure', 'park'),
        ('mall', 'shop', 'mall'),
        ('crossing', 'highway', 'crossing')
    ]
    
    for name, tag, val in categories:
        if isinstance(val, list):
            subset = pois[pois[tag].isin(val)] if tag in pois.columns else pd.DataFrame()
        else:
            subset = pois[pois[tag] == val] if tag in pois.columns else pd.DataFrame()
            
        total_obj = len(subset)
        if total_obj == 0:
            print(f"{name.capitalize()}: 0 extracted")
            continue
            
        # Match to nearest segment (max dist 5000)
        joined = gpd.sjoin_nearest(subset, segments_gdf, how='left', distance_col='dist')
        matched = len(joined[joined['dist'] <= 5000].drop_duplicates(subset=['id']))
        unmatched = total_obj - matched
        coverage = (matched / total_obj) * 100
        avg_dist = joined['dist'].mean()
        
        print(f"{name.capitalize()}: Total={total_obj}, Matched={matched}, Unmatched={unmatched}, Coverage={coverage:.2f}%, AvgDist={avg_dist:.2f}m")

    print("\n--- 3. Feature Completeness ---")
    try:
        poi_feat = pd.read_parquet("ml/datasets/processed/osm_poi_features.parquet")
        dist_feat = pd.read_parquet("ml/datasets/processed/osm_distance_features.parquet")
        road_feat = pd.read_parquet("ml/datasets/processed/osm_road_features.parquet")
        
        master = segments[['segment_id']].merge(poi_feat, on='segment_id', how='left')
        master = master.merge(dist_feat, on='segment_id', how='left')
        master = master.merge(road_feat, on='segment_id', how='left')
        
        print(f"Rows: {len(master)}")
        print(f"Columns: {len(master.columns)}")
        print(f"Duplicate segment_ids: {master['segment_id'].duplicated().sum()}")
        invalid_geoms = (~segments_gdf.geometry.is_valid).sum()
        print(f"Invalid geometries: {invalid_geoms}")
        print("Missing values per feature:")
        missing = master.isna().sum()
        for col, count in missing[missing > 0].items():
            print(f"  {col}: {count}")
        if missing.sum() == 0:
            print("  0 missing values across all columns.")
    except Exception as e:
        print(f"Could not load feature files for completeness check: {e}")

    print("\n--- 6. Output Validation ---")
    out_dir = Path("ml/datasets/processed")
    for file in ['road_segments.parquet', 'osm_poi_features.parquet', 'osm_distance_features.parquet', 'osm_road_features.parquet']:
        p = out_dir / file
        if p.exists():
            df = pd.read_parquet(p)
            size_mb = p.stat().st_size / (1024 * 1024)
            print(f"File: {file} | Rows: {len(df)} | Cols: {len(df.columns)} | Size: {size_mb:.2f}MB | PK Unique: {df['segment_id'].is_unique}")
        else:
            print(f"File: {file} | Not found")

if __name__ == '__main__':
    run_validation()
