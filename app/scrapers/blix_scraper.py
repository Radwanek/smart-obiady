import re
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any

STORES = {
    "Lidl": "https://blix.pl/sklep/lidl",
    "Biedronka": "https://blix.pl/sklep/biedronka",
    "Kaufland": "https://blix.pl/sklep/kaufland"
}

MEAT_KEYWORDS = [
    'kurczak', 'filet', 'udo', 'podudzi', 'skrzydeł', 'indyk', 'schab', 
    'karków', 'łopatk', 'polędwic', 'wołowin', 'mielon', 'żeberk', 'kaczk', 
    'łosoś', 'dorsz', 'pstrąg', 'krewet', 'makrel', 'ryb', 'szynk'
]

DAIRY_KEYWORDS = [
    'ser ', 'ser,', 'sery', 'gouda', 'mozzarella', 'parmezan', 'grana padano', 
    'feta', 'twaróg', 'twarog', 'serek', 'mascarpone', 'ricotta', 'jogurt', 
    'skyr', 'kefir', 'śmietan', 'masło', 'mleko'
]

VEG_KEYWORDS = [
    'ziemniak', 'pieczark', 'papryk', 'cukini', 'brokuł', 'kalafior', 
    'marchew', 'cebul', 'czosnek', 'pomidor', 'passat', 'fasol', 'por ', 
    'seler', 'kapust', 'dyni', 'szpinak'
]

EXCLUDE_KEYWORDS = [
    'kawa ', 'kawa,', 'kawy', 'kawa mielona', 'kawa ziarnista', 'herbata', 
    'piwo', 'wino', 'wódka', 'whisky', 'chips', 'czips', 'czekolad', 
    'ciastk', 'napój', 'cola', 'sok ', 'proszek', 'płyn', 'papier toalet', 
    'szampon', 'karma dla', 'znicz', 'skarpety', 'bluzka', 'kurtka', 'zabawk'
]

def classify_item(name: str) -> str:
    lower = name.lower()
    
    # Check exclusion
    if any(ex in lower for ex in EXCLUDE_KEYWORDS):
        return ""
        
    if any(k in lower for k in MEAT_KEYWORDS):
        # Prevent "kawa mielona" or "deser" false match
        if "kawa" in lower or "karma" in lower:
            return ""
        return "Mięso i ryby"
        
    if any(k in lower for k in DAIRY_KEYWORDS):
        if "piwo" in lower or "budweiser" in lower:
            return ""
        return "Nabiał i sery"
        
    if any(k in lower for k in VEG_KEYWORDS):
        return "Warzywa i baza"
        
    return ""

def scrape_store_promotions(store_name: str, store_url: str, client: httpx.Client) -> List[Dict[str, Any]]:
    results = []
    seen = set()
    
    try:
        r = client.get(store_url, timeout=12.0)
        if r.status_code != 200:
            return []
            
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Find latest flyers
        flyer_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if f"/sklep/{store_name.lower()}/gazetka/" in href:
                if not href.startswith("http"):
                    href = "https://blix.pl" + href
                flyer_links.append(href)
                
        # Take the top 2 active flyers
        unique_flyers = list(dict.fromkeys(flyer_links))[:2]
        
        for flyer_url in unique_flyers:
            try:
                fr = client.get(flyer_url, timeout=12.0)
                if fr.status_code != 200:
                    continue
                fsoup = BeautifulSoup(fr.text, 'html.parser')
                offers = fsoup.select('[data-name]')
                
                for o in offers:
                    name = o.get('data-name', '').strip()
                    if not name or name in seen:
                        continue
                        
                    category = classify_item(name)
                    if not category:
                        continue
                        
                    seen.add(name)
                    price_val = o.get('data-price')
                    if price_val and price_val.isdigit() and int(price_val) > 0:
                        price = f"{int(price_val)/100:.2f} zł"
                    else:
                        price = "Supercena w gazetce"
                        
                    results.append({
                        "store": store_name,
                        "name": name,
                        "price": price,
                        "category": category,
                        "date_start": o.get('data-date-start', ''),
                        "date_end": o.get('data-date-end', ''),
                        "leaflet_id": o.get('data-leaflet-id', '')
                    })
            except Exception as fe:
                print(f"Error scraping flyer {flyer_url}: {fe}")
                
    except Exception as e:
        print(f"Error scraping {store_name}: {e}")
        
    return results

def scrape_all_promotions() -> List[Dict[str, Any]]:
    all_deals = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    with httpx.Client(headers=headers, follow_redirects=True) as client:
        for store_name, url in STORES.items():
            deals = scrape_store_promotions(store_name, url, client)
            all_deals.extend(deals)
            
    return all_deals
