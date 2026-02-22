import os
import pandas as pd
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    DateRange,
    Dimension,
    Metric,
)

def _get_client(credentials_path):
    """Initialize GA4 client with credentials."""
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
    return BetaAnalyticsDataClient()

def fetch_ga4_landing_pages(credentials_path, property_id, start_date='2025-02-06', end_date='2026-02-06', limit=100000):
    """
    Fetches GA4 Landing Page data using the official API.
    Returns a DataFrame compatible with the pipeline's expected format.
    """
    print(f"[LP] Fetching Landing Pages for Property {property_id}...")
    client = _get_client(credentials_path)
    
    data = []
    current_offset = 0
    batch_limit = 100000
    
    while True:
        print(f"[LP] Fetching batch offset {current_offset}...")
        request = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[
                Dimension(name="landingPage"),
            ],
            metrics=[
                Metric(name="sessions"),
                Metric(name="totalUsers"),
                Metric(name="firstTimePurchasers"),
                Metric(name="ecommercePurchases"),
                Metric(name="purchaseRevenue"),
            ],
            limit=batch_limit,
            offset=current_offset
        )

        try:
            response = client.run_report(request=request)
        except Exception as e:
            print(f"[LP] API ERROR: {e}")
            break

        if not response.rows:
            break

        for row in response.rows:
            data.append({
                "Landing page": row.dimension_values[0].value,
                "Sessions": int(row.metric_values[0].value),
                "Users": int(row.metric_values[1].value),
                "First time purchasers": int(row.metric_values[2].value),
                "Purchases": int(row.metric_values[3].value),
                "Purchase revenue": float(row.metric_values[4].value)
            })
            
        if len(response.rows) < batch_limit:
            break
            
        current_offset += batch_limit

    if not data:
        print("[LP] No data returned.")
        return pd.DataFrame()

    df = pd.DataFrame(data)
    print(f"[LP] Success: {len(df)} rows.")
    return df


def fetch_ga4_items(credentials_path, property_id, start_date='2025-02-06', end_date='2026-02-06', limit=100000):
    """
    Fetches GA4 Item-level data using the official API.
    Returns a DataFrame compatible with the pipeline's expected format.
    """
    print(f"[Items] Fetching Items for Property {property_id}...")
    client = _get_client(credentials_path)

    data = []
    current_offset = 0
    batch_limit = 100000
    
    while True:
        print(f"[Items] Fetching batch offset {current_offset}...")
        request = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            dimensions=[
                Dimension(name="itemId"),
                Dimension(name="itemName"),
            ],
            metrics=[
                Metric(name="itemsViewed"),
                Metric(name="itemsPurchased"),
                Metric(name="itemRevenue"),
            ],
            limit=batch_limit,
            offset=current_offset
        )

        try:
            response = client.run_report(request=request)
        except Exception as e:
            print(f"[Items] API ERROR: {e}")
            break

        if not response.rows:
            break

        for row in response.rows:
            data.append({
                "Item ID": row.dimension_values[0].value,
                "Item name": row.dimension_values[1].value,
                "Items viewed": int(row.metric_values[0].value),
                "Items purchased": int(row.metric_values[1].value),
                "Item revenue": float(row.metric_values[2].value)
            })
            
        if len(response.rows) < batch_limit:
            break
            
        current_offset += batch_limit

    if not data:
        print("[Items] No data returned.")
        return pd.DataFrame()

    df = pd.DataFrame(data)
    print(f"[Items] Success: {len(df)} rows.")
    return df


# Legacy alias for backward compatibility
def fetch_ga4_data(credentials_path, property_id, start_date='2025-02-06', end_date='2026-02-06', limit=100000):
    """Backward-compatible alias for fetch_ga4_landing_pages."""
    return fetch_ga4_landing_pages(credentials_path, property_id, start_date, end_date, limit)
