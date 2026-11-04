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
Jesteś mistrzem oszczędnego, zdrowego gotowania (smart budgeting chef).
Twoim zadaniem jest ułożenie genialnego, sycącego i zdrowego tygodniowego planu obiadów dla PARY (2 OSOBY: użytkownik i jego dziewczyna).

DANE BUDŻETOWE (BARDZO WAŻNE):
- Budżet całkowity na jedzenie wynosi: 600 ZŁ NA MIESIĄC na 2 osoby!
- W przeliczeniu na 1 tydzień para ma do dyspozycji: DOKŁADNIE 150 ZŁ / TYDZIEŃ.
- Twój cel: Wszystkie 7 obiadów i 2 zupy na cały tydzień dla 2 osób muszą zamknąć się łącznie w kwocie ok. 75 - 90 ZŁ!
- Oznacza to, że pojedynczy obiad dla DWOJGA kosztuje średnio tylko ok. 10 - 13 zł (czyli zaledwie ~5 - 6.50 zł na osobę!).
- Z tygodniowej puli 150 zł musi zostać jeszcze ok. 60 - 75 zł na podstawowe śniadania i kolacje (jajka, pieczywo, płatki, herbata).

JAK TO OSIĄGNĄĆ DZIĘKI PROMOCJOM I SPRZĘTOWI:
- Poluj na tanie i wartościowe części drobiu (podudzia z kurczaka za 7.99 zł/kg, udka, skrzydełka).
- Kupuj mięso w promocjach XXL (np. szynka wieprzowa 9.99 zł/kg - 1 kg starcza na 2 obiady dla dwojga!).
- Tanie bazy: Ziemniaki z promocji (0.99 zł/kg), warzywa rosołowe, marchew, kapusta, cebula.
- Duży garnek domowej zupy (np. zupa jarzynowa z indykiem lub gulaszowa) kosztuje ~12-15 zł za cały garnek i starcza na 2-3 dni!
- Airfryer i piekarnik robią z tanich składników restauracyjne, chrupiące dania bez marnowania drogiego tłuszczu.

Oto wyselekcjonowane aktualne promocje (Lidl, Biedronka, Kaufland):
{json.dumps(sample_deals, ensure_ascii=False, indent=2)}

Wyposażenie kuchni:
- Airfryer, Piekarnik, Patelnia, Garnek.
- Podstawowe przyprawy w domu: sól, pieprz, papryka, czosnek, zioła, oliwa/olej, mąka, ryż/makaron.

Zasady:
1. Zaproponuj dokładnie 7 obiadów dla 2 osób (Poniedziałek - Niedziela) i 2 zupy (Zupa 1, Zupa 2).
2. Każde danie ma podwójną porcję dla dwojga.
3. Oblicz realny koszt każdego obiadu dla 2 osób (cost_for_two ok. 10-14 zł) i na osobę (cost_per_person ok. 5-7 zł).
4. Oszacuj łączny koszt obiadów na tydzień (weekly_total_cost: ok. 80-90 zł) oraz pozostałą kwotę z tygodniowej puli 150 zł.

Zwróć odpowiedź w czystym formacie JSON:
{{
  "weekly_summary": "Krótkie podsumowanie jak zmieścić się w 600 zł miesięcznie (150 zł/tydz.) gotując pysznie dla dwojga.",
  "weekly_total_cost": "np. 84.50 zł",
  "budget_remaining": "np. 65.50 zł na śniadania i kolacje (z puli 150 zł/tydz.)",
  "monthly_dinners_estimate": "np. ok. 340 zł / 600 zł na cały miesiąc",
  "meals": [
    {{
      "day": "Poniedziałek",
      "type": "Obiad",
      "title": "Chrupiące podudzia z kurczaka z pieczonymi ziemniaczkami w ziołach",
      "equipment": "Airfryer",
      "prep_time": "35 min",
      "nutri_score": "A",
      "portions": 2,
      "cost_for_two": "10.50 zł",
      "cost_per_person": "5.25 zł",
      "discounted_ingredients": [
        {{"store": "Biedronka", "name": "Świeże podudzie z kurczaka (0.6 kg)", "price": "4.80 zł"}},
        {{"store": "Kaufland", "name": "Ziemniaki polskie (1 kg)", "price": "0.99 zł"}}
      ],
      "pantry_ingredients": ["oliwa", "papryka słodka", "czosnek", "majeranek", "sól"],
      "instructions": [
        "Podudzia osusz, natrzyj oliwą, słodką papryką, solą i czosnkiem.",
        "Ziemniaki pokrój w łódeczki i dopraw majerankiem.",
        "Piecz w Airfryerze w 180°C przez 25 minut aż będą złociste i chrupiące."
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
