import json
import httpx
from typing import Dict, Any, List, Optional
from app.config import GEMINI_API_KEY
from app.database import search_active_promotions, get_recent_promotions

CANDIDATE_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash"
]

def ask_shopping_assistant(user_message: str) -> Dict[str, Any]:
    if not GEMINI_API_KEY:
        return {
            "reply": "Klucz API Gemini nie jest skonfigurowany na serwerze. Dodaj GEMINI_API_KEY w panelu Render.",
            "matched_deals": []
        }
        
    cleaned_query = user_message.strip()
    if not cleaned_query:
        return {
            "reply": "Napisz, jakiego produktu lub dania szukasz (np. *kurczak*, *łosoś*, *twaróg*, *tani obiad*), a sprawdzę gazetki Lidla, Biedronki i Kauflandu!",
            "matched_deals": []
        }
        
    # Szukaj dopasowanych aktywnych promocji
    matched_deals = search_active_promotions(cleaned_query, limit=20)
    
    # Jeśli zapytanie jest ogólne (np. "co na obiad", "najtańsze mięso"), weź topowe aktywne oferty
    if len(matched_deals) < 3:
        general_deals = get_recent_promotions(limit=25, only_active=True)
        # Połącz i zdeduplikuj
        seen_keys = {(d["store"], d["name"]) for d in matched_deals}
        for gd in general_deals:
            key = (gd["store"], gd["name"])
            if key not in seen_keys:
                matched_deals.append(gd)
                seen_keys.add(key)
            if len(matched_deals) >= 20:
                break

    deals_summary = []
    for d in matched_deals[:15]:
        deals_summary.append({
            "sklep": d.get("store"),
            "produkt": d.get("name"),
            "cena": d.get("price"),
            "kategoria": d.get("category"),
            "waznosc": d.get("date_badge", d.get("date_end", "aktualna")),
            "nutri_score": d.get("nutri_score", "A"),
            "czysty_sklad": d.get("clean_label", "CLEAN"),
            "wymaga_aplikacji": d.get("is_app_deal", False)
        })

    prompt = f"""
Jesteś inteligentnym, osobistym Asystentem Zakupów w aplikacji "Smart Obiady".
Profil użytkowników:
- Para (2 osoby: chłopak i dziewczyna).
- Bardzo ścisły budżet: 600 ZŁ NA MIESIĄC na jedzenie (~150 zł na tydzień, czyli obiady ~75-90 zł/tydz., ok. 5-7 zł/osobę na obiad).
- Wyposażenie: Airfryer, Piekarnik, Patelnia, podstawowe przyprawy.
- Priorytet: Czysty skład (bez chemii/azotynów) oraz wysoka wartość odżywcza (Nutri-Score A/B).

PYTANIE UŻYTKOWNIKA:
"{cleaned_query}"

AKTUALNE AKTYWNE PROMOCJE W BAZIE (Lidl, Biedronka, Kaufland - tylko ważne oferty):
{json.dumps(deals_summary, ensure_ascii=False, indent=2)}

TWOJE ZADANIE:
1. Odpowiedz bezpośrednio na pytanie użytkownika:
   - Czy szukany produkt jest w promocji?
   - W którym sklepie (Lidl / Biedronka / Kaufland) i w jakiej cenie?
   - Do kiedy obowiązuje promocja (data ważności)?
   - Czy oferta wymaga aplikacji (Lidl Plus / Moja Biedronka / Kaufland Card)?
2. Jeśli jest kilka ofert, wskaż najtańszą i najbardziej opłacalną dla ich budżetu 600 zł.
3. Jeśli użytkownik pyta ogólnie o obiad lub składnik, zaproponuj szybki pomysł na danie dla 2 osób z wykorzystaniem Airfryera, piekarnika lub patelni oraz szacowany koszt obiadu dla dwojga.
4. Styl odpowiedzi: Ciepły, zwięzły, konkretny, po polsku. Używaj czytelnego formatowania (pogrubienia, punktorów, emotek sklepów: 🟡 Biedronka, 🔵 Lidl, 🔴 Kaufland).
"""

    reply_text = ""
    for model_name in CANDIDATE_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 800
            }
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            reply_text = parts[0].get("text", "").strip()
                            break
        except Exception as e:
            print(f"Błąd asystenta z modelem {model_name}: {e}")
            continue

    if not reply_text:
        reply_text = "Przepraszam, chwilowo nie udało się połączyć z modelem AI. Sprawdź poniżej znalezione okazje z bazy gazetek."

    # Zwróć tylko najtrafniejsze oferty do wyświetlenia pod odpowiedzią
    top_deals = matched_deals[:6]
    return {
        "reply": reply_text,
        "matched_deals": top_deals
    }
