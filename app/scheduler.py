import threading
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import SCHEDULE_HOURS
from app.database import (
    save_promotions, 
    get_recent_promotions, 
    save_meal_plan, 
    log_sync
)
from app.scrapers.blix_scraper import scrape_all_promotions
from app.ai.planner import generate_weekly_meal_plan

scheduler = BackgroundScheduler()
sync_lock = threading.Lock()
is_syncing = False

def run_full_sync_task() -> dict:
    global is_syncing
    if not sync_lock.acquire(blocking=False):
        return {"status": "ALREADY_RUNNING", "message": "Synchronizacja już trwa w tle."}
        
    is_syncing = True
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Rozpoczęto pobieranie promocji...")
        deals = scrape_all_promotions()
        deals_count = len(deals)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Pobrano {deals_count} promocji.")
        
        if deals:
            save_promotions(deals)
            
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Generowanie planu obiadów dla 2 osób (budżet 600 zł) przez Gemini AI...")
        recent_deals = get_recent_promotions(limit=50)
        plan_data = generate_weekly_meal_plan(recent_deals)
        
        if plan_data and "meals" in plan_data:
            summary = plan_data.get("weekly_summary", "Plan obiadów dla 2 osób na bazie aktualnych promocji")
            total_cost = plan_data.get("weekly_total_cost", "~180 zł")
            budget_rem = plan_data.get("budget_remaining", "~420 zł na śniadania i kolacje")
            meals = plan_data.get("meals", [])
            
            plan_id = save_meal_plan(summary, meals, total_cost, budget_rem)
            msg = f"Sukces: Zapisano {deals_count} promocji oraz plan dla 2 osób #{plan_id} ({len(meals)} dań, szacunek: {total_cost})."
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
            log_sync("SUCCESS", deals_count, msg)
            return {"status": "SUCCESS", "message": msg, "deals_count": deals_count, "meals_count": len(meals)}
        else:
            msg = f"Pobrano {deals_count} promocji, ale generowanie planu AI nie powiodło się."
            log_sync("PARTIAL_SUCCESS", deals_count, msg)
            return {"status": "PARTIAL_SUCCESS", "message": msg, "deals_count": deals_count}
            
    except Exception as e:
        msg = f"Błąd synchronizacji: {str(e)}"
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        log_sync("ERROR", 0, msg)
        return {"status": "ERROR", "message": msg}
    finally:
        is_syncing = False
        sync_lock.release()

def start_scheduler():
    hours = [h.strip() for h in SCHEDULE_HOURS.split(",") if h.strip()]
    for h in hours:
        scheduler.add_job(
            run_full_sync_task,
            CronTrigger(hour=int(h), minute=0),
            id=f"promo_sync_hour_{h}",
            replace_existing=True
        )
        print(f"Zaplanowano automatyczne sprawdzanie o godzinie {h}:00")
        
    scheduler.start()
