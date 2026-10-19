import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from pyrosm import OSM
from shapely.geometry import LineString
import warnings
warnings.filterwarnings('ignore')

def main():
    out_dir = Path("docs/reports/osm_validation")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print("Loading road segments...")
    segments = pd.read_parquet("ml/datasets/processed/road_segments.parquet")
    segments_gdf = gpd.GeoDataFrame(
        segments, 
        geometry=gpd.points_from_xy(segments.longitude, segments.latitude),
        crs="EPSG:4326"
    ).to_crs(epsg=3857)
    
    print("Loading POIs from PBF...")
    osm = OSM("ml/datasets/raw/osm/chennai_v1.osm.pbf")
    custom_filter = {
        'amenity': ['hospital', 'clinic', 'police', 'school', 'restaurant', 'atm', 'bank', 'fuel'],
        'highway': ['bus_stop']
    }
    pois = osm.get_pois(custom_filter=custom_filter)
    pois['geometry'] = pois.geometry.centroid
    pois = pois.to_crs(epsg=3857)
    
    # Categorize
    def get_cat(row):
        if pd.notna(row.get('amenity')):
            val = row['amenity']
            if val in ['hospital', 'clinic']: return 'Hospital'
            if val == 'police': return 'Police'
            if val == 'school': return 'School'
            if val == 'restaurant': return 'Restaurant'
            if val == 'atm': return 'ATM'
            if val == 'bank': return 'Bank'
            if val == 'fuel': return 'Fuel'
        if pd.notna(row.get('highway')) and row['highway'] == 'bus_stop': return 'Bus Stop'
        return 'Unknown'
        
    pois['category'] = pois.apply(get_cat, axis=1)
    pois = pois[pois['category'] != 'Unknown'].copy()
    
    # Generate an explicit POI ID
    pois['poi_id'] = range(len(pois))
    
    print("Performing spatial joins...")
    # Perform nearest join
    joined = gpd.sjoin_nearest(pois, segments_gdf, how='left', distance_col='dist_to_segment')
    
    # Validate uniqueness
    print("Validating constraints...")
    duplicate_assignments = joined.duplicated(subset=['poi_id']).sum()
    missing_assignments = joined['dist_to_segment'].isna().sum()
    
    # Force 1-to-1 by dropping duplicates if any (due to exact equidistant segments)
    joined = joined.drop_duplicates(subset=['poi_id'])
    
    # Sample 100 per category
    samples = []
    for cat in joined['category'].unique():
        cat_df = joined[joined['category'] == cat]
        if len(cat_df) > 100:
            samples.append(cat_df.sample(100, random_state=42))
        else:
            samples.append(cat_df)
            
    sampled_df = pd.concat(samples)
    
    # Create sample report
    sample_report = sampled_df[['id', 'name', 'category', 'segment_id', 'dist_to_segment']]
    # Add lat/lon from EPSG 4326
    pois_4326 = pois.to_crs(epsg=4326)
    sample_report = sample_report.merge(
        pois_4326[['poi_id', 'geometry']].rename(columns={'geometry': 'geom_4326'}),
        left_index=True, right_index=True
    )
    sample_report['latitude'] = sample_report['geom_4326'].apply(lambda pt: pt.y if pd.notna(pt) else None)
    sample_report['longitude'] = sample_report['geom_4326'].apply(lambda pt: pt.x if pd.notna(pt) else None)
    sample_report['within_threshold'] = sample_report['dist_to_segment'] <= 5000
    sample_report.drop(columns=['geom_4326']).to_csv(out_dir / "pois_sample.csv", index=False)
    
    # Summary statistics
    print("Computing statistics...")
    stats = []
    for cat in joined['category'].unique():
        cat_df = joined[joined['category'] == cat]
        dists = cat_df['dist_to_segment']
        stats.append({
            'Category': cat,
            'Total Extracted': len(cat_df),
            'Total Assigned': len(cat_df[cat_df['dist_to_segment'].notna()]),
            'Mean Distance': dists.mean(),
            'Median Distance': dists.median(),
            '95th Percentile': dists.quantile(0.95),
            'Max Distance': dists.max()
        })
        
        # Histograms
        plt.figure(figsize=(8, 5))
        plt.hist(dists.clip(upper=1000), bins=50, color='skyblue', edgecolor='black')
        plt.title(f'Distance to Nearest Road - {cat}')
        plt.xlabel('Distance (meters) - Capped at 1000m for visualization')
        plt.ylabel('Frequency')
        plt.tight_layout()
        plt.savefig(out_dir / f'dist_hist_{cat}.png')
        plt.close()
        
    stats_df = pd.DataFrame(stats)
    with open(out_dir / "validation_stats.txt", "w") as f:
        f.write("--- OSM Extraction Validation Statistics ---\n\n")
        f.write(stats_df.to_string(index=False))
        f.write("\n\n--- Verification Constraints ---\n")
        f.write(f"Duplicate POI Assignments: {duplicate_assignments}\n")
        f.write(f"Missing POI Assignments: {missing_assignments}\n")
        
    # Export GeoJSON for subset (Too large to export all, take a 5km x 5km bounding box)
    print("Exporting spatial files...")
    bounds = pois.total_bounds
    center_x = (bounds[0] + bounds[2]) / 2
    center_y = (bounds[1] + bounds[3]) / 2
    bbox = [center_x - 2500, center_y - 2500, center_x + 2500, center_y + 2500]
    
    sub_pois = pois.cx[bbox[0]:bbox[2], bbox[1]:bbox[3]].to_crs(epsg=4326)
    sub_segs = segments_gdf.cx[bbox[0]:bbox[2], bbox[1]:bbox[3]].to_crs(epsg=4326)
    
    if not sub_pois.empty and not sub_segs.empty:
        sub_segs.to_file(out_dir / "segments_subset.geojson", driver='GeoJSON')
        sub_pois.to_file(out_dir / "pois_subset.geojson", driver='GeoJSON')
        
        # Generate Assignment Lines
        # We need the segments lat/lon to draw lines
        lines = []
        subset_joined = joined.loc[sub_pois.index]
        subset_joined = subset_joined.merge(segments_gdf[['segment_id', 'geometry']], on='segment_id', suffixes=('', '_seg'))
        
        for idx, row in subset_joined.iterrows():
            if pd.notna(row.get('geometry_seg')):
                lines.append(LineString([row['geometry'], row['geometry_seg']]))
                
        lines_gdf = gpd.GeoDataFrame(geometry=lines, crs="EPSG:3857").to_crs(epsg=4326)
        lines_gdf.to_file(out_dir / "assignment_links.geojson", driver='GeoJSON')
        
        # Visualization Map
        fig, ax = plt.subplots(figsize=(10, 10))
        sub_segs.plot(ax=ax, color='gray', alpha=0.5, markersize=1, label='Road Segments')
        lines_gdf.plot(ax=ax, color='blue', alpha=0.3, linewidth=0.5, label='Assignments')
        sub_pois.plot(ax=ax, column='category', legend=True, markersize=15, cmap='tab10')
        plt.title('POI to Road Segment Assignments')
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(out_dir / 'map_subset.png', dpi=300)
        plt.close()
        
    print("Done!")

if __name__ == '__main__':
    main()
