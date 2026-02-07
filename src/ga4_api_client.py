import os
import pandas as pd
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    DateRange,
    Dimension,
    Metric,
)

def fetch_ga4_data(credentials_path, property_id, start_date='2024-01-01', end_date='today', limit=100000):
    """
    Fetches GA4 data using the official API.
    Returns a DataFrame compatible with the pipeline's expected format.
    """
    
    print(f"Initializing GA4 Client with credentials: {credentials_path}")
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
    client = BetaAnalyticsDataClient()

    print(f"Requesting report for Property {property_id} ({start_date} to {end_date})...")
    request = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        dimensions=[
            Dimension(name="landingPagePlusQueryString"),
        ],
        metrics=[
            Metric(name="sessions"),
            Metric(name="totalUsers"),
            Metric(name="firstTimePurchasers"),
            Metric(name="ecommercePurchases"),
            Metric(name="purchaseRevenue"),
        ],
        limit=limit
    )

    try:
        response = client.run_report(request=request)
    except Exception as e:
        print(f"CRITICAL API ERROR: {e}")
        return pd.DataFrame()

    print(f"Report received. Processing {len(response.rows)} rows...")
    
    data = []
    for row in response.rows:
        data.append({
            "Landing page + query string": row.dimension_values[0].value,
            "Sessions": int(row.metric_values[0].value),
            "Users": int(row.metric_values[1].value),
            "First time purchasers": int(row.metric_values[2].value),
            "Purchases": int(row.metric_values[3].value),
            "Item revenue": float(row.metric_values[4].value)
        })

    if not data:
        print("No data found in GA4 response.")
        return pd.DataFrame()

    df = pd.DataFrame(data)
    
    # Rename columns to match CSV format expected by pipeline
    # CSV headers were: Landing page + query string,Sessions,Users,First time purchasers,Purchases,Item revenue
    # API data is already in this format via dict keys.
    
    print(f"Success. DataFrame shape: {df.shape}")
    return df
