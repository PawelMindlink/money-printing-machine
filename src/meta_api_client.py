import os
import requests
import pandas as pd
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

META_GRAPH_URL = "https://graph.facebook.com/v21.0"

def fetch_meta_ads_data(account_id: str, date_from: str, date_to: str, access_token: str = None) -> pd.DataFrame:
    """
    Fetches Ad-level performance and destination URLs from Meta Graph API.
    Handles pagination automatically.
    
    Args:
        account_id: Meta Ads Account ID (should start with 'act_')
        date_from: Start date in YYYY-MM-DD
        date_to: End date in YYYY-MM-DD
        access_token: Meta User Access Token. If None, expects META_ACCESS_TOKEN in env.
        
    Returns:
        pd.DataFrame containing columns:
        ['Date', 'Ad ID', 'Ad name', 'Link (ad settings)', 'Amount spent (PLN)', 'Purchases', 'Purchases conversion value']
    """
    token = access_token or os.environ.get("META_ACCESS_TOKEN")
    if not token:
        raise ValueError("META_ACCESS_TOKEN not found in environment variables.")
        
    if not account_id.startswith('act_'):
        account_id = f"act_{account_id}"

    # Prepare fields and parameters
    # Note: 'website_url' requires fetching ad creative details separately or via insights
    # However, in Insights API we can get 'ad_name', 'ad_id', 'spend', 'actions', 'action_values'
    # For 'website_url', we need 'adcreative' -> 'object_story_spec', or just rely on 'outbound_clicks' if possible,
    # but to match the previous CSV 'Link (ad settings)', we need the creative url.
    # To be efficient, we'll fetch insights breakdown by Ad, then fetch creatives for those ads.
    
    fields = [
        "date_start",
        "ad_id",
        "ad_name",
        "spend",
        "actions",
        "action_values"
    ]
    
    params = {
        "access_token": token,
        "level": "ad",
        "time_range": f'{{"since":"{date_from}","until":"{date_to}"}}',
        "fields": ",".join(fields),
        "limit": 500  # API handles pagination
    }

    url = f"{META_GRAPH_URL}/{account_id}/insights"
    
    all_insights = []
    
    print(f"[META API] Fetching insights for account {account_id} from {date_from} to {date_to}...")
    
    # 1. Fetch Insights (Spend, Purchases, Revenue)
    retries = 0
    max_retries = 10
    while url:
        response = requests.get(url, params=params if 'limit' in params else None)  # params are baked into next url
        
        if response.status_code in [403, 429]:
            print(f"[META API] Rate limit reached during insights fetch. Sleeping 60s... (Attempt {retries+1}/{max_retries})")
            time.sleep(60)
            retries += 1
            if retries > max_retries:
                print("[META API] Max retries reached. Breaking.")
                break
            continue
            
        if response.status_code != 200:
            print(f"[META API] Error: {response.status_code} - {response.text}")
            break
            
        retries = 0
        data = response.json()
        all_insights.extend(data.get('data', []))
        
        # Pagination
        url = data.get('paging', {}).get('next')
        params = {} # Clear params because 'next' url already contains them

    if not all_insights:
        print("[META API] No insights data returned.")
        return pd.DataFrame()

    print(f"[META API] Retrieved {len(all_insights)} insight records. Processing metrics...")

    processed_data = []
    unique_ad_ids = set()
    
    for row in all_insights:
        spend = float(row.get('spend', 0.0))
        ad_id = row.get('ad_id')
        ad_name = row.get('ad_name')
        
        # Parse actions
        purchases = 0
        actions = row.get('actions', [])
        for action in actions:
            if action.get('action_type') == 'purchase':
                purchases = int(action.get('value', 0))
                break
                
        # Parse action values
        revenue = 0.0
        action_values = row.get('action_values', [])
        for val in action_values:
            if val.get('action_type') == 'purchase':
                revenue = float(val.get('value', 0.0))
                break
                
        processed_data.append({
            'Date': row.get('date_start'),
            'Ad ID': ad_id,
            'Ad name': ad_name,
            'Amount spent (PLN)': spend,
            'Purchases': purchases,
            'Purchases conversion value': revenue
        })
        unique_ad_ids.add(ad_id)

    df_insights = pd.DataFrame(processed_data)
    
    # 2. Fetch Ad Creatives (to get Destination URL / Link)
    print(f"[META API] Fetching creative URLs for {len(unique_ad_ids)} unique ads...")
    ad_urls = {}
    
    # Batch fetch ads limits to 50 per request usually, so we chunk it
    ad_ids_list = list(unique_ad_ids)
    chunk_size = 50
    
    for i in range(0, len(ad_ids_list), chunk_size):
        chunk = ad_ids_list[i:i+chunk_size]
        
        # We fetch the creative connected to the ad
        ads_params = {
            "access_token": token,
            "ids": ",".join(chunk),
            "fields": "creative{object_story_spec,asset_feed_spec,url_tags}"
        }
        
        chunk_retries = 0
        while chunk_retries <= max_retries:
            try:
                res = requests.get(f"{META_GRAPH_URL}/", params=ads_params)
                
                if res.status_code in [403, 429]:
                    print(f"[META API] Rate limit fetching creatives. Sleeping 60s... (Attempt {chunk_retries+1}/{max_retries})")
                    time.sleep(60)
                    chunk_retries += 1
                    continue
                    
                if res.status_code == 200:
                    ads_data = res.json()
                    for a_id, a_data in ads_data.items():
                        if isinstance(a_data, dict):
                            creative = a_data.get('creative', {})
                            link = extract_link_from_creative(creative)
                            if link:
                                ad_urls[a_id] = link
                    break # Success, break retry loop
                else:
                    print(f"[META API] Warning fetching creatives: HTTP {res.status_code}")
                    break
                    
            except Exception as e:
                print(f"[META API] Error fetching creatives: {e}")
                time.sleep(5)
                chunk_retries += 1
            
    # Map URLs back to the dataframe
    df_insights['Link (ad settings)'] = df_insights['Ad ID'].map(ad_urls)
    
    # Fill missing with empty string
    df_insights['Link (ad settings)'] = df_insights['Link (ad settings)'].fillna('')
    
    print(f"[META API] Successfully returned {len(df_insights)} Meta Ads records with URLs.")
    return df_insights

def extract_link_from_creative(creative_node: dict) -> str:
    """Helper to deeply extract the landing page URL from a Meta ad creative."""
    # This covers the most common formats: Link, Carousel, Catalog Sales
    if not creative_node: return ""
    
    spec = creative_node.get('object_story_spec', {})
    
    # Single image / video link data
    link_data = spec.get('link_data', {})
    if 'link' in link_data:
        return link_data['link']
        
    video_data = spec.get('video_data', {})
    if 'call_to_action' in video_data:
        cta_value = video_data['call_to_action'].get('value', {})
        if 'link' in cta_value:
            return cta_value['link']
            
    # Carousel (we just take the first card's link as a proxy, or domain)
    template_data = spec.get('template_data', {})
    if 'link' in template_data:
        return template_data['link']
        
    # Asset feed spec (dynamic ads)
    asset_feed = creative_node.get('asset_feed_spec', {})
    link_urls = asset_feed.get('link_urls', [])
    if link_urls and len(link_urls) > 0:
        return link_urls[0].get('website_url', '')

    return ""
