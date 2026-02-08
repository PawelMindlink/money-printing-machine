import os
import subprocess
import json
import sys

def run_command(command):
    print(f"\n[EXEC] {command}")
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f"[ERROR] Command failed: {command}")
        return False
    return True

def main():
    # 1. Load Brands
    with open("business_logic.json", "r", encoding="utf-8") as f:
        config = json.load(f)
        
    brands = [c['name'] for c in config['clients']]
    print(f"Starting Production Run for: {brands}")
    
    for brand in brands:
        print(f"\n{'='*60}")
        print(f"PROCESSING BRAND: {brand.upper()}")
        print(f"{'='*60}")
        
        # Process 1: Ad Analysis
        cmd1 = f"python src/ad_analysis.py {brand}"
        if not run_command(cmd1):
            continue
            
        # Process 2: Growth Opportunities (MSC-ALGO)
        cmd2 = f"python src/complete_pipeline.py {brand}"
        if not run_command(cmd2):
            continue
            
    print("\n[DONE] Production Suite Completed.")

if __name__ == "__main__":
    main()
