
import pandas as pd
import os

PATH = "c:/Users/Paweł/Documents/GitHub/Money Printing Machine/Output/Bushido/Normalized"

def check():
    feed = pd.read_csv(os.path.join(PATH, "feed_clean.csv"), dtype=str)
    ga4 = pd.read_csv(os.path.join(PATH, "ga4_items_clean.csv"), dtype=str)
    
    feed_ids = set(feed['id'])
    ga4_ids = set(ga4['Item ID'])
    
    common = feed_ids.intersection(ga4_ids)
    print(f"BUSHIDO DEBUG:")
    print(f"Feed IDs (Total {len(feed_ids)}): {list(feed_ids)[:5]}")
    print(f"GA4 IDs (Total {len(ga4_ids)}): {list(ga4_ids)[:5]}")
    print(f"INTERSECTION: {len(common)}")
    if len(common) > 0:
        print(f"Sample matches: {list(common)[:5]}")

if __name__ == "__main__":
    check()
