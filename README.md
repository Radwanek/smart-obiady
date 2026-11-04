# 🥘 Smart Obiady - Asystent Promocji & Planer Obiadów AI

Aplikacja, która automatycznie przeszukuje aktualne gazetki promocyjne (**Lidl**, **Biedronka**, **Kaufland**), filtruje jakościowe mięsa, sery, twarogi, jogurty i warzywa, a następnie przy użyciu **Google Gemini AI** układa zbilansowany tygodniowy plan obiadów i zup dostosowany do Twojego sprzętu (**Airfryer, Piekarnik, Patelnia, Przyprawy**).

---

## 🌟 Główne Funkcje

1. **Automatyczne przeszukiwanie gazetek (7:00, 15:00, 18:00)**:
   - Wbudowany harmonogram pobiera aktualne promocje 3 razy dziennie.
   - Dostępny przycisk manualny **"Generuj Nowy Plan"** w aplikacji WWW.
2. **AI Chef (Google Gemini)**:
   - Analizuje przeceny pod kątem Twojego sprzętu: Airfryer, piekarnik, patelnia.
   - Tworzy 7 różnorodnych dań obiadowych na każdy dzień tygodnia + 2 zupy.
   - Podaje składniki promocyjne ze sklepem i ceną, składniki domowe oraz przepis krok po kroku.
3. **Interaktywna Lista Zakupów**:
   - Składniki ze zniżkami automatycznie posortowane według sklepów (Lidl / Biedronka / Kaufland).
   - Checkboxy zapamiętywane w telefonie do odhaczania produktów w sklepie.
4. **Responsywny interfejs (PWA / Mobile-friendly)**:
   - Działa i wygląda jak nowoczesna aplikacja na smartfonie, tablecie i laptopie.

---

## 🚀 Uruchomienie lokalne

1. Aktywuj środowisko i zainstaluj zależności:
   ```bash
   py -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Skonfiguruj plik `.env` (klucz Gemini jest już wstawiony):
   ```env
   GEMINI_API_KEY=twoj_klucz_z_google_ai_studio
   PORT=8000
   SCHEDULE_HOURS=7,15,18
   ```
3. Uruchom serwer deweloperski:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
4. Otwórz w przeglądarce: `http://localhost:8000`

---

## ☁️ Wdrożenie na Railway

1. **Utwórz repozytorium na GitHubie** (np. `smart-obiady`).
2. Zainicjalizuj i wyślij kod:
   ```bash
   git init
   git add .
   git commit -m "Initial commit - Smart Obiady"
   git branch -M main
   git remote add origin https://github.com/TWOJ_USER/smart-obiady.git
   git push -u origin main
   ```
3. **Na Railway.app**:
   - Kliknij **New Project** -> **Deploy from GitHub repo**.
   - Wybierz repozytorium `smart-obiady`.
   - W zakładce **Variables** dodaj zmienną środowiskową:
     - `GEMINI_API_KEY` = Twój klucz z Google AI Studio.
   - W zakładce **Settings** -> **Networking** kliknij **Generate Domain**.
   - Twoja aplikacja będzie działać 24/7 pod adresem `https://twoja-nazwa.up.railway.app`!

---

## 💻 Zarządzanie z laptopa w Antigravity

Dzięki temu, że kod jest na GitHubie:
1. Na laptopie sklonuj repozytorium lub otwórz folder w **Antigravity**.
2. Możesz rozmawiać z asystentem, wprowadzać nowe funkcje, a po `git push` Railway automatycznie zaktualizuje Twoją działającą stronę w chmurze!
