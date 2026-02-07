from ga4_api_client import fetch_ga4_data
import os

# Path to credentials found earlier
creds_path = r"c:\Users\Paweł\Documents\GitHub\ICP Research\Core\Configs\ga4_credentials.json"
# Koszulkowy Property ID (Need to extract from existing config or ask user)
# Checking existing files for property ID
property_id = "270928705"  # Koszulkowy Property ID from clients_config.json

print(f"Testing GA4 API connection with credentials: {creds_path}")

try:
    df = fetch_ga4_data(creds_path, property_id, start_date='2024-01-01', end_date='today', limit=100)
    if not df.empty:
        print("Success! Fetched data sample:")
        print(df.head())
        print(f"Total rows: {len(df)}")
        print("Columns:", df.columns.tolist())
    else:
        print("Connection successful but no data returned.")
except Exception as e:
    print(f"Error fetching GA4 data: {e}")
