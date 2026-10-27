import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.browser import BrowserManager
from config import settings

def inspect():
    mgr = BrowserManager(headless=True)
    try:
        p = mgr.iniciar()
        p.goto("https://fgtsdigital.sistema.gov.br/portal", wait_until="domcontentloaded")
        p.locator("button:has-text('Entrar com gov.br')").first.click()
        p.wait_for_url("**/sso.acesso.gov.br/login**", timeout=25000)
        p.wait_for_load_state("networkidle")

        btn = p.locator("#login-certificate").first
        print("OuterHTML do botão:")
        print(btn.evaluate("e => e.outerHTML"))

        # Inspeciona o form pai e atributos
        parent = btn.locator("xpath=..")
        print("\nParent HTML:")
        print(parent.evaluate("e => e.outerHTML"))

        # Inspeciona scripts e endpoints relacionados ao certificado
        print("\nLinks ou actions com certificado:")
        elems = p.locator("[href*='cert'], [action*='cert'], [onclick*='cert']").all()
        for el in elems:
            print(el.evaluate("e => e.outerHTML"))

    finally:
        mgr.fechar()

if __name__ == "__main__":
    inspect()
