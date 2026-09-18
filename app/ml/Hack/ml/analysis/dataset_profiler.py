"""
Dataset Profiler module.
Analyzes the final merged master feature table and labels for exploratory analysis,
correlation, outlier detection, and range validation. Generates comprehensive CSV and HTML reports.
"""

import logging
import base64
from io import BytesIO
from pathlib import Path
import pandas as pd
import numpy as np
import sys

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    from sklearn.feature_selection import mutual_info_regression
    HAS_EXTRAS = True
except ImportError:
    HAS_EXTRAS = False
    print("Warning: matplotlib, seaborn, or scikit-learn missing. Visuals and mutual info will be skipped.")

from ml.config.paths import MASTER_FEATURE_TABLE, LABELS

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class DatasetProfiler:
    """Reads processed ML datasets and generates statistical profiles."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.html_sections = []
        self.df = None
        self.numeric_df = None

    def _fig_to_base64(self) -> str:
        """Converts the current matplotlib figure to a base64 HTML img tag."""
        if not HAS_EXTRAS:
            return ""
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close()
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        return f'<img src="data:image/png;base64,{img_str}" />'

    def load_data(self) -> bool:
        """Loads and joins the master feature table and labels."""
        if not MASTER_FEATURE_TABLE.exists() or not LABELS.exists():
            logger.error("Required Parquet datasets not found. Ensure pipeline has run.")
            return False

        logger.info("Loading Datasets...")
        master = pd.read_parquet(MASTER_FEATURE_TABLE)
        labels = pd.read_parquet(LABELS)

        # Inner join on segment_id
        self.df = master.merge(labels, on='segment_id', how='inner')
        self.numeric_df = self.df.select_dtypes(include=[np.number])
        return True

    def analyze_overview(self) -> None:
        """Generates dataset overview (rows, cols, memory)."""
        logger.info("Analyzing Overview...")
        num_rows = len(self.df)
        num_cols = len(self.df.columns)
        memory = self.df.memory_usage(deep=True).sum() / (1024 * 1024)

        summary_df = pd.DataFrame({
            "Metric": ["Rows", "Columns", "Memory Usage (MB)"],
            "Value": [num_rows, num_cols, f"{memory:.2f}"]
        })
        summary_df.to_csv(self.output_dir / "dataset_summary.csv", index=False)

        dtypes_df = pd.DataFrame(self.df.dtypes, columns=['Data Type']).reset_index()
        dtypes_df.rename(columns={'index': 'Column'}, inplace=True)
        dtypes_df['Data Type'] = dtypes_df['Data Type'].astype(str)

        html = f"""
        <h2>Dataset Overview</h2>
        <p><strong>Rows:</strong> {num_rows}</p>
        <p><strong>Columns:</strong> {num_cols}</p>
        <p><strong>Memory Usage:</strong> {memory:.2f} MB</p>
        {dtypes_df.to_html(index=False, classes='table')}
        """
        self.html_sections.append(html)

    def analyze_missing(self) -> None:
        """Analyzes missing data counts and percentages."""
        logger.info("Analyzing Missing Data...")
        missing_counts = self.df.isna().sum()
        missing_pct = (missing_counts / len(self.df)) * 100

        missing_df = pd.DataFrame({
            'Missing_Count': missing_counts,
            'Missing_Percentage': missing_pct
        }).sort_values('Missing_Percentage', ascending=False)
        
        missing_df.to_csv(self.output_dir / "missing_values.csv")

        html = f"""
        <h2>Missing Data</h2>
        {missing_df[missing_df['Missing_Count'] > 0].to_html(classes='table') if (missing_df['Missing_Count'] > 0).any() else "<p>No missing values found.</p>"}
        """
        self.html_sections.append(html)

    def analyze_numeric_stats(self) -> None:
        """Computes core numeric statistics."""
        logger.info("Analyzing Numeric Statistics...")
        stats_df = self.numeric_df.describe(percentiles=[.25, .5, .75]).T
        stats_df.rename(columns={'50%': 'median'}, inplace=True)
        stats_df.to_csv(self.output_dir / "feature_statistics.csv")

        html = f"""
        <h2>Numeric Feature Statistics</h2>
        {stats_df[['mean', 'median', 'std', 'min', 'max', '25%', '75%']].to_html(classes='table')}
        """
        self.html_sections.append(html)

    def analyze_distributions(self) -> None:
        """Plots histograms for numeric features."""
        if not HAS_EXTRAS:
            return
            
        logger.info("Plotting Feature Distributions...")
        cols = [c for c in self.numeric_df.columns if c != 'segment_id']
        n_cols = len(cols)
        
        # Grid layout
        fig_cols = 4
        fig_rows = int(np.ceil(n_cols / fig_cols))
        
        plt.figure(figsize=(fig_cols * 4, fig_rows * 3))
        for i, col in enumerate(cols):
            plt.subplot(fig_rows, fig_cols, i + 1)
            sns.histplot(self.numeric_df[col].dropna(), bins=30, kde=True)
            plt.title(col, fontsize=10)
            plt.xlabel("")
            plt.ylabel("")
        plt.tight_layout()
        img_html = self._fig_to_base64()
        
        self.html_sections.append(f"<h2>Feature Distributions</h2>{img_html}")

    def analyze_correlations(self) -> None:
        """Computes Pearson correlation and highlights top drivers for safety score."""
        logger.info("Analyzing Correlations...")
        corr_matrix = self.numeric_df.corr(method='pearson')
        corr_matrix.to_csv(self.output_dir / "correlation_matrix.csv")

        html = "<h2>Correlation Analysis</h2>"
        
        if HAS_EXTRAS:
            plt.figure(figsize=(12, 10))
            sns.heatmap(corr_matrix, annot=False, cmap='coolwarm', center=0)
            plt.title('Pearson Correlation Matrix')
            html += self._fig_to_base64()

        if 'safety_score' in corr_matrix.columns:
            target_corr = corr_matrix['safety_score'].drop('safety_score').sort_values(ascending=False)
            top_pos = target_corr.head(5)
            top_neg = target_corr.tail(5)
            
            html += "<h3>Strongest Positive Correlations with Safety Score</h3>"
            html += top_pos.to_frame(name='Pearson r').to_html(classes='table')
            html += "<h3>Strongest Negative Correlations with Safety Score</h3>"
            html += top_neg.to_frame(name='Pearson r').to_html(classes='table')
            
        self.html_sections.append(html)

    def detect_outliers(self) -> None:
        """Detects IQR-based outliers."""
        logger.info("Detecting Outliers...")
        Q1 = self.numeric_df.quantile(0.25)
        Q3 = self.numeric_df.quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        outlier_counts = ((self.numeric_df < lower_bound) | (self.numeric_df > upper_bound)).sum()
        outlier_pct = (outlier_counts / len(self.numeric_df)) * 100
        
        outliers_df = pd.DataFrame({
            'Outlier_Count': outlier_counts,
            'Percentage': outlier_pct
        }).sort_values('Percentage', ascending=False)
        
        suspicious = outliers_df[outliers_df['Percentage'] > 5.0]
        
        html = f"""
        <h2>Outlier Detection (IQR Method)</h2>
        <p>Features with > 5% outliers are flagged as suspicious:</p>
        {suspicious.to_html(classes='table') if not suspicious.empty else "<p>No suspicious features found.</p>"}
        """
        self.html_sections.append(html)

    def range_validation(self) -> None:
        """Validates specific features remain strictly within 0-100 bounds."""
        logger.info("Validating Ranges (0-100 bounds)...")
        target_features = [
            'human_activity_score', 'desertion_score', 'essential_services_density',
            'synth_lighting', 'synth_cctv', 'synth_night_activity', 'synth_visibility',
            'synth_community_safety', 'synth_road_maintenance', 'synthetic_confidence',
            'safety_score', 'crowd_score', 'label_confidence'
        ]
        
        results = []
        for feat in target_features:
            if feat in self.df.columns:
                s = self.df[feat].dropna()
                min_val = s.min()
                max_val = s.max()
                is_valid = (min_val >= 0.0) and (max_val <= 100.0)
                results.append({'Feature': feat, 'Min': min_val, 'Max': max_val, 'Valid': is_valid})
        
        val_df = pd.DataFrame(results)
        
        html = f"""
        <h2>Range Validation</h2>
        {val_df.to_html(classes='table', index=False)}
        """
        self.html_sections.append(html)

    def analyze_feature_importance(self) -> None:
        """Computes Mutual Information against safety_score."""
        if not HAS_EXTRAS or 'safety_score' not in self.numeric_df.columns:
            return
            
        logger.info("Computing Mutual Information Feature Importance...")
        df_clean = self.numeric_df.dropna()
        if df_clean.empty:
            return
            
        X = df_clean.drop(columns=['safety_score', 'segment_id'], errors='ignore')
        y = df_clean['safety_score']
        
        mi_scores = mutual_info_regression(X, y, random_state=42)
        mi_df = pd.DataFrame({'Feature': X.columns, 'MI_Score': mi_scores}).sort_values('MI_Score', ascending=False)
        
        plt.figure(figsize=(10, 8))
        sns.barplot(x='MI_Score', y='Feature', data=mi_df.head(20))
        plt.title("Top 20 Features by Mutual Information")
        plt.tight_layout()
        img_html = self._fig_to_base64()
        
        html = f"""
        <h2>Feature Importance Preview (Mutual Information)</h2>
        {img_html}
        {mi_df.head(10).to_html(classes='table', index=False)}
        """
        self.html_sections.append(html)

    def export_html(self) -> None:
        """Writes the aggregated HTML report."""
        logger.info("Generating final HTML profile...")
        css = """
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; color: #333; }
            h1, h2, h3 { color: #2c3e50; }
            .table { border-collapse: collapse; margin-bottom: 30px; font-size: 0.9em; min-width: 400px; box-shadow: 0 0 20px rgba(0, 0, 0, 0.15); }
            .table thead tr { background-color: #009879; color: #ffffff; text-align: left; }
            .table th, .table td { padding: 12px 15px; border: 1px solid #ddd; }
            .table tbody tr { border-bottom: 1px solid #dddddd; }
            .table tbody tr:nth-of-type(even) { background-color: #f3f3f3; }
            .table tbody tr:last-of-type { border-bottom: 2px solid #009879; }
            img { max-width: 100%; height: auto; border: 1px solid #ccc; margin-bottom: 30px; }
        </style>
        """
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>SafeShe Dataset Profile</title>{css}</head>
        <body>
            <h1>SafeShe Master Dataset Profile Report</h1>
            {''.join(self.html_sections)}
        </body>
        </html>
        """
        with open(self.output_dir / "dataset_profile.html", "w", encoding='utf-8') as f:
            f.write(full_html)

    def run(self) -> None:
        if not self.load_data():
            return
            
        self.analyze_overview()
        self.analyze_missing()
        self.analyze_numeric_stats()
        self.detect_outliers()
        self.range_validation()
        
        self.analyze_distributions()
        self.analyze_correlations()
        self.analyze_feature_importance()
        
        self.export_html()
        logger.info(f"Dataset profiling complete. Reports saved to {self.output_dir.absolute()}")

if __name__ == "__main__":
    report_dir = Path("reports")
    profiler = DatasetProfiler(report_dir)
    profiler.run()
