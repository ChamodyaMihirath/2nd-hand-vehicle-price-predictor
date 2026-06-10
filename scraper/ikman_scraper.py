import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

def get_ikman_links(location, page_number):
    """Scrapes individual ad links for Toyota cars inside a specific geographic hub."""
    search_url = f"https://ikman.lk/en/ads/{location}/cars/toyota?page={page_number}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    links = []
    try:
        response = requests.get(search_url, headers=headers, timeout=15)
        if response.status_code != 200:
            return links
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Target ikman single ad relative paths (/en/ad/...)
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if "/en/ad/" in href:
                full_url = f"https://ikman.lk{href}" if href.startswith("/") else href
                if full_url not in links:
                    links.append(full_url)
                    
    except Exception as e:
        print(f"\n   [Error] Connection failed on {location} Page {page_number}: {e}")
        
    return links


def scrape_ikman_ad_details(ad_url):
    """Deep extracts specifications using fuzzy regex class matching to shield against dynamic CSS re-compiling."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(ad_url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        data = {"URL": ad_url}

        # 1. Capture Header Title
        title_h1 = soup.find('h1', class_=re.compile(r'title--'))
        if not title_h1: title_h1 = soup.find('h1')  # Fallback selector
        if title_h1:
            data['Title'] = title_h1.text.strip()

        # 2. Capture Advertised Price
        price_div = soup.find('div', class_=re.compile(r'amount--'))
        if price_div:
            data['Price'] = price_div.text.strip()

        # 3. Zip Extraction for Specification Tables (Mileage, Transmission, Engine Capacity, Year)
        labels = soup.find_all('div', class_=re.compile(r'label--'))
        values = soup.find_all('div', class_=re.compile(r'value--'))
        
        for label, val in zip(labels, values):
            key = label.text.replace(':', '').strip()
            value = val.text.strip()
            if key:
                data[key] = value

        return data

    except Exception as e:
        print(f"   [Error] Skipped page processing for {ad_url}: {e}")
        return None


# --- Core Dataset Aggregator Engine ---
if __name__ == "__main__":
    output_filename = "ikman_toyota_market_data.csv"
    master_link_pool = []
    
    # Segmented targets list to bypass platform pagination limits completely
    locations_pool = ["colombo", "gampaha", "kandy", "kurunegala", "kalutara", "galle", "sri-lanka"]
    
    print("--- Step 1: Initiating Hub-Segmented Index Scanner ---")
    for loc in locations_pool:
        print(f"\nTargeting Location Hub: [{loc.upper()}]")
        current_page = 1
        consecutive_empty_count = 0
        
        while True:
            # HARD CAP SAFETY: If it passes ikman's server index cap, break and move to next location pool
            if current_page > 97:
                print(f"  Reached ikman's hard limit of 97 pages for {loc}. Moving to next pool.")
                break
                
            print(f"  Scanning Page {current_page}... ", end="", flush=True)
            page_links = get_ikman_links(loc, current_page)
            
            if not page_links:
                consecutive_empty_count += 1
                print("Empty block profile.")
                if consecutive_empty_count >= 2:
                    break
            else:
                consecutive_empty_count = 0
                
                # Filter out what we already gathered to see if ikman started looping old data early
                new_links = [link for link in page_links if link not in master_link_pool]
                
                if current_page > 1 and len(new_links) == 0:
                    print("Only duplicate links returned from the wall. Breaking out of location early.")
                    break
                    
                print(f"Extracted {len(page_links)} links ({len(new_links)} brand new).")
                master_link_pool.extend(page_links)
                master_link_pool = list(dict.fromkeys(master_link_pool))
                
            current_page += 1
            time.sleep(1.2)  # Maintain healthy request rhythm between index changes
            
    total_unique_items = len(master_link_pool)
    print(f"\nLink Scan Completed. Total Unique Toyota Ads found: {total_unique_items}\n")
    
    print("--- Step 2: Executing Data Extraction Pipeline ---")
    dataset_rows = []
    
    for index, url in enumerate(master_link_pool, start=1):
        print(f"[{index}/{total_unique_items}] Processing ad: {url}")
        
        ad_features = scrape_ikman_ad_details(url)
        if ad_features:
            dataset_rows.append(ad_features)
            
        # Standardize pause to secure long-running connection windows from server resets
        time.sleep(1.5)
        
        # Safe Checkpoint Save: writes data out incrementally every 50 loops
        if index % 50 == 0 or index == total_unique_items:
            if dataset_rows:
                df = pd.DataFrame(dataset_rows)
                df.to_csv(output_filename, index=False, encoding='utf-8')
                print(f"   [Incremental Save] Backup written to disk: {output_filename} ({len(df)} records total)")

    print(f"\n Dataset Compilation Completed successfully! Final matrix saved at: {output_filename}")