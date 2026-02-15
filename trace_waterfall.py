"""
Trace WHY the waterfall returns IGNORE even when ga4lp_sessions=500.
The waterfall at line 302 checks: ga4lp_sessions >= MIN_ORGANIC_SESSIONS (default 300)
But the direct API test returns IGNORE with sessions=500. Something is wrong.
"""
import sys, json, requests
sys.path.insert(0, "src")
import pandas as pd
import complete_pipeline as cp
import business_logic_layer as bl

# Simulate exactly what the API does
feed_data = [{
    "feed_id": "1159",
    "feed_title": "iiyama XUB2492HSU-B6",
    "feed_link": "https://iiyama-sklep.pl/1159-test.html",
    "feed_brand": "iiyama",
    "feed_category": "Monitory biurowe",
    "feed_category_full": "Monitory biurowe",
    "feed_price_str": "599 PLN",
    "norm_url": "iiyama-sklep.pl/1159-monitory-biurowe-monitor-iiyama-prolite-xub2492hsu-b6-24-ips-led-100hz-04ms-hdmi-displayport-hub-usb-has-flickerfree-4948570122578.html",
    "base_gross_margin": 0.1,
}]

lp_data = [{
    "ga4_lp_url": "/1159-monitory-biurowe-monitor-iiyama-prolite-xub2492hsu-b6-24-ips-led-100hz-04ms-hdmi-displayport-hub-usb-has-flickerfree-4948570122578.html",
    "ga4_norm_path": "1159-monitory-biurowe-monitor-iiyama-prolite-xub2492hsu-b6-24-ips-led-100hz-04ms-hdmi-displayport-hub-usb-has-flickerfree-4948570122578.html",
    "ga4_sessions": 500,
    "ga4_revenue": 25000.0,
    "ga4_trans": 8,
    "ga4_users": 400,
    "ga4_first_time_purchasers": 3,
}]

# Apply LP_REMAP (same as main.py _prepare_lp)
LP_REMAP = {
    'ga4_lp_url': 'Landing page',
    'ga4_norm_path': '_ga4_norm_path',
    'ga4_sessions': 'Sessions',
    'ga4_revenue': 'Purchase revenue',
    'ga4_trans': 'Purchases',
    'ga4_users': 'Users',
    'ga4_first_time_purchasers': 'First time purchasers',
}

feed_df = pd.DataFrame(feed_data)
lp_df = pd.DataFrame(lp_data)

# Remap
lp_df = lp_df.rename(columns={k: v for k, v in LP_REMAP.items() if k in lp_df.columns})
print("LP after remap:")
print(f"  Columns: {list(lp_df.columns)}")
print(f"  Values: {lp_df.iloc[0].to_dict()}")

# Call join_and_enrich_data
print("\n=== join_and_enrich_data ===")
result_df = cp.join_and_enrich_data(feed_df, pd.DataFrame(), lp_df, pd.DataFrame(), 
                                     default_margin=0.1, category_overrides=[])

print(f"After join: {len(result_df)} rows")
print(f"Columns: {sorted(result_df.columns.tolist())}")

# Check LP-related columns after join
print(f"\n--- LP columns after join ---")
for col in ['ga4lp_sessions', 'ga4lp_purchases', 'ga4lp_revenue', 'ga4lp_users',
            'ga4lp_first_time_purchasers', 'path_key', 'norm_url']:
    if col in result_df.columns:
        val = result_df.iloc[0][col]
        print(f"  {col} = {val}")
    else:
        print(f"  {col} = MISSING FROM COLUMNS!")

# Now run the waterfall
print(f"\n=== run_pipeline_logic ===")
params = {
    'vat': 0.23,
    'P75_VOL_META': 1, 'P75_EFF_META': 1,
    'P75_VOL_GA': 1, 'P75_EFF_GA': 1,
    'P75_VOL_ITEM': 1, 'P75_EFF_ITEM': 1,
    'MIN_META_TRANS': 10,
    'MIN_ORGANIC_SESSIONS': 300,
}

result = cp.run_pipeline_logic(result_df, params)
print(f"Result: {len(result)} rows")
for _, row in result.iterrows():
    print(f"  ID={row.get('feed_id')}")
    print(f"    ga4lp_sessions = {row.get('ga4lp_sessions')} (type: {type(row.get('ga4lp_sessions')).__name__})")
    print(f"    calc_gpps = {row.get('calc_gpps')}")
    print(f"    calc_segment = {row.get('calc_segment')}")
    print(f"    calc_priority = {row.get('calc_priority')}")
    print(f"    calc_reason = {row.get('calc_reason')}")
    print(f"    ga4_class = {row.get('ga4_class')}")
    print(f"    meta_class = {row.get('meta_class')}")
    print(f"    calc_entity_type = {row.get('calc_entity_type')}")
    print(f"    calc_contribution_profit = {row.get('calc_contribution_profit')}")
    print(f"    ga4item_views = {row.get('ga4item_views')}")
    
    # Manually step through waterfall
    print(f"\n    --- Waterfall trace ---")
    meta_purchases = row.get('meta_purchases', 0)
    print(f"    Step 1: meta_purchases={meta_purchases} >= MIN_META_TRANS={params['MIN_META_TRANS']}? {meta_purchases >= params['MIN_META_TRANS'] if pd.notna(meta_purchases) else 'NaN'}")
    
    sessions = row.get('ga4lp_sessions', 0)
    print(f"    Step 2: ga4lp_sessions={sessions} >= MIN_ORGANIC_SESSIONS={params['MIN_ORGANIC_SESSIONS']}? {sessions >= params['MIN_ORGANIC_SESSIONS'] if pd.notna(sessions) else 'NaN'}")
    
    if pd.notna(sessions) and sessions >= params['MIN_ORGANIC_SESSIONS']:
        is_high_vol = sessions >= params['P75_VOL_GA']
        gpps = row.get('calc_gpps', 0)
        is_high_eff = pd.notna(gpps) and gpps >= params['P75_EFF_GA']
        print(f"    Step 2a: is_high_vol={is_high_vol} (sessions={sessions} >= P75_VOL_GA={params['P75_VOL_GA']})")
        print(f"    Step 2b: is_high_eff={is_high_eff} (calc_gpps={gpps} >= P75_EFF_GA={params['P75_EFF_GA']})")
        if is_high_vol and is_high_eff:
            print(f"    -> Should be NEW_STAR_LAUNCH or RECOVERY_LAUNCH")
        elif is_high_vol and not is_high_eff:
            print(f"    -> Should be FIX_LANDING_PAGE")
    
    entity_type = row.get('calc_entity_type')
    print(f"    Step 3: calc_entity_type='{entity_type}' == 'PRODUCT'? {entity_type == 'PRODUCT'}")
    
    views = row.get('ga4item_views', 0)
    print(f"    Step 4: ga4item_views={views} >= MIN_ORGANIC_SESSIONS={params['MIN_ORGANIC_SESSIONS']}? {views >= params['MIN_ORGANIC_SESSIONS'] if pd.notna(views) else 'NaN'}")
