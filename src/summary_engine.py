import pandas as pd
import os
import json
import glob
from datetime import datetime

def generate_summary(output_dir="Output"):
    print(f"Generating Summary Report from {output_dir}...")
    
    summary_data = []
    
    # 1. Scan for Brand Files
    files = glob.glob(os.path.join(output_dir, "*", "*_Landing_Page_Final.csv"))
    
    if not files:
        print("No output files found!")
        return

    # 2. Aggregations
    total_revenue_potential = 0
    total_products = 0
    
    for file in files:
        try:
            brand = os.path.basename(os.path.dirname(file))
            df = pd.read_csv(file)
            
            # Basic Stats
            n_products = len(df)
            total_products += n_products
            
            # P-Class Distribution
            p_counts = df['priority'].value_counts().to_dict()
            
            # GA4 Class Distribution
            class_counts = df['ga4_class'].value_counts().to_dict()
            
            # Revenue (Purchase Revenue or Item Revenue)
            # Try to find a revenue column
            rev_col = next((c for c in df.columns if 'revenue' in c.lower() and 'purchase' in c.lower()), None)
            if not rev_col:
                rev_col = next((c for c in df.columns if 'item revenue' in c.lower()), None)
                
            brand_revenue = df[rev_col].sum() if rev_col and rev_col in df.columns else 0
            
            # Meta Spend
            spend = df['meta_spend'].sum() if 'meta_spend' in df.columns else 0
            
            summary_data.append({
                'Brand': brand,
                'Products': n_products,
                'Revenue': brand_revenue,
                'Ad Spend': spend,
                'P1 (Star+Profitable)': p_counts.get('P1', 0),
                'P2 (Cow+Profitable)': p_counts.get('P2', 0),
                'P3 (Gem+Profitable)': p_counts.get('P3', 0),
                'P4 (Star/NoAds)': p_counts.get('P4', 0),
                'P5 (Cow/NoAds)': p_counts.get('P5', 0),
                'Stars': class_counts.get('Star', 0),
                'Cash Cows': class_counts.get('Cash Cow', 0),
                'Hidden Gems': class_counts.get('Hidden Gem', 0),
                'Slackers': class_counts.get('Slacker', 0)
            })
            
        except Exception as e:
            print(f"Error processing {file}: {e}")

    # 3. Create DataFrame
    summ_df = pd.DataFrame(summary_data)
    
    # 4. Generate Markdown Report
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md_report = f"# Global Pipeline Summary\nGenerated: {timestamp}\n\n"
    
    # Helper to generate markdown table
    def to_md(df):
        if df.empty: return "No data matches."
        # Header
        col_widths = [max(len(str(x)) for x in df[col].tolist() + [col]) for col in df.columns]
        header = "| " + " | ".join([f"{col:<{w}}" for col, w in zip(df.columns, col_widths)]) + " |"
        separator = "| " + " | ".join(["-" * w for w in col_widths]) + " |"
        # Rows
        rows = []
        for _, row in df.iterrows():
            rows.append("| " + " | ".join([f"{str(val):<{w}}" for val, w in zip(row, col_widths)]) + " |")
        return "\n".join([header, separator] + rows)

    # Table 1: Brand Performance
    md_report += "## Brand Performance\n\n"
    # Format floats
    perf_df = summ_df[['Brand', 'Products', 'Revenue', 'Ad Spend']].copy()
    perf_df['Revenue'] = perf_df['Revenue'].apply(lambda x: f"{x:.2f}")
    perf_df['Ad Spend'] = perf_df['Ad Spend'].apply(lambda x: f"{x:.2f}")
    md_report += to_md(perf_df)
    md_report += "\n\n"
    
    # Table 2: Priority Distribution
    md_report += "## Priority Distribution (Actionable)\n\n"
    md_report += to_md(summ_df[['Brand', 'P1 (Star+Profitable)', 'P2 (Cow+Profitable)', 'P3 (Gem+Profitable)', 'P4 (Star/NoAds)', 'P5 (Cow/NoAds)']])
    md_report += "\n\n"
    
    # Table 3: Classification Distribution
    md_report += "## GA4 Classification (Health Check)\n\n"
    md_report += to_md(summ_df[['Brand', 'Stars', 'Cash Cows', 'Hidden Gems', 'Slackers']])
    md_report += "\n\n"
    
    # Save
    report_path = os.path.join(output_dir, "GLOBAL_SUMMARY.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md_report)
        
    print(f"Summary Report saved to: {report_path}")

if __name__ == "__main__":
    generate_summary()
