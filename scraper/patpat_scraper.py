import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

def get_patpat_links(page_number):
    """Scrapes a single listing page and extracts all unique vehicle listing URLs."""
    # This URL filter targets the primary automotive listing context
    search_url = f"https://patpat.lk/en/sri-lanka/vehicle/car/toyota?page={page_number}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    links = []
    try:
        response = requests.get(search_url, headers=headers, timeout=15)
        if response.status_code != 200:
            return links
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Isolate individual vehicle anchor tags
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if "/vehicle/" in href and href not in links:
                if href.startswith("/"):
                    links.append(f"https://patpat.lk{href}")
                else:
                    links.append(href)
                    
    except Exception as e:
        print(f"\n   [Error] Connection interrupted on Search Page {page_number}: {e}")
        
    return links


def scrape_patpat_ad_details(ad_url):
    """
    Deep extracts vehicle technical specifications and price metrics.
    Supports both standard table definitions and custom DOM layouts seen in your screenshots.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # Initialize all 11 user-specified output data features
    data = {
        "URL": ad_url,
        "Price": "N/A",
        "Mileage": "N/A",
        "Engine/Motor Capacity": "N/A",
        "Transmission": "N/A",
        "Manufacturer": "N/A",
        "Model Year": "N/A",
        "Condition": "N/A",
        "Model": "N/A",
        "Fuel Type": "N/A",
        "Colour": "N/A",
        "Vehicle Type": "N/A"
    }
    
    try:
        response = requests.get(ad_url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')

        # =========================================================
        # 1. 🎯 TARGETED PRICE EXTRACTION ENGINE
        # =========================================================
        price_found = False
        
        # Strategy A: Target the custom transparent/gradient typography classes seen in your HTML source
        gradient_price = soup.find('span', class_=lambda c: c and 'bg-gradient-to-r' in c and 'text-transparent' in c)
        if gradient_price:
            raw_price_text = gradient_price.text.strip()
            # Clean up both standard notation formats ("Rs. 1,200,000" and "Rs: 1,200,000")
            cleaned = re.sub(r'Rs[:\.]?', '', raw_price_text, flags=re.IGNORECASE).strip()
            if cleaned:
                data['Price'] = cleaned
                price_found = True

        # Strategy B: Fallback global header check if the explicit span layout class differs
        if not price_found:
            for tag in soup.find_all(['span', 'div', 'h1', 'h2', 'h3']):
                text_str = tag.text.strip()
                if "Rs" in text_str and any(char.isdigit() for char in text_str) and len(text_str) < 35:
                    cleaned = re.sub(r'Rs[:\.]?', '', text_str, flags=re.IGNORECASE).strip()
                    if cleaned:
                        data['Price'] = cleaned
                        price_found = True
                        break

        # =========================================================
        # 2. ADVANCED SPECIFICATION FEATURE MATRIX PARSER
        # =========================================================
        
        # --- PATHWAY I: SIBLING ELEMENT PARSING (For class="label--..." formats) ---
        ikman_style_labels = soup.find_all('div', class_=lambda c: c and 'label--' in c)
        
        if ikman_style_labels:
            for label_div in ikman_style_labels:
                label_name = label_div.text.replace(":", "").strip()
                
                # Fetch matching feature container next to the structural label division
                val_div = label_div.find_next_sibling('div', class_=lambda c: c and 'value--' in c)
                if val_div:
                    val_text = val_div.text.strip()
                    
                    # Normalize source keys directly into your target data frame parameters
                    if label_name == "Mileage":
                        data["Mileage"] = val_text
                    elif "Engine capacity" in label_name:
                        data["Engine/Motor Capacity"] = val_text
                    elif "Transmission" in label_name:
                        data["Transmission"] = val_text
                    elif "Brand" in label_name:
                        data["Manufacturer"] = val_text
                    elif "Year of Manufacture" in label_name:
                        data["Model Year"] = val_text
                    elif "Condition" in label_name:
                        data["Condition"] = val_text
                    elif "Model" in label_name and "Year" not in label_name:
                        data["Model"] = val_text
                    elif "Fuel type" in label_name:
                        data["Fuel Type"] = val_text
                    elif "Colour" in label_name:
                        data["Colour"] = val_text
                    elif "Vehicle type" in label_name:
                        data["Vehicle Type"] = val_text

        # --- PATHWAY II: STANDARD DOM ELEMENT ROW PARSING ---
        else:
            for li in soup.find_all('li'):
                text_content = li.text.strip()
                
                if "Mileage" in text_content:
                    data["Mileage"] = text_content.replace("Mileage", "").strip()
                elif "Engine/Motor Capacity" in text_content:
                    data["Engine/Motor Capacity"] = text_content.replace("Engine/Motor Capacity", "").strip()
                elif "Transmission" in text_content:
                    data["Transmission"] = text_content.replace("Transmission", "").strip()
                elif "Manufacturer" in text_content:
                    data["Manufacturer"] = text_content.replace("Manufacturer", "").strip()
                elif "Model Year" in text_content:
                    data["Model Year"] = text_content.replace("Model Year", "").strip()
                elif "Condition" in text_content:
                    data["Condition"] = text_content.replace("Condition", "").strip()
                elif "Model" in text_content:
                    if "Model Year" not in text_content:
                        data["Model"] = text_content.replace("Model", "").strip()
                elif "Fuel Type" in text_content:
                    data["Fuel Type"] = text_content.replace("Fuel Type", "").strip()
                elif "Colour" in text_content:
                    data["Colour"] = text_content.replace("Colour", "").strip()
                elif "Vehicle Type" in text_content:
                    data["Vehicle Type"] = text_content.replace("Vehicle Type", "").strip()

        return data

    except Exception as e:
        print(f"   [Error] Aborted details processing for target URL {ad_url}: {e}")
        return None


# --- Core Dataset Pipeline Entry Point ---
if __name__ == "__main__":
    output_filename = "patpat_toyota_market_data.csv"
    master_link_pool = []
    
    # Scanning index catalog boundaries
    TOTAL_PAGES_TO_SCAN = 122
    
    print(f"--- Step 1: Mapping Catalog URLs Across {TOTAL_PAGES_TO_SCAN} Target Index Pages ---")
    for current_page in range(1, TOTAL_PAGES_TO_SCAN + 1):
        print(f"  Scanning Index Page {current_page}/{TOTAL_PAGES_TO_SCAN}... ", end="", flush=True)
        page_links = get_patpat_links(current_page)
        
        if not page_links:
            print("No items found. Halting mapping step safely.")
            break
        else:
            print(f"Discovered {len(page_links)} vehicle references.")
            master_link_pool.extend(page_links)
            master_link_pool = list(dict.fromkeys(master_link_pool)) # Dynamic deduplication
            
        time.sleep(1.0) # Standard request spacing pause
            
    total_unique_items = len(master_link_pool)
    print(f"\nPhase 1 Complete. Matrix Link Pool contains: {total_unique_items} entries.\n")
    
    print("--- Step 2: Executing deep item extraction engine ---")
    dataset_rows = []
    
    for index, url in enumerate(master_link_pool, start=1):
        print(f"[{index}/{total_unique_items}] Parsing data matrix for: {url}")
        
        ad_features = scrape_patpat_ad_details(url)
        if ad_features:
            dataset_rows.append(ad_features)
            
        time.sleep(1.2) # Active pacing buffer to secure stable connections
        
        # Checkpoint serialization sequence every 50 records
        if index % 50 == 0 or index == total_unique_items:
            if dataset_rows:
                df = pd.DataFrame(dataset_rows)
                
                # Order columns exactly matching your structured data layout specifications
                ordered_columns = [
                    "Price", "Mileage", "Engine/Motor Capacity", "Transmission", 
                    "Manufacturer", "Model Year", "Condition", 
                    "Model", "Fuel Type", "Colour", "Vehicle Type", "URL"
                ]
                df = df.reindex(columns=ordered_columns)
                df.to_csv(output_filename, index=False, encoding='utf-8')
                print(f"   [Checkpoint] Saved {len(df)} compiled records safely to disk -> {output_filename}")

    print(f"\n Clean matrix compiled successfully! Final dataset stored at: {output_filename}")