import sqlite3
import json
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
    
    # Dodaj kolumny jeśli tabela już istniała w starszej wersji
    existing_cols = [r["name"] for r in cursor.execute("PRAGMA table_info(promotions)").fetchall()]
    for col, col_type in [
        ("image_url", "TEXT"),
        ("nutri_score", "TEXT"),
        ("clean_label", "TEXT"),
        ("clean_label_desc", "TEXT"),
        ("page_number", "TEXT")
    ]:
        if col not in existing_cols:
            cursor.execute(f"ALTER TABLE promotions ADD COLUMN {col} {col_type}")
    
    # Tabela planów obiadów
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS meal_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        weekly_summary TEXT,
        is_active INTEGER DEFAULT 1
    )
    """)
    
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
        FOREIGN KEY (plan_id) REFERENCES meal_plans(id)
    )
    """)
    
    meal_cols = [r["name"] for r in cursor.execute("PRAGMA table_info(meals)").fetchall()]
    if "nutri_score" not in meal_cols:
        cursor.execute("ALTER TABLE meals ADD COLUMN nutri_score TEXT")
    
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
    
    conn.commit()
    conn.close()

def save_promotions(deals: List[Dict[str, Any]]) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    inserted = 0
    now = datetime.now().isoformat()
    
    for d in deals:
        try:
            cursor.execute("""
            INSERT INTO promotions (
                store, name, price, category, image_url, nutri_score, 
                clean_label, clean_label_desc, date_start, date_end, 
                leaflet_id, page_number, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(store, name, date_start) DO UPDATE SET
                price=excluded.price,
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
        except Exception as e:
            pass
            
    conn.commit()
    conn.close()
    return inserted

def get_recent_promotions(limit: int = 80, store: Optional[str] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
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
        
    query += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_meal_plan(weekly_summary: str, meals: List[Dict[str, Any]]) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE meal_plans SET is_active = 0 WHERE is_active = 1")
    cursor.execute("INSERT INTO meal_plans (weekly_summary, is_active) VALUES (?, 1)", (weekly_summary,))
    plan_id = cursor.lastrowid
    
    for m in meals:
        cursor.execute("""
        INSERT INTO meals (
            plan_id, day, type, title, equipment, prep_time, 
            discounted_ingredients, pantry_ingredients, instructions, nutri_score
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            m.get("nutri_score", "A")
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
