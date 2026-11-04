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
        
    # We select up to 30 relevant high-quality promotions across stores
    sample_deals = []
    for d in promotions[:40]:
        sample_deals.append({
            "store": d.get("store"),
            "name": d.get("name"),
            "price": d.get("price"),
            "category": d.get("category")
        })
        
    prompt = f"""
Jesteś profesjonalnym szefem kuchni oraz dietetykiem.
Twoim celem jest stworzenie kompletnego, pysznego i zbilansowanego planu obiadów na tydzień (7 dań głównych) oraz 2 sycących domowych zup na bazie aktualnych promocji z marketów: Lidl, Biedronka, Kaufland.

Oto wyselekcjonowane aktualne promocje (mięsa, ryby, sery, twarogi, jogurty, warzywa):
{json.dumps(sample_deals, ensure_ascii=False, indent=2)}

Wyposażenie kuchni i spiżarnia użytkownika:
- Airfryer (frytkownica beztłuszczowa - idealna do chrupiącego drobiu, pieczonych warzyw, mięs bez tłuszczu)
- Piekarnik (do pieczenia, zapiekanek, dań jednogarnkowych)
- Patelnia (do szybkiego podsmażania, kotletów, sosów)
- Garnek (do zup i gotowania dodatków)
- Spiżarnia: Podstawowe przyprawy (sól, pieprz, papryka słodka/ostra, czosnek granulowany, majeranek, zioła prowansalskie), oliwa/olej, mąka, makaron, ryż, ziemniaki.

Zasady:
1. Zaproponuj dokładnie 7 obiadów:
   - Poniedziałek, Wtorek, Środa, Czwartek, Piątek, Sobota, Niedziela
2. Zaproponuj dokładnie 2 zupy:
   - Zupa 1, Zupa 2
3. W każdym posiłku maksymalnie wykorzystaj produkty z powyższej listy promocji (podaj nazwę przecenionego produktu, sklep i cenę).
4. Wykorzystaj sprzęt kuchenny – niech przynajmniej 2-3 dania będą zrobione w Airfryerze, inne w piekarniku lub na patelni.
5. Przepisy mają być praktyczne, konkretne i łatwe do powtórzenia w domu.

Zwróć odpowiedź w czystym formacie JSON o poniższej strukturze:
{{
  "weekly_summary": "Krótki 2-3 zdaniowy opis pomysłu na ten tydzień i największych oszczędności.",
  "meals": [
    {{
      "day": "Poniedziałek",
      "type": "Obiad",
      "title": "Chrupiące podudzia z kurczaka w ziołach z ziemniaczkami",
      "equipment": "Airfryer",
      "prep_time": "35 min",
      "discounted_ingredients": [
        {{"store": "Biedronka", "name": "Świeże podudzie z kurczaka", "price": "7.99 zł"}}
      ],
      "pantry_ingredients": ["ziemniaki", "papryka słodka", "czosnek", "oliwa"],
      "instructions": [
        "Podudzia osusz i natrzyj oliwą, słodką papryką, czosnkiem i solą.",
        "Włóż do koszyka Airfryera na 180°C na 25-30 minut, obracając w połowie.",
        "Podawaj z pieczonymi ziemniakami i ulubioną surówką."
      ]
    }}
  ]
}}
"""

    headers = {"Content-Type": "application/json"}
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
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
                    print(f"Warning: {last_error}")
        except Exception as e:
            last_error = f"{model_name}: {e}"
            print(f"Warning exception: {last_error}")
            
    print(f"Failed to generate meal plan with all candidate models. Last error: {last_error}")
    return None
