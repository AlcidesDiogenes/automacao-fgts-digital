import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.browser import BrowserManager
from config import settings

def run():
    mgr = BrowserManager(headless=True)
    try:
        p = mgr.iniciar()
        p.goto("https://fgtsdigital.sistema.gov.br/portal", wait_until="domcontentloaded")
        p.locator("button:has-text('Entrar com gov.br')").first.click()
        p.wait_for_url("**/sso.acesso.gov.br/login**", timeout=25000)
        p.wait_for_load_state("networkidle")

        # Salva todo o HTML formatado
        html = p.content()
        Path("data/logs/sso_completo.html").write_text(html, encoding="utf-8")
        print("HTML salvo em data/logs/sso_completo.html")

        # Procura por form loginData
        form = p.locator("#loginData").first
        if form.count() > 0:
            print("Form #loginData encontrado:")
            print("Action:", form.get_attribute("action"))
            print("Method:", form.get_attribute("method"))
            inputs = form.locator("input").all()
            for inp in inputs:
                print(f"Input: name='{inp.get_attribute('name')}', value='{inp.get_attribute('value')}', type='{inp.get_attribute('type')}'")
    finally:
        mgr.fechar()

if __name__ == "__main__":
    run()
