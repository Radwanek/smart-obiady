import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.config import DATABASE_PATH

def get_connection():
    conn = sqlite3.connect(DATABASE_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabela promocji
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS promotions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        store TEXT NOT NULL,
        name TEXT NOT NULL,
        price TEXT,
        category TEXT NOT NULL,
        image_url TEXT,
        nutri_score TEXT,
        clean_label TEXT,
        clean_label_desc TEXT,
        date_start TEXT,
        date_end TEXT,
        leaflet_id TEXT,
        page_number TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(store, name, date_start)
    )
    """)
    
    existing_cols = [r["name"] for r in cursor.execute("PRAGMA table_info(promotions)").fetchall()]
    for col, col_type in [
        ("image_url", "TEXT"),
        ("nutri_score", "TEXT"),
        ("clean_label", "TEXT"),
        ("clean_label_desc", "TEXT"),
        ("page_number", "TEXT"),
        ("tags", "TEXT")
    ]:
        if col not in existing_cols:
            cursor.execute(f"ALTER TABLE promotions ADD COLUMN {col} {col_type}")
    
    # Tabela planów obiadów
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS meal_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        weekly_summary TEXT,
        total_estimated_cost TEXT,
        budget_remaining TEXT,
        is_active INTEGER DEFAULT 1
    )
    """)
    
    plan_cols = [r["name"] for r in cursor.execute("PRAGMA table_info(meal_plans)").fetchall()]
    for col in ["total_estimated_cost", "budget_remaining"]:
        if col not in plan_cols:
            cursor.execute(f"ALTER TABLE meal_plans ADD COLUMN {col} TEXT")
    
    # Tabela posiłków
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS meals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id INTEGER NOT NULL,
        day TEXT NOT NULL,
        type TEXT NOT NULL,
        title TEXT NOT NULL,
        equipment TEXT NOT NULL,
        prep_time TEXT,
        discounted_ingredients TEXT,
        pantry_ingredients TEXT,
        instructions TEXT,
        nutri_score TEXT,
        cost_for_two TEXT,
        cost_per_person TEXT,
        portions INTEGER DEFAULT 2,
        FOREIGN KEY (plan_id) REFERENCES meal_plans(id)
    )
    """)
    
    meal_cols = [r["name"] for r in cursor.execute("PRAGMA table_info(meals)").fetchall()]
    for col, col_type in [
        ("nutri_score", "TEXT"),
        ("cost_for_two", "TEXT"),
        ("cost_per_person", "TEXT"),
        ("portions", "INTEGER DEFAULT 2")
    ]:
        if col not in meal_cols:
            cursor.execute(f"ALTER TABLE meals ADD COLUMN {col} {col_type}")
    
    # Tabela historii synchronizacji
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sync_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT NOT NULL,
        deals_count INTEGER DEFAULT 0,
        message TEXT
    )
    """)
    
    cursor.execute("SELECT COUNT(*) FROM promotions")
    promo_count = cursor.fetchone()[0]
    
    conn.commit()
    conn.close()
    
    # Jeśli baza jest pusta (np. po starcie nowego kontenera na Renderze), załaduj gotowy seed
    if promo_count == 0:
        seed_path = Path(__file__).resolve().parent / "seed_data.json"
        if seed_path.exists():
            try:
                print(f"[init_db] Pusta baza - natychmiastowe ładowanie seed_data z {seed_path}...")
                with open(seed_path, "r", encoding="utf-8") as f:
                    seed_data = json.load(f)
                    
                promos = seed_data.get("promotions", [])
                if promos:
                    save_promotions(promos)
                    
                p = seed_data.get("meal_plan")
                if p and "meals" in p:
                    save_meal_plan(
                        p.get("weekly_summary", "Plan obiadów dla 2 osób"),
                        p.get("meals", []),
                        p.get("total_estimated_cost", "~86 zł"),
                        p.get("budget_remaining", "~64 zł")
                    )
                    
                ls = seed_data.get("last_sync", {})
                log_sync(
                    ls.get("status", "SUCCESS"),
                    len(promos),
                    ls.get("message", "Załadowano bazę startową (instant startup)")
                )
                print(f"[init_db] Gotowe! Załadowano {len(promos)} ofert oraz kompletny plan obiadów w 0.05s.")
            except Exception as e:
                print(f"[init_db] Błąd podczas importu seed_data: {e}")

def save_promotions(deals: List[Dict[str, Any]]) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    inserted = 0
    now = datetime.now().isoformat()
    
    for d in deals:
        try:
            tags_val = d.get("tags_str") or (", ".join(d.get("tags", [])) if isinstance(d.get("tags"), list) else str(d.get("tags", "")))
            cursor.execute("""
            INSERT INTO promotions (
                store, name, price, category, tags, image_url, nutri_score, 
                clean_label, clean_label_desc, date_start, date_end, 
                leaflet_id, page_number, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(store, name, date_start) DO UPDATE SET
                price=excluded.price,
                category=excluded.category,
                tags=excluded.tags,
                image_url=excluded.image_url,
                nutri_score=excluded.nutri_score,
                clean_label=excluded.clean_label,
                clean_label_desc=excluded.clean_label_desc,
                page_number=excluded.page_number,
                updated_at=excluded.updated_at
            """, (
                d.get("store"),
                d.get("name"),
                d.get("price"),
                d.get("category"),
                tags_val,
                d.get("image_url"),
                d.get("nutri_score"),
                d.get("clean_label"),
                d.get("clean_label_desc"),
                d.get("date_start"),
                d.get("date_end"),
                d.get("leaflet_id"),
                d.get("page_number"),
                now
            ))
            inserted += 1
        except Exception:
            pass
            
    conn.commit()
    conn.close()
    return inserted

MONTH_NAMES_PL = {
    "January": "sty", "February": "lut", "March": "mar", "April": "kwi",
    "May": "maj", "June": "cze", "July": "lip", "August": "sie",
    "September": "wrz", "October": "paź", "November": "lis", "December": "gru"
}

WEEKDAYS_PL = {
    0: "pon", 1: "wt", 2: "śr", 3: "czw", 4: "pt", 5: "sob", 6: "nd"
}

def parse_date_end(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    for fmt in ("%B %d, %Y %H:%M", "%B %d, %Y", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except Exception:
            pass
    return None

def format_date_badge(date_str: str) -> Dict[str, Any]:
    dt = parse_date_end(date_str)
    if not dt:
        return {
            "is_active": True,
            "badge_text": "Aktualna oferta",
            "is_urgent": False,
            "days_left": None
        }
    
    now = datetime.now()
    if dt < now:
        return {
            "is_active": False,
            "badge_text": "Oferta zakończona",
            "is_urgent": False,
            "days_left": -1
        }
    
    diff_days = (dt.date() - now.date()).days
    weekday = WEEKDAYS_PL.get(dt.weekday(), "")
    month_en = dt.strftime("%B")
    month_pl = MONTH_NAMES_PL.get(month_en, dt.strftime("%m"))
    date_formatted = f"{dt.day} {month_pl}"
    
    if diff_days == 0:
        badge_text = "🔥 Kończy się dziś!"
        is_urgent = True
    elif diff_days == 1:
        badge_text = "⏰ Tylko do jutra!"
        is_urgent = True
    else:
        badge_text = f"Ważne do {weekday} ({date_formatted})"
        is_urgent = False
        
    return {
        "is_active": True,
        "badge_text": badge_text,
        "is_urgent": is_urgent,
        "days_left": diff_days,
        "formatted_date": f"{date_formatted} ({weekday})"
    }

def check_app_deal(name: str, store: str) -> Dict[str, Any]:
    lower = (name or "").lower()
    is_app = False
    badge = ""
    if any(k in lower for k in ["plus", "aplikac", "karta", "kaufland card", "moja biedronka", "lidl plus"]):
        is_app = True
        if "lidl" in (store or "").lower():
            badge = "Lidl Plus"
        elif "biedronka" in (store or "").lower():
            badge = "Moja Biedronka"
        elif "kaufland" in (store or "").lower():
            badge = "Kaufland Card"
        else:
            badge = "Z aplikacją"
    return {"is_app_deal": is_app, "app_badge": badge}

def get_recent_promotions(
    limit: int = 100, 
    store: Optional[str] = None, 
    category: Optional[str] = None,
    search: Optional[str] = None,
    only_active: bool = True
) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM promotions WHERE 1=1"
    params = []
    
    if store and store.lower() != "wszystkie":
        query += " AND LOWER(store) = LOWER(?)"
        params.append(store)
    if category and category.lower() != "wszystkie":
        query += " AND LOWER(category) = LOWER(?)"
        params.append(category)
    if search and search.strip():
        search_terms = [t.strip().lower() for t in search.strip().split() if t.strip()]
        for term in search_terms:
            query += " AND (LOWER(name) LIKE ? OR LOWER(category) LIKE ? OR LOWER(COALESCE(tags, '')) LIKE ?)"
            p = f"%{term}%"
            params.extend([p, p, p])
        
    fetch_limit = limit * 2 if only_active else limit
    query += " ORDER BY updated_at DESC LIMIT ?"
    params.append(fetch_limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    enriched = []
    for r in rows:
        d = dict(r)
        date_info = format_date_badge(d.get("date_end", ""))
        app_info = check_app_deal(d.get("name", ""), d.get("store", ""))
        
        d["date_badge"] = date_info["badge_text"]
        d["is_urgent"] = date_info["is_urgent"]
        d["is_active"] = date_info["is_active"]
        d["is_app_deal"] = app_info["is_app_deal"]
        d["app_badge"] = app_info["app_badge"]
        
        tags_raw = d.get("tags") or ""
        d["tags"] = [t.strip() for t in tags_raw.split(",") if t.strip()] if isinstance(tags_raw, str) else (tags_raw or [])
        
        if only_active and not date_info["is_active"]:
            continue
            
        enriched.append(d)
        if len(enriched) >= limit:
            break
            
    return enriched

def search_active_promotions(query: str, limit: int = 30) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    
    terms = [t.strip().lower() for t in query.split() if len(t.strip()) > 1]
    stopwords = {"czy", "jest", "gdzie", "jak", "dla", "jaka", "jaki", "tani", "tanie", "kupic", "kupię", "polecasz"}
    meaningful_terms = [t for t in terms if t not in stopwords]
    if not meaningful_terms:
        meaningful_terms = terms
        
    if not meaningful_terms:
        cursor.execute("SELECT * FROM promotions ORDER BY updated_at DESC LIMIT ?", (limit * 2,))
        rows = cursor.fetchall()
    else:
        clauses = []
        params = []
        for term in meaningful_terms:
            clauses.append("(LOWER(name) LIKE ? OR LOWER(category) LIKE ? OR LOWER(COALESCE(tags, '')) LIKE ? OR LOWER(store) LIKE ?)")
            p = f"%{term}%"
            params.extend([p, p, p, p])
        sql = f"SELECT * FROM promotions WHERE {' OR '.join(clauses)} ORDER BY updated_at DESC LIMIT ?"
        params.append(limit * 3)
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
    conn.close()
    
    results = []
    for r in rows:
        d = dict(r)
        date_info = format_date_badge(d.get("date_end", ""))
        if not date_info["is_active"]:
            continue
        app_info = check_app_deal(d.get("name", ""), d.get("store", ""))
        d["date_badge"] = date_info["badge_text"]
        d["is_urgent"] = date_info["is_urgent"]
        d["is_active"] = True
        d["is_app_deal"] = app_info["is_app_deal"]
        d["app_badge"] = app_info["app_badge"]
        tags_raw = d.get("tags") or ""
        d["tags"] = [t.strip() for t in tags_raw.split(",") if t.strip()] if isinstance(tags_raw, str) else (tags_raw or [])
        results.append(d)
        if len(results) >= limit:
            break
            
    return results

def save_meal_plan(weekly_summary: str, meals: List[Dict[str, Any]], total_cost: str = "", budget_remaining: str = "") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE meal_plans SET is_active = 0 WHERE is_active = 1")
    cursor.execute("""
    INSERT INTO meal_plans (weekly_summary, total_estimated_cost, budget_remaining, is_active) 
    VALUES (?, ?, ?, 1)
    """, (weekly_summary, total_cost, budget_remaining))
    plan_id = cursor.lastrowid
    
    for m in meals:
        cursor.execute("""
        INSERT INTO meals (
            plan_id, day, type, title, equipment, prep_time, 
            discounted_ingredients, pantry_ingredients, instructions, 
            nutri_score, cost_for_two, cost_per_person, portions
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            plan_id,
            m.get("day", ""),
            m.get("type", "Obiad"),
            m.get("title", ""),
            m.get("equipment", "Airfryer"),
            m.get("prep_time", ""),
            json.dumps(m.get("discounted_ingredients", []), ensure_ascii=False),
            json.dumps(m.get("pantry_ingredients", []), ensure_ascii=False),
            json.dumps(m.get("instructions", []), ensure_ascii=False),
            m.get("nutri_score", "A"),
            m.get("cost_for_two", "ok. 20 zł"),
            m.get("cost_per_person", "ok. 10 zł"),
            m.get("portions", 2)
        ))
        
    conn.commit()
    conn.close()
    return plan_id

def get_active_meal_plan() -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM meal_plans WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
    plan_row = cursor.fetchone()
    if not plan_row:
        conn.close()
        return None
        
    plan = dict(plan_row)
    cursor.execute("SELECT * FROM meals WHERE plan_id = ? ORDER BY id ASC", (plan["id"],))
    meal_rows = cursor.fetchall()
    conn.close()
    
    meals = []
    for mr in meal_rows:
        m = dict(mr)
        try:
            m["discounted_ingredients"] = json.loads(m["discounted_ingredients"])
        except Exception:
            m["discounted_ingredients"] = []
        try:
            m["pantry_ingredients"] = json.loads(m["pantry_ingredients"])
        except Exception:
            m["pantry_ingredients"] = []
        try:
            m["instructions"] = json.loads(m["instructions"])
        except Exception:
            m["instructions"] = []
        meals.append(m)
        
    plan["meals"] = meals
    return plan

def log_sync(status: str, deals_count: int, message: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO sync_history (status, deals_count, message)
    VALUES (?, ?, ?)
    """, (status, deals_count, message))
    conn.commit()
    conn.close()

def get_last_sync_info() -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sync_history ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
