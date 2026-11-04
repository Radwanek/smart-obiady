# 📋 RAPORT PRZEKAZANIA PROJEKTU (HANDOFF DLA NOWEGO PROFILU AI)

Ten plik służy do natychmiastowego wprowadzenia nowego asystenta AI po zmianie konta.

---

## 🎯 Cel Projektu: Smart Obiady
Aplikacja wyszukuje okazje i promocje z gazetek (**Lidl, Biedronka, Kaufland**), filtruje wartościowe produkty (**mięso, ryby, sery, twarogi, jogurty, warzywa**) i przy użyciu **Google Gemini AI** tworzy cotygodniowy plan 7 obiadów + 2 zup.

Posiadany sprzęt kuchenny użytkownika:
- **Airfryer** ⚡
- **Piekarnik** 🔥
- **Patelnia** 🍳
- **Garnki** 🍲
- Spiżarnia z podstawowymi przyprawami, oliwą i dodatkami.

---

## 🛠️ Stan Projektu (CO ZOSTAŁO ZROBIONE I DZIAŁA):

1. **Scraper promocji (`app/scrapers/blix_scraper.py`)**:
   - Przetestowany i w 100% sprawny. Pobiera na żywo oferty z Lidla, Biedronki i Kauflanda (ostatni test: 472 unikalne promocje).
   - Inteligentny filtr kategorii + odrzucanie spamu (chemia, alkohol, ciastka, kawa).
2. **Silnik AI Gemini (`app/ai/planner.py`)**:
   - Przetestowany na kluczu Google AI Studio.
   - Używa modelu `gemini-3.5-flash-lite` (z automatycznym fallbackiem na `gemini-3-flash-preview` i `gemini-3.1-flash-lite`).
   - Układa 7 dań obiadowych na dany tydzień + 2 zupy, przypisując sprzęt i przecenione składniki.
3. **Baza danych SQLite (`app/database.py`)**:
   - Tabele: `promotions`, `meal_plans`, `meals`, `sync_history`.
   - Zapisuje pobrane promocje, historię obiadów i stan synchronizacji.
4. **Harmonogram (`app/scheduler.py`)**:
   - APScheduler: automatyczne pobieranie o **07:00, 15:00 i 18:00**.
   - Obsługa manualnego wymuszenia przyciskiem (`POST /api/refresh`).
5. **Backend FastAPI & Frontend Web (`app/main.py`, `app/static/`)**:
   - Nowoczesny, responsywny interfejs (PWA / Mobile-first).
   - Zakładki:
     - 📅 *Plan Obiadów na Tydzień* (z przepisami krok po kroku i badge'ami sprzętu).
     - 🏷️ *Przegląd Promocji* (z filtrowaniem sklepów i kategorii).
     - 🛒 *Lista Zakupów* (zgrupowana sklepami, z checkboxami w pamięci telefonu).
6. **Git & GitHub**:
   - Repozytorium powiązane z GitHubem użytkownika: `git@github.com:Radwanek/smart-obiady.git`
   - Klucz SSH użytkownika jest już sparowany z GitHubem.

---

## 🚀 Co zrobić na nowym profilu AI:

1. **Nowy klucz Gemini API**:
   - Wygeneruj klucz na nowym koncie w [aistudio.google.com](https://aistudio.google.com/).
   - Wklej go do pliku `.env`: `GEMINI_API_KEY=...`
2. **Darmowy hosting (zamiast kończącego się Railway)**:
   - Podpiąć repozytorium `Radwanek/smart-obiady` pod darmowy **Koyeb** (koyeb.com) lub **Render** (render.com) – oba mają darmowy plan 0 zł i wspierają Pythona/Dockera.
   - Dodać w hostingu zmienną środowiskową: `GEMINI_API_KEY`.
