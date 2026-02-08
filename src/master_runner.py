
import json
import os
import sys
from complete_pipeline import run_pipeline
from summary_engine import generate_summary

def main():
    print(">>> STARTING MASTER RUNNER <<<")
    
    # Files
    config_path = "business_logic.json"
    input_dir = "Input"
    output_dir = "Output"
    
    # Load Config
    if not os.path.exists(config_path):
        print(f"CRITICAL ERROR: Config file not found at {config_path}")
        return
        
    with open(config_path, "r", encoding="utf-8") as f:
        full_config = json.load(f)
        
    clients = full_config.get('clients', [])
    if not clients:
        print("No clients found in business_logic.json")
        return
        
    # Run for each brand
    for client in clients:
        brand_name = client['name']
        try:
            print(f"\n--- Processing {brand_name} ---")
            run_pipeline(brand_name, input_dir, output_dir, full_config)
            print(f"--- Finished {brand_name} ---\n")
        except Exception as e:
            print(f"!!! Error processing {brand_name}: {e}")
            import traceback
            traceback.print_exc()
            
    # Generate Summary
    print("\n>>> Generating Global Summary <<<")
    generate_summary(output_dir)
    print(">>> DONE <<<")

if __name__ == "__main__":
    main()
