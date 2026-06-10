import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os

def get_listing_links_from_page(page_number):
    """Scrapes a single search results page and extracts ad links."""
    search_url = f"https://riyasewana.com/search?page={page_number}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    links = []
    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return links
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for ad links containing '/buy/'
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if "/buy/" in href:
                if href.startswith("//"):
                    full_url = f"https:{href}"
                elif href.startswith("/"):
                    full_url = f"https://riyasewana.com{href}"
                else:
                    full_url = href
                
                if full_url not in links:
                    links.append(full_url)
                    
    except Exception as e:
        print(f"\n   [Error] Exception on page {page_number}: {e}")
        
    return links


def scrape_ad_details(ad_url):
    """Scrapes all specific structural details and optional specs from an ad page."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(ad_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        data = {"URL": ad_url}

        # 1. Title Extraction
        title_div = soup.find('div', class_='vmore-title')
        if title_div and title_div.find('h1'):
            data['Title'] = title_div.find('h1').text.strip()

        # 2. Price Extraction
        price_amount = soup.find('div', class_='price-amount')
        if price_amount:
            data['Price'] = price_amount.text.strip()

        # 3. Dynamic Spec Map Rows
        detail_rows = soup.find_all('div', class_='detail-row')
        for row in detail_rows:
            label_span = row.find('span', class_='detail-label')
            value_span = row.find('span', class_='detail-value')
            if label_span and value_span:
                key = label_span.text.replace(':', '').strip()
                value = value_span.text.strip()
                data[key] = value

        # 4. Optional Features Chips Array
        options_list = soup.find('div', class_='options-list')
        if options_list:
            chips = options_list.find_all('span', class_='option-chip')
            data['Options'] = [chip.text.strip() for chip in chips]
        else:
            data['Options'] = [] 

        return data

    except Exception as e:
        print(f"Error scraping details for {ad_url}: {e}")
        return None


# --- Core Execution Pipeline ---
if __name__ == "__main__":
    output_filename = "riyasewana_vehicles.csv"
    all_target_links = []
    
    current_page = 1
    consecutive_empty_pages = 0
    
    print("--- Step 1: Scanning ALL active index pages across the site ---")
    while True:
        print(f"Scanning Search Page {current_page}... ", end="", flush=True)
        page_links = get_listing_links_from_page(current_page)
        
        if not page_links:
            consecutive_empty_pages += 1
            print("Empty page.")
            # If 2 pages in a row return absolutely no new car links, we've definitively reached the end.
            if consecutive_empty_pages >= 2:
                print("Reached the final page of listings.")
                break
        else:
            consecutive_empty_pages = 0
            print(f"Found {len(page_links)} links.")
            all_target_links.extend(page_links)
            
            # De-duplicate links continuously
            all_target_links = list(dict.fromkeys(all_target_links))
            
        current_page += 1
        time.sleep(0.75) # Moderate spacing delay for index scraper
        
    total_links = len(all_target_links)
    print(f"\nTotal unique item URLs gathered across all pages: {total_links}\n")
    
    print("--- Step 2: Running Deep Feature Scraper ---")
    scraped_results = []
    
    for index, url in enumerate(all_target_links, start=1):
        print(f"[{index}/{total_links}] Extracting attributes: {url}")
        
        ad_data = scrape_ad_details(url)
        if ad_data:
            scraped_results.append(ad_data)
            
        # VERY IMPORTANT: Keep a 1-second sleep so their hosting firewall doesn't drop your 
        # connection or block your local IP address during long collection intervals.
        time.sleep(1.0)
        
        # Incremental Save: Saves progress to CSV every 50 records collected so you never lose data if it stops.
        if index % 50 == 0 or index == total_links:
            if scraped_results:
                df = pd.DataFrame(scraped_results)
                df.to_csv(output_filename, index=False, encoding='utf-8')
                print(f"   [Backup Saved] Progress written to {output_filename}")

    print(f"\n Generation Complete! Clean dataset with all features generated: {output_filename}")