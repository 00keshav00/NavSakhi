"""
Generates clean, publication-grade architectural diagrams for the SafeShe ML Academic Report.
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os

os.makedirs("docs/report_assets", exist_ok=True)

plt.rcParams['font.family'] = 'DejaVu Sans'

def draw_overall_architecture():
    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    ax.axis('off')
    
    # Palette
    c_blue = '#1B365D'
    c_slate = '#2C5282'
    c_teal = '#0F766E'
    c_amber = '#D97706'
    c_light = '#F8FAFC'
    c_gray = '#64748B'

    title = fig.suptitle("SafeShe: End-to-End Machine Learning Subsystem Architecture", 
                         fontsize=14, fontweight='bold', color=c_blue, y=0.98)
    
    # Stages: Box list
    stages = [
        ("Raw Geospatial Data\n(OSM, Crime CSV, WorldPop)", 0.05, 0.72, 0.25, 0.18, '#E2E8F0', '#1E293B'),
        ("Geospatial Processing\n& 150m Segmentation", 0.38, 0.72, 0.25, 0.18, '#E0F2FE', '#0369A1'),
        ("Spatial Feature Joins\n& Derived Feature Eng.", 0.70, 0.72, 0.25, 0.18, '#E0F2FE', '#0369A1'),
        
        ("Synthetic Target Gen.\nCPTED Heuristic + Noise", 0.70, 0.42, 0.25, 0.18, '#FEF3C7', '#B45309'),
        ("41 Canonical Predictors\nMaster Feature Table", 0.38, 0.42, 0.25, 0.18, '#F1F5F9', '#334155'),
        ("GroupShuffleSplit\n(by OSM way_id, 0% Overlap)", 0.05, 0.42, 0.25, 0.18, '#EDE9FE', '#6D28D9'),
        
        ("Frozen Preprocessor\nStandardScaler + OHE (77 Dims)", 0.05, 0.12, 0.25, 0.18, '#CCFBF1', '#0F766E'),
        ("Tuned LightGBM Regressor\n(n_est=150, leaves=63)", 0.38, 0.12, 0.25, 0.18, '#DBEAFE', '#1D4ED8'),
        ("Online MLSafetyPredictor\n[0, 100] Safety Score Serving", 0.70, 0.12, 0.25, 0.18, '#DCFCE7', '#15803D')
    ]

    for label, x, y, w, h, bg, border in stages:
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.03",
                                      facecolor=bg, edgecolor=border, linewidth=1.5)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, label, ha='center', va='center', fontsize=9, fontweight='bold', color=border)

    # Arrows
    arrow_props = dict(facecolor=c_gray, edgecolor=c_gray, arrowstyle="->", lw=2, mutation_scale=15)
    
    # 1 -> 2 -> 3
    ax.annotate("", xy=(0.38, 0.81), xytext=(0.30, 0.81), arrowprops=arrow_props)
    ax.annotate("", xy=(0.70, 0.81), xytext=(0.63, 0.81), arrowprops=arrow_props)
    # 3 -> 4
    ax.annotate("", xy=(0.825, 0.60), xytext=(0.825, 0.72), arrowprops=arrow_props)
    # 4 -> 5 -> 6
    ax.annotate("", xy=(0.63, 0.51), xytext=(0.70, 0.51), arrowprops=arrow_props)
    ax.annotate("", xy=(0.30, 0.51), xytext=(0.38, 0.51), arrowprops=arrow_props)
    # 6 -> 7
    ax.annotate("", xy=(0.175, 0.30), xytext=(0.175, 0.42), arrowprops=arrow_props)
    # 7 -> 8 -> 9
    ax.annotate("", xy=(0.38, 0.21), xytext=(0.30, 0.21), arrowprops=arrow_props)
    ax.annotate("", xy=(0.70, 0.21), xytext=(0.63, 0.21), arrowprops=arrow_props)

    plt.tight_layout()
    plt.savefig("docs/report_assets/arch_overall.png", dpi=300)
    plt.close()

def draw_data_acquisition_pipeline():
    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=300)
    ax.axis('off')
    fig.suptitle("SafeShe Data Ingestion and Feature Assembly Pipeline", fontsize=13, fontweight='bold', color='#1B365D', y=0.98)
    
    boxes = [
        ("chennai_roads.osm.pbf\n(38.6 MB OpenStreetMap)", 0.05, 0.65, 0.26, 0.22, '#E2E8F0', '#1E293B'),
        ("pyrosm Road Network\n& Multi-radius POI Extraction", 0.37, 0.65, 0.26, 0.22, '#E0F2FE', '#0369A1'),
        ("Intermediate Parquet Tables\n(road, poi, dist, pop)\n1,042,651 Segments", 0.69, 0.65, 0.26, 0.22, '#F1F5F9', '#334155'),
        
        ("chennai_crime_data.csv\n(4,821 Police Records)", 0.05, 0.15, 0.26, 0.22, '#FEE2E2', '#B91C1C'),
        ("Spatial Geocoding\n& Demographic Imputation", 0.37, 0.15, 0.26, 0.22, '#FEF3C7', '#B45309'),
        ("Master Parquet Dataset\n(training_dataset.parquet)\n1,042,651 rows x 56 cols", 0.69, 0.15, 0.26, 0.22, '#DCFCE7', '#15803D')
    ]
    for label, x, y, w, h, bg, border in boxes:
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.03",
                                      facecolor=bg, edgecolor=border, linewidth=1.5)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, label, ha='center', va='center', fontsize=8.5, fontweight='bold', color=border)

    arrow_props = dict(facecolor='#64748B', edgecolor='#64748B', arrowstyle="->", lw=2, mutation_scale=15)
    ax.annotate("", xy=(0.37, 0.76), xytext=(0.31, 0.76), arrowprops=arrow_props)
    ax.annotate("", xy=(0.69, 0.76), xytext=(0.63, 0.76), arrowprops=arrow_props)
    ax.annotate("", xy=(0.37, 0.26), xytext=(0.31, 0.26), arrowprops=arrow_props)
    ax.annotate("", xy=(0.69, 0.26), xytext=(0.63, 0.26), arrowprops=arrow_props)
    ax.annotate("", xy=(0.82, 0.37), xytext=(0.82, 0.65), arrowprops=arrow_props)

    plt.tight_layout()
    plt.savefig("docs/report_assets/data_acquisition_pipeline.png", dpi=300)
    plt.close()

def draw_inference_pipeline():
    fig, ax = plt.subplots(figsize=(9, 4), dpi=300)
    ax.axis('off')
    fig.suptitle("Online ML Inference Engine (MLSafetyPredictor)", fontsize=13, fontweight='bold', color='#1B365D', y=0.98)
    
    boxes = [
        ("OSRM Route Query\nCandidate Segments", 0.05, 0.35, 0.18, 0.35, '#F1F5F9', '#334155'),
        ("Input Schema Validation\n(41 Canonical Features)", 0.28, 0.35, 0.19, 0.35, '#EDE9FE', '#6D28D9'),
        ("ColumnTransformer\n(77 Scaled/OHE Dims)", 0.51, 0.35, 0.19, 0.35, '#CCFBF1', '#0F766E'),
        ("Frozen LightGBM\n(Leaf-wise Prediction)", 0.74, 0.55, 0.21, 0.25, '#DBEAFE', '#1D4ED8'),
        ("Safety Score\n[0.0, 100.0] Clipped", 0.74, 0.15, 0.21, 0.25, '#DCFCE7', '#15803D')
    ]
    for label, x, y, w, h, bg, border in boxes:
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.03",
                                      facecolor=bg, edgecolor=border, linewidth=1.5)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, label, ha='center', va='center', fontsize=8.5, fontweight='bold', color=border)

    arrow_props = dict(facecolor='#64748B', edgecolor='#64748B', arrowstyle="->", lw=2, mutation_scale=15)
    ax.annotate("", xy=(0.28, 0.52), xytext=(0.23, 0.52), arrowprops=arrow_props)
    ax.annotate("", xy=(0.51, 0.52), xytext=(0.47, 0.52), arrowprops=arrow_props)
    ax.annotate("", xy=(0.74, 0.67), xytext=(0.70, 0.52), arrowprops=arrow_props)
    ax.annotate("", xy=(0.845, 0.40), xytext=(0.845, 0.55), arrowprops=arrow_props)

    plt.tight_layout()
    plt.savefig("docs/report_assets/inference_pipeline.png", dpi=300)
    plt.close()

draw_overall_architecture()
draw_data_acquisition_pipeline()
draw_inference_pipeline()
print("All architecture and pipeline diagrams successfully rendered!")
