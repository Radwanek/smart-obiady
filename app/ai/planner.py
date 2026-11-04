import json
import httpx
from typing import List, Dict, Any, Optional
from app.config import GEMINI_API_KEY

CANDIDATE_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash"
]

def generate_weekly_meal_plan(promotions: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY is not configured!")
        return None
        
    sample_deals = []
    for d in promotions[:40]:
        sample_deals.append({
            "store": d.get("store"),
            "name": d.get("name"),
            "price": d.get("price"),
            "category": d.get("category"),
            "nutri_score": d.get("nutri_score", "A"),
            "clean_label": d.get("clean_label", "CLEAN")
        })
        
    prompt = f"""
Jesteś profesjonalnym szefem kuchni oraz dietetykiem klinicznym.
Twoim celem jest stworzenie prestiżowego, zdrowego i zbilansowanego planu obiadów na tydzień (7 dań głównych) oraz 2 zup na bazie aktualnych promocji z marketów: Lidl, Biedronka, Kaufland.

PRIORYTETY JAKOŚCIOWE:
- Priorytetyzuj produkty z CZYSTYM SKŁADEM (100% świeże mięso drobiowe, wołowe, schab, ryby, warzywa, czyste twarogi, jogurty).
- Unikaj wysoko przetworzonej żywności z konserwantami i azotynami.
- Każde danie powinno mieć wysoki wskaźnik Nutri-Score (A lub B).

Oto wyselekcjonowane aktualne promocje:
{json.dumps(sample_deals, ensure_ascii=False, indent=2)}

Wyposażenie kuchni i spiżarnia użytkownika:
- Airfryer (frytkownica beztłuszczowa - chrupiące, soczyste potrawy bez ton tłuszczu)
- Piekarnik (zapiekanki, pieczenie, pieczenie warzyw i mięs)
- Patelnia (szybkie podsmażanie, steki, potrawki)
- Garnek (zupy i bazy)
- Spiżarnia: Podstawowe przyprawy, zioła, oliwa, czosnek, cebula, mąka, makaron/ryż, ziemniaki.

Zasady:
1. Zaproponuj dokładnie 7 obiadów (Poniedziałek - Niedziela) i 2 zupy (Zupa 1, Zupa 2).
2. Wskaż sprzęt dla każdego dania (np. Airfryer, Piekarnik, Patelnia, Garnek).
3. Każde danie musi wykorzystywać składniki z powyższej listy promocji.
4. Przepisy mają być konkretne, apetyczne i zdrowe.

Zwróć odpowiedź w czystym formacie JSON:
{{
  "weekly_summary": "Krótki 2-3 zdaniowy opis pomysłu na ten tydzień z akcentem na czysty skład, zdrowe białko i oszczędności.",
  "meals": [
    {{
      "day": "Poniedziałek",
      "type": "Obiad",
      "title": "Chrupiący filet z indyka z pieczonymi ziołowymi ziemniaczkami",
      "equipment": "Airfryer",
      "prep_time": "30 min",
      "nutri_score": "A",
      "discounted_ingredients": [
        {{"store": "Lidl", "name": "Indyk filet z piersi XXL", "price": "19.99 zł"}}
      ],
      "pantry_ingredients": ["ziemniaki", "papryka słodka", "oliwa z oliwek", "czosnek"],
      "instructions": [
        "Indyka pokrój na zgrabne steki, osusz i natrzyj oliwą oraz przyprawami.",
        "Włóż do Airfryera na 180°C na 14-16 minut, obracając raz w połowie pieczenia.",
        "Podawaj z chrupiącymi ziemniaczkami i świeżą surówką."
      ]
    }}
  ]
}}
"""

    headers = {"Content-Type": "application/json"}
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.35,
            "responseMimeType": "application/json"
        }
    }
    
    last_error = ""
    for model_name in CANDIDATE_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        try:
            with httpx.Client(timeout=40.0) as client:
                resp = client.post(url, headers=headers, json=body)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_text = data['candidates'][0]['content']['parts'][0]['text'].strip()
                    if raw_text.startswith("```"):
                        raw_text = raw_text.split("\n", 1)[1].rsplit("\n```", 1)[0]
                    return json.loads(raw_text)
                else:
                    last_error = f"{model_name}: {resp.status_code} - {resp.text[:120]}"
        except Exception as e:
            last_error = f"{model_name}: {e}"
            
    print(f"Failed to generate meal plan with candidate models. Last error: {last_error}")
    return None
