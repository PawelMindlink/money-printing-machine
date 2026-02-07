
import os
import pandas as pd
import xml.etree.ElementTree as ET

INPUT_DIR = "c:/Users/Paweł/Documents/GitHub/Money Printing Machine/Input"

def identify_file(filepath):
    filename = os.path.basename(filepath)
    if filename.lower() in ['desktop.ini', 'agents.md', 'matryca priorytetów.md', 'matryca priorytetów.txt', 'linki do feedów produktowych.txt']:
        return "Config/Doc", "Shared"

    # Read first chunk
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            head = f.read(2048) # 2KB sample
    except:
        return "Error", "Unknown"

    brand = "Unknown"
    ftype = "Unknown"

    # BRAND DETECTION
    head_lower = head.lower()
    if "bushido" in head_lower:
        brand = "Bushido"
    elif "iiyama" in head_lower:
        brand = "Iiyama"
    elif "koszulkowy" in head_lower:
        brand = "Koszulkowy"

    # TYPE DETECTION
    if "<rss" in head_lower or "<channel>" in head_lower or "<item>" in head_lower:
        ftype = "XML Feed"
    elif "item id" in head_lower and "item revenue" in head_lower:
        ftype = "GA4 Items"
    elif "landing page" in head_lower and "sessions" in head_lower:
        ftype = "GA4 LandingPage"
    elif "landing page" in head_lower and "users" in head_lower: # Alternative GA4
        ftype = "GA4 LandingPage"
    elif "ad name" in head_lower and "amount spent" in head_lower:
        ftype = "Meta Ads"
    elif "campaign name" in head_lower and "impressions" in head_lower:
        ftype = "Meta Ads"
    elif "session source" in head_lower:
        ftype = "GA4 Source"
    
    return ftype, brand

print(f"{'FILENAME':<50} | {'TYPE':<20} | {'BRAND':<15}")
print("-" * 90)

for f in os.listdir(INPUT_DIR):
    path = os.path.join(INPUT_DIR, f)
    if os.path.isfile(path):
        ftype, brand = identify_file(path)
        print(f"{f:<50} | {ftype:<20} | {brand:<15}")
