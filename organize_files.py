
import os
import shutil

INPUT_DIR = "c:/Users/Paweł/Documents/GitHub/Money Printing Machine/Input"

# Define the mapping based on previous scan
FILE_MAP = {
    "Bushido": {
        "ga4_items.csv": "Bushido Item Breakdown GA4.csv", 
        "ga4_lp.csv": "download (3).csv",
        "meta_ads.csv": "Untitled-report-Feb-6-2025-to-Feb-6-2026 (1).csv",
        "product_feed.xml": "facebookads_16dafb891c459c40b5bb164a 1.txt"
    },
    "Iiyama": {
        "ga4_items.csv": "download (4).csv",
        "ga4_lp.csv": "download (5).csv",
        "meta_ads.csv": "Untitled-report-Feb-6-2025-to-Feb-6-2026.csv",
        "product_feed.xml": "facebook353re3534sdfdfdef.txt"
    },
    "Koszulkowy": {
        "ga4_items.csv": "download (10).csv", # Using newer/larger file if duplicate
        "ga4_lp.csv": "download (6).csv",
        "meta_ads.csv": "Export-Raport.csv",
        "product_feed.xml": "facebook-products-feed_id-1.txt"
    }
}

def organize():
    print("--- ORGANIZING INPUT FILES ---")
    
    for brand, files in FILE_MAP.items():
        brand_dir = os.path.join(INPUT_DIR, brand)
        if not os.path.exists(brand_dir):
            os.makedirs(brand_dir)
            print(f"Created directory: {brand_dir}")
        
        for new_name, old_name in files.items():
            src = os.path.join(INPUT_DIR, old_name)
            dst = os.path.join(brand_dir, new_name)
            
            if os.path.exists(src):
                # Copy instead of move for safety in this step, or move? 
                # User asked to organize. Move is cleaner.
                shutil.move(src, dst)
                print(f"Moved [{brand}] {old_name} -> {new_name}")
            else:
                print(f"WARNING: Source file not found: {old_name}")

if __name__ == "__main__":
    organize()
