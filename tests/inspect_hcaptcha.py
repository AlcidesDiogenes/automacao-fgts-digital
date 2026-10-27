import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.browser import BrowserManager
from config import settings

def inspect_hcaptcha():
    mgr = BrowserManager(headless=True)
    try:
        p = mgr.iniciar()
        p.goto("https://fgtsdigital.sistema.gov.br/portal", wait_until="domcontentloaded")
        p.locator("button:has-text('Entrar com gov.br')").first.click()
        p.wait_for_url("**/sso.acesso.gov.br/login**", timeout=25000)
        p.wait_for_load_state("networkidle")

        # Inspeciona window.hcaptcha e propriedades
        info = p.evaluate('''() => {
            return {
                widgetId: window.hcaptchaWidgetId,
                scripts: Array.from(document.scripts).map(s => s.src || s.innerText).filter(s => s.includes("hcaptcha") || s.includes("Widget"))
            };
        }''')
        print("Widget ID:", info["widgetId"])
        print("Scripts:", len(info["scripts"]))
        for s in info["scripts"]:
            print("--- SCRIPT ---")
            print(s[:500])
    finally:
        mgr.fechar()

if __name__ == "__main__":
    inspect_hcaptcha()
