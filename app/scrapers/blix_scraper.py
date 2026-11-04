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
    if any(ex in lower for ex in EXCLUDE_KEYWORDS):
        return ""
    if any(k in lower for k in MEAT_KEYWORDS):
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

def analyze_nutrition_and_clean_label(name: str, category: str) -> Dict[str, str]:
    lower = name.lower()
    
    # Przetwory mięsne z konserwantami
    if any(k in lower for k in ['parówk', 'sokoli', 'kabanos', 'kiełbas', 'pasztet', 'konserw', 'boczek wędz', 'salami']):
        return {
            "nutri_score": "D",
            "clean_label": "PROCESSED",
            "clean_label_desc": "Produkt przetworzony (może zawierać azotyn sodu E250 i fosforany)"
        }
        
    # Świeży drób (indyk, kurczak, filet)
    if any(k in lower for k in ['kurczak', 'filet', 'indyk', 'pierś', 'podudzi', 'udo z kurczaka']):
        return {
            "nutri_score": "A",
            "clean_label": "CLEAN",
            "clean_label_desc": "🌿 100% czyste mięso drobiowe, wysokie białko, bez chemii"
        }
        
    # Świeże ryby
    if any(k in lower for k in ['łosoś', 'dorsz', 'pstrąg', 'ryba', 'miruna', 'sandacz']):
        return {
            "nutri_score": "A",
            "clean_label": "CLEAN",
            "clean_label_desc": "🌿 Świeża ryba, zdrowe kwasy tłuszczowe Omega-3"
        }
        
    # Czysta wieprzowina i wołowina
    if any(k in lower for k in ['schab', 'polędwic', 'wołowin', 'łopatk', 'szynka wieprzowa']):
        return {
            "nutri_score": "B",
            "clean_label": "CLEAN",
            "clean_label_desc": "🌿 Czyste mięso surowe bez nastrzykiwania i dodatków"
        }
        
    # Wysokobiałkowy czysty nabiał
    if any(k in lower for k in ['skyr', 'twaróg', 'twarog', 'serek wiejski', 'jogurt naturalny', 'kefir']):
        return {
            "nutri_score": "A",
            "clean_label": "CLEAN",
            "clean_label_desc": "🌿 Czysty nabiał, bogate źródło białka, zero zagęszczaczy"
        }
        
    # Sery i masło
    if any(k in lower for k in ['ser ', 'ser,', 'sery', 'gouda', 'edam', 'mozzarella', 'masło']):
        return {
            "nutri_score": "C",
            "clean_label": "CLEAN",
            "clean_label_desc": "Tradycyjny nabiał, naturalne tłuszcze mleczne"
        }
        
    # Warzywa i baza
    if category == "Warzywa i baza" or any(k in lower for k in ['ziemniak', 'brokuł', 'pieczark', 'marchew', 'pomidor', 'kapust', 'papryk']):
        return {
            "nutri_score": "A",
            "clean_label": "CLEAN",
            "clean_label_desc": "🌿 100% naturalne warzywa, witaminy i minerały"
        }
        
    return {
        "nutri_score": "B",
        "clean_label": "CLEAN",
        "clean_label_desc": "Produkt o dobrym profilu odżywczym"
    }

def scrape_store_promotions(store_name: str, store_url: str, client: httpx.Client) -> List[Dict[str, Any]]:
    results = []
    seen = set()
    
    try:
        r = client.get(store_url, timeout=12.0)
        if r.status_code != 200:
            return []
            
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Znajdź gazetki
        flyer_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if f"/sklep/{store_name.lower()}/gazetka/" in href:
                if not href.startswith("http"):
                    href = "https://blix.pl" + href
                flyer_links.append(href)
                
        unique_flyers = list(dict.fromkeys(flyer_links))[:2]
        
        for flyer_url in unique_flyers:
            try:
                fr = client.get(flyer_url, timeout=12.0)
                if fr.status_code != 200:
                    continue
                fsoup = BeautifulSoup(fr.text, 'html.parser')
                
                # Zbuduj mapę stron do zdjęć wysokiej rozdzielczości
                page_images = {}
                for img in fsoup.find_all('img'):
                    src = img.get('src') or img.get('data-src') or ''
                    alt = img.get('alt', '')
                    if 'imgproxy.blix.pl' in src and 'leaflet' in src:
                        # Szukaj numeru strony w alt
                        page_match = re.search(r'strona\s+(\d+)', alt, re.IGNORECASE)
                        if page_match:
                            p_num = page_match.group(1)
                            page_images[p_num] = src
                        elif "1" not in page_images:
                            page_images["1"] = src
                            
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
                        
                    page_num = str(o.get('data-page-number', '1'))
                    image_url = page_images.get(page_num) or page_images.get('1') or ''
                    
                    analysis = analyze_nutrition_and_clean_label(name, category)
                    
                    results.append({
                        "store": store_name,
                        "name": name,
                        "price": price,
                        "category": category,
                        "image_url": image_url,
                        "nutri_score": analysis["nutri_score"],
                        "clean_label": analysis["clean_label"],
                        "clean_label_desc": analysis["clean_label_desc"],
                        "date_start": o.get('data-date-start', ''),
                        "date_end": o.get('data-date-end', ''),
                        "leaflet_id": o.get('data-leaflet-id', ''),
                        "page_number": page_num
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
