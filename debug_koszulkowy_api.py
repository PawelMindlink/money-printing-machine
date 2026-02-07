import os
import pandas as pd
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest,
    DateRange,
    Dimension,
    Metric,
)
import traceback

# Setup credentials
CREDENTIALS_PATH = os.environ.get("GA4_CREDS_PATH", r"c:\Users\Paweł\Documents\GitHub\ICP Research\Core\Configs\ga4_credentials.json")
PROPERTY_ID = '270928705'  # Koszulkowy

def test_items_fetch():
    print(f"Testing GA4 Items Fetch for Property {PROPERTY_ID}...")
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = CREDENTIALS_PATH
    client = BetaAnalyticsDataClient()

    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date='2024-01-01', end_date='today')],
        dimensions=[
            Dimension(name="itemId"),
            Dimension(name="itemName"),
        ],
        metrics=[
            Metric(name="itemsViewed"),
            Metric(name="itemsPurchased"),
            Metric(name="itemRevenue"),
        ],
        limit=1000
    )

    try:
        response = client.run_report(request=request)
        print("Success! Response received.")
        print(f"Row count: {len(response.rows)}")
        if len(response.rows) > 0:
            print("First row:", response.rows[0])
    except Exception as e:
        print("API ERROR CAUGHT:")
        traceback.print_exc()

if __name__ == "__main__":
    test_items_fetch()
