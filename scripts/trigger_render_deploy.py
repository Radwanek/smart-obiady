import httpx
import sys

DEPLOY_HOOK_URL = "https://api.render.com/deploy/srv-dblpre8m7kps73buqqj0?key=GfZr1mELTK8"

def trigger_render_deploy():
    print(f"Wysyłanie sygnału deploy do Rendera...")
    try:
        r = httpx.post(DEPLOY_HOOK_URL, timeout=15.0)
        if r.status_code == 200:
            data = r.json()
            deploy_id = data.get("deploy", {}).get("id", "brak_id")
            print(f"Sukces! Nowe wdrożenie zostało zainicjowane na Renderze (ID: {deploy_id}).")
            return True
        else:
            print(f"Błąd Rendera: {r.status_code} - {r.text}")
            return False
    except Exception as e:
        print(f"Błąd połączenia: {e}")
        return False

if __name__ == "__main__":
    success = trigger_render_deploy()
    sys.exit(0 if success else 1)
