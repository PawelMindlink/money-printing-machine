
import pandas as pd
import os

GOLD_STD = r"c:\Users\Paweł\Documents\GitHub\Money Printing Machine\Input\Gold Standard 09.02.26 Iiyama_Growth_Opportunities - Iiyama_Growth_Opportunities.csv"

if os.path.exists(GOLD_STD):
    df = pd.read_csv(GOLD_STD)
    if 'calc_priority' in df.columns:
        print("--- GOLD STANDARD DISTRIBUTION ---")
        print(df['calc_priority'].value_counts().sort_index())
    else:
        print("calc_priority not found in Gold Standard")
else:
    print(f"File not found: {GOLD_STD}")
