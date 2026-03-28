import pandas as pd
df = pd.read_csv('Output/Koszulkowy/Koszulkowy_Growth_Opportunities.csv', dtype=str)
subset = df.iloc[6070:11551]
cols = ['calc_gpps', 'calc_cr', 'calc_frequency', 'calc_gppv', 'arpu', 'arpiv', 'meta_spend', 'meta_revenue', 'meta_purchases', 'calc_roas', 'ga4lp_sessions', 'ga4lp_revenue', 'ga4lp_purchases', 'ga4lp_first_time_purchasers', 'ga4item_views', 'ga4item_revenue']

print('--- CHECKING VALUES IN RANGE 6070-11551 ---')
for c in cols:
    if c in subset.columns:
        z_count = (subset[c] == '0.0').sum()
        z_str_count = (subset[c] == '0').sum()
        total_z = z_count + z_str_count
        nan_count = subset[c].isna().sum()
        valid = len(subset) - total_z - nan_count
        print(f'{c}: Zeros={total_z}, NaNs={nan_count}, ValidValues={valid}')
    else:
        print(f'{c}: MISSING COLUMN')
