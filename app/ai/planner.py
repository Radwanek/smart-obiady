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
Jesteś profesjonalnym szefem kuchni oraz dietetykiem klinicznym i doradcą budżetowym.
Twoim celem jest stworzenie prestiżowego, zdrowego i ekonomicznego planu obiadów na tydzień dla MŁODEJ PARY (2 OSOBY: użytkownik i jego dziewczyna).

DANE BUDŻETOWE I PROFIL:
- Liczba osób: DOKŁADNIE 2 OSOBY (każdy obiad ma być sycącą podwójną porcją dla pary).
- Całkowity budżet tygodniowy na jedzenie: 600 ZŁ.
- Cel kosztowy na obiady + zupy: Koszt wszystkich 7 obiadów i 2 zup ma zamykać się w granicach ok. 160 - 240 zł łącznie dla 2 osób (czyli ok. 15-28 zł za cały obiad dla dwojga, ~8-14 zł na osobę).
- Dzięki temu z budżetu 600 zł zostaje parze jeszcze ponad 350-400 zł na śniadania, kolacje, owoce i dobre kawy!

PRIORYTETY JAKOŚCIOWE:
- Czysty skład (100% świeże mięso drobiowe, wieprzowe, wołowe, ryby, warzywa, czyste twarogi, jogurty).
- Unikaj wysoko przetworzonej żywności z konserwantami i azotynami.
- Wysoki wskaźnik Nutri-Score (A lub B) dla dań.

Oto wyselekcjonowane aktualne promocje (Lidl, Biedronka, Kaufland):
{json.dumps(sample_deals, ensure_ascii=False, indent=2)}

Wyposażenie kuchni pary:
- Airfryer (frytkownica beztłuszczowa - chrupiące mięsa i pieczone warzywa)
- Piekarnik (zapiekanki, pieczenie dla 2 osób)
- Patelnia (szybkie podsmażanie, steki, potrawki)
- Garnek (zupy i bazy)
- Spiżarnia: Podstawowe przyprawy, zioła, oliwa, czosnek, cebula, mąka, makaron/ryż, ziemniaki.

Zasady:
1. Zaproponuj dokładnie 7 obiadów dla 2 osób (Poniedziałek - Niedziela) i 2 zupy (Zupa 1, Zupa 2).
2. Wskaż sprzęt dla każdego dania (np. Airfryer, Piekarnik, Patelnia, Garnek).
3. Każde danie musi wykorzystywać składniki z powyższej listy promocji.
4. Oszacuj realny koszt każdego obiadu dla 2 osób (cost_for_two) oraz w przeliczeniu na 1 osobę (cost_per_person).
5. Oszacuj łączny koszt obiadów na tydzień (weekly_total_cost) oraz ile zostaje z budżetu 600 zł (budget_remaining).

Zwróć odpowiedź w czystym formacie JSON:
{{
  "weekly_summary": "Krótki 2-3 zdaniowy opis pomysłu na ten tydzień dla 2 osób z uwzględnieniem budżetu 600 zł i oszczędności.",
  "weekly_total_cost": "np. 185 zł",
  "budget_remaining": "np. 415 zł na śniadania, kolacje i przekąski",
  "meals": [
    {{
      "day": "Poniedziałek",
      "type": "Obiad",
      "title": "Chrupiący filet z indyka z pieczonymi ziołowymi ziemniaczkami",
      "equipment": "Airfryer",
      "prep_time": "30 min",
      "nutri_score": "A",
      "portions": 2,
      "cost_for_two": "21.50 zł",
      "cost_per_person": "10.75 zł",
      "discounted_ingredients": [
        {{"store": "Lidl", "name": "Indyk filet z piersi XXL", "price": "19.99 zł"}}
      ],
      "pantry_ingredients": ["ziemniaki", "papryka słodka", "oliwa z oliwek", "czosnek"],
      "instructions": [
        "Dwie porcje fileta z indyka osusz i natrzyj oliwą oraz przyprawami.",
        "Włóż do Airfryera na 180°C na 14-16 minut, obracając w połowie.",
        "Podawaj dla dwojga z pieczonymi ziemniaczkami i świeżą surówką."
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
