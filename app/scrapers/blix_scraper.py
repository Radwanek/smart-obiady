import re
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

STORES = {
    "Lidl": "https://blix.pl/sklep/lidl",
    "Biedronka": "https://blix.pl/sklep/biedronka",
    "Kaufland": "https://blix.pl/sklep/kaufland"
}

NON_FOOD_EXCLUDE = [
    'proszek do', 'płyn do naczyń', 'płyn do płukania', 'papier toalet', 
    'szampon', 'żel pod prysznic', 'pasta do zębów', 'znicz', 'skarpety', 
    'bluzka', 'kurtka', 'zabawk', 'karma dla psa', 'karma dla kota', 
    'kapsułki do prania', 'zawieszka do wc', 'maszynki do golenia', 
    'płyn do szyb', 'dezodorant', 'krem do rąk', 'tabletki do zmywarki', 
    'pieluchy', 'chusteczki nawilżane', 'baterie', 'znicze', 'wkład do znicza'
]

MEAT_KEYWORDS = [
    'kurczak', 'filet', 'udo', 'podudzi', 'skrzydeł', 'indyk', 'schab', 
    'karków', 'łopatk', 'polędwic', 'wołowin', 'mielon', 'żeberk', 'kaczk', 
    'łosoś', 'dorsz', 'pstrąg', 'krewet', 'makrel', 'ryb', 'szynk', 'kiełbas', 
    'parówk', 'boczek', 'kabanos', 'salami', 'pasztet'
]

DAIRY_KEYWORDS = [
    'ser ', 'ser,', 'sery', 'gouda', 'mozzarella', 'parmezan', 'grana padano', 
    'feta', 'twaróg', 'twarog', 'serek', 'mascarpone', 'ricotta', 'jogurt', 
    'skyr', 'kefir', 'śmietan', 'masło', 'mleko', 'jaj'
]

FRUIT_VEG_KEYWORDS = [
    'truskawk', 'borówk', 'jabłk', 'banan', 'winogron', 'mandarynk', 'cytryn', 
    'pomarańcz', 'malin', 'ziemniak', 'pieczark', 'papryk', 'cukini', 'brokuł', 
    'kalafior', 'marchew', 'cebul', 'czosnek', 'pomidor', 'fasol', 'por ', 
    'seler', 'kapust', 'dyni', 'szpinak', 'ogórk', 'sałat', 'awokado', 'gruszk',
    'arbuz', 'melon', 'brzoskwini', 'śliwk'
]

SNACK_KEYWORDS = [
    'chips', 'czips', 'pringles', 'lay', 'takis', 'cheetos', 'chrupk', 
    'orzech', 'czekolad', 'ciastk', 'wafl', 'baton', 'żelk', 'paluszk', 
    'krakers', 'nachos', 'popcorn', 'piernik', 'praliny', 'biscof', 'cukierk'
]

DRINK_KEYWORDS = [
    'sok', 'napój', 'cola', 'pepsi', 'fanta', 'sprite', 'woda ', 'woda,', 
    'mineralna', 'herbata', 'kawa ', 'kawy', 'piwo'
]

PANTRY_KEYWORDS = [
    'makaron', 'ryż', 'oliwa', 'olej ', 'passat', 'mąka', 'sos ', 'ketchup', 
    'majonez', 'przypraw', 'cukier', 'sól '
]

def classify_item(name: str) -> str:
    lower = name.lower()
    if any(ex in lower for ex in NON_FOOD_EXCLUDE):
        return ""
    if any(k in lower for k in MEAT_KEYWORDS):
        return "Mięso i ryby"
    if any(k in lower for k in DAIRY_KEYWORDS):
        return "Nabiał i sery"
    if any(k in lower for k in FRUIT_VEG_KEYWORDS):
        return "Warzywa i owoce"
    if any(k in lower for k in SNACK_KEYWORDS):
        return "Przekąski i słodycze"
    if any(k in lower for k in DRINK_KEYWORDS):
        return "Napoje"
    if any(k in lower for k in PANTRY_KEYWORDS):
        return "Baza i spiżarnia"
    return "Inne spożywcze"

KEYWORD_MAP = {
    'chips': ['chipsy', 'przekąski', 'chrupiące'],
    'czips': ['chipsy', 'przekąski', 'chrupiące'],
    'pringles': ['chipsy', 'pringles', 'przekąski'],
    'lay': ['chipsy', 'lays', 'przekąski'],
    'takis': ['chipsy', 'takis', 'ostre'],
    'cheetos': ['chrupki', 'chipsy', 'przekąski'],
    'truskawk': ['truskawki', 'owoce', 'świeże', 'słodkie'],
    'borówk': ['borówki', 'owoce', 'antyoksydanty'],
    'jabłk': ['jabłka', 'owoce', 'polskie'],
    'winogron': ['winogrona', 'owoce', 'słodkie'],
    'banan': ['banany', 'owoce', 'energia'],
    'mandarynk': ['mandarynki', 'cytrusy', 'owoce'],
    'cytryn': ['cytryny', 'cytrusy', 'witamina c'],
    'pomarańcz': ['pomarańcze', 'cytrusy', 'owoce'],
    'ziemniak': ['ziemniaki', 'tania baza', 'obiad'],
    'pieczark': ['pieczarki', 'grzyby', 'obiad'],
    'pomidor': ['pomidory', 'warzywa', 'świeże'],
    'ogórk': ['ogórki', 'warzywa', 'chrupiące'],
    'marchew': ['marchew', 'warzywa', 'zupa'],
    'papryk': ['papryka', 'warzywa', 'witaminy'],
    'brokuł': ['brokuły', 'warzywa', 'fit'],
    'kurczak': ['kurczak', 'drób', 'wysokie białko', 'airfryer'],
    'filet': ['filet', 'drób', 'czyste mięso', 'fit'],
    'indyk': ['indyk', 'drób', 'lekkostrawne'],
    'schab': ['schab', 'wieprzowina', 'kotlety'],
    'szynk': ['szynka', 'mięso', 'wędliny'],
    'łosoś': ['łosoś', 'ryba', 'omega-3', 'zdrowe tłuszcze'],
    'dorsz': ['dorsz', 'ryba', 'chuda ryba'],
    'masło': ['masło', 'tłuszcze', 'śniadanie'],
    'twaróg': ['twaróg', 'wysokie białko', 'fit'],
    'ser': ['ser', 'nabiał'],
    'jogurt': ['jogurt', 'nabiał', 'probiotyk'],
    'skyr': ['skyr', 'wysokie białko', 'fit'],
    'mleko': ['mleko', 'nabiał'],
    'czekolad': ['czekolada', 'słodycze', 'deser'],
    'ciastk': ['ciastka', 'słodycze'],
    'orzech': ['orzechy', 'zdrowe tłuszcze', 'przekąski'],
    'sok': ['soki', 'napoje', 'witaminy'],
    'cola': ['cola', 'napoje', 'gazowane'],
    'kawa': ['kawa', 'kofeina', 'poranek'],
    'herbata': ['herbata', 'napar', 'ciepło']
}

def generate_tags(name: str, category: str) -> List[str]:
    lower = name.lower()
    tags = set()
    
    if category == "Mięso i ryby":
        tags.add("mięso")
    elif category == "Nabiał i sery":
        tags.add("nabiał")
    elif category == "Warzywa i owoce":
        if any(w in lower for w in ['truskawk', 'jabłk', 'banan', 'winogron', 'borówk', 'cytryn', 'mandarynk', 'pomarańcz', 'owoce']):
            tags.add("owoce")
        else:
            tags.add("warzywa")
    elif category == "Przekąski i słodycze":
        tags.add("przekąski")
    elif category == "Napoje":
        tags.add("napoje")

    for kw, kw_tags in KEYWORD_MAP.items():
        if kw in lower:
            for t in kw_tags:
                tags.add(t)
                
    return sorted(list(tags))

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
        
    # Świeże warzywa i owoce
    if category == "Warzywa i owoce" or any(k in lower for k in ['truskawk', 'jabłk', 'banan', 'ziemniak', 'brokuł', 'pieczark', 'marchew', 'pomidor', 'kapust', 'papryk']):
        return {
            "nutri_score": "A",
            "clean_label": "CLEAN",
            "clean_label_desc": "🌿 100% naturalne witaminy i minerały prosto z natury"
        }
        
    # Przekąski i chipsy
    if category == "Przekąski i słodycze" or any(k in lower for k in ['chips', 'czips', 'czekolad', 'ciastk', 'wafl']):
        return {
            "nutri_score": "D",
            "clean_label": "PROCESSED",
            "clean_label_desc": "Przekąska rekreacyjna o wyższej zawartości tłuszczu lub cukru"
        }
        
    # Napoje słodzone
    if any(k in lower for k in ['cola', 'pepsi', 'fanta', 'sprite', 'napój']):
        return {
            "nutri_score": "E",
            "clean_label": "PROCESSED",
            "clean_label_desc": "Napój słodzony"
        }
        
    # Soki 100%
    if any(k in lower for k in ['sok 100%', 'sok jabłko', 'sok pomarańcz', 'tłoczony']):
        return {
            "nutri_score": "B",
            "clean_label": "CLEAN",
            "clean_label_desc": "🌿 Czysty sok owocowy bez dodatku cukru"
        }
        
    return {
        "nutri_score": "B",
        "clean_label": "CLEAN",
        "clean_label_desc": "Produkt o dobrym profilu odżywczym"
    }

def scrape_single_flyer(flyer_url: str, store_name: str, headers: dict) -> List[Dict[str, Any]]:
    results = []
    seen = set()
    try:
        with httpx.Client(headers=headers, follow_redirects=True, timeout=10.0) as client:
            fr = client.get(flyer_url)
            if fr.status_code != 200:
                return []
            fsoup = BeautifulSoup(fr.text, 'html.parser')
            
            # Zbuduj mapę stron do zdjęć wysokiej rozdzielczości
            page_images = {}
            for img in fsoup.find_all('img'):
                src = img.get('src') or img.get('data-src') or ''
                alt = img.get('alt', '')
                if 'imgproxy.blix.pl' in src and 'leaflet' in src:
                    page_match = re.search(r'strona\s+(\d+)', alt, re.IGNORECASE)
                    if page_match:
                        page_images[page_match.group(1)] = src
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
                tags = generate_tags(name, category)
                
                results.append({
                    "store": store_name,
                    "name": name,
                    "price": price,
                    "category": category,
                    "tags": tags,
                    "tags_str": ", ".join(tags),
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
        
    return results

def scrape_store_promotions(store_name: str, store_url: str, headers: dict) -> List[Dict[str, Any]]:
    try:
        with httpx.Client(headers=headers, follow_redirects=True, timeout=10.0) as client:
            r = client.get(store_url)
            if r.status_code != 200:
                return []
                
            soup = BeautifulSoup(r.text, 'html.parser')
            flyer_links = []
            for a in soup.find_all('a', href=True):
                href = a['href']
                if f"/sklep/{store_name.lower()}/gazetka/" in href:
                    if not href.startswith("http"):
                        href = "https://blix.pl" + href
                    flyer_links.append(href)
                    
            unique_flyers = list(dict.fromkeys(flyer_links))[:2]

        results = []
        with ThreadPoolExecutor(max_workers=2) as executor:
            flyer_results = executor.map(
                lambda url: scrape_single_flyer(url, store_name, headers),
                unique_flyers
            )
            for sublist in flyer_results:
                results.extend(sublist)
                
        return results
    except Exception as e:
        print(f"Error scraping {store_name}: {e}")
        return []

def scrape_all_promotions() -> List[Dict[str, Any]]:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    all_deals = []
    seen = set()
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        store_futures = [
            executor.submit(scrape_store_promotions, store_name, url, headers)
            for store_name, url in STORES.items()
        ]
        for f in store_futures:
            try:
                deals = f.result()
                for d in deals:
                    key = (d["store"], d["name"])
                    if key not in seen:
                        seen.add(key)
                        all_deals.append(d)
            except Exception as e:
                print(f"Błąd wątku sklepu: {e}")
                
    return all_deals
