"""
Analyze Gold Standard file to see session distribution.
Goal: determine if 'sessions >= 50' filter is safe or too aggressive.
"""
import csv, json

GOLD_STD = r"c:\Users\Paweł\Documents\GitHub\Money Printing Machine\Input\Gold Standard 09.02.26 Iiyama_Growth_Opportunities - Iiyama_Growth_Opportunities.csv"

print(f"Analyzing: {GOLD_STD}")

with open(GOLD_STD, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

total_rows = len(rows)
sess_gt_0 = 0
sess_gt_50 = 0
sess_gt_300 = 0
max_sess = 0

for row in rows:
    sess = float(row.get("ga4lp_sessions", 0) or 0)
    if sess > max_sess: max_sess = sess
    
    if sess > 0: sess_gt_0 += 1
    if sess >= 50: sess_gt_50 += 1
    if sess >= 300: sess_gt_300 += 1

print(f"Total rows: {total_rows}")
print(f"Sessions > 0: {sess_gt_0} ({sess_gt_0/total_rows*100:.1f}%)")
print(f"Sessions >= 50: {sess_gt_50} ({sess_gt_50/total_rows*100:.1f}%)")
print(f"Sessions >= 300: {sess_gt_300} ({sess_gt_300/total_rows*100:.1f}%)")
print(f"Max sessions: {max_sess}")

if sess_gt_50 == 0:
    print("\nWARNING: No rows passed the >= 50 filter in Gold Standard!")
    print("Filter is likely too strict for this dataset.")
else:
    print(f"\nFilter >= 50 retains {sess_gt_50} rows. Seem safe?")
