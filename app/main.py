import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from app.database import (
    init_db, 
    get_recent_promotions, 
    get_active_meal_plan, 
    get_last_sync_info
)
from app.scheduler import start_scheduler, run_full_sync_task, is_syncing
from app.config import SCHEDULE_HOURS

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicjalizacja bazy
    init_db()
    # Start harmonogramu (7, 15, 18)
    start_scheduler()
    
    # Jeśli baza jest pusta, uruchom pierwszy sync w tle
    plan = get_active_meal_plan()
    if not plan:
        print("Pierwsze uruchomienie - kolejkowanie wstępnego pobrania danych...")
        asyncio.create_task(asyncio.to_thread(run_full_sync_task))
        
    yield

app = FastAPI(title="Promocje & Obiady AI", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/status")
def get_status():
    last_sync = get_last_sync_info()
    plan = get_active_meal_plan()
    return {
        "is_syncing": is_syncing,
        "schedule_hours": SCHEDULE_HOURS,
        "last_sync": last_sync,
        "has_active_plan": plan is not None,
        "plan_created_at": plan.get("created_at") if plan else None
    }

@app.get("/api/promotions")
def list_promotions(
    store: Optional[str] = Query(None, description="Lidl | Biedronka | Kaufland | Wszystkie"),
    category: Optional[str] = Query(None, description="Mięso i ryby | Nabiał i sery | Warzywa i baza | Wszystkie"),
    limit: int = 80
):
    deals = get_recent_promotions(limit=limit, store=store, category=category)
    return {"count": len(deals), "promotions": deals}

@app.get("/api/meal-plan")
def get_meal_plan():
    plan = get_active_meal_plan()
    if not plan:
        return {"plan": None, "message": "Brak wygenerowanego planu. Kliknij przycisk odświeżenia."}
    return {"plan": plan}

@app.post("/api/refresh")
async def trigger_refresh(background_tasks: BackgroundTasks):
    global is_syncing
    if is_syncing:
        return {"status": "ALREADY_RUNNING", "message": "Synchronizacja już trwa w tle."}
        
    background_tasks.add_task(run_full_sync_task)
    return {"status": "STARTED", "message": "Rozpoczęto pobieranie promocji i generowanie obiadów w tle."}

# Mount static frontend
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
