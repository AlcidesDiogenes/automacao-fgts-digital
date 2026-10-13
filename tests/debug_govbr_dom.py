import sys
from pathlib import Path
import time

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.browser import BrowserManager
from config import settings

def debug_govbr():
    pfx_path = Path(settings.PFX_PATH)
    pfx_pass = settings.PFX_PASSWORD
    output_dir = Path(settings.DEFAULT_OUTPUT_DIR)

    print(f"Iniciando depuração com certificado: {pfx_path.name}")
    browser_mgr = BrowserManager(
        pfx_path=pfx_path,
        pfx_password=pfx_pass,
        headless=False,
        downloads_path=output_dir
    )

    try:
        page = browser_mgr.iniciar()
        print("Acessando portal do FGTS Digital...")
        page.goto("https://fgtsdigital.sistema.gov.br/portal", wait_until="domcontentloaded")
        time.sleep(3)

        print("Clicando em Entrar com gov.br...")
        page.locator("button:has-text('Entrar com gov.br')").first.click()
        
        print("Aguardando SSO gov.br carregar a tela de login...")
        # Aguarda chegar na página de login do SSO (após o redirect de authorize)
        page.wait_for_url("**/sso.acesso.gov.br/login**", timeout=25000)
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        print(f"URL atual no Gov.br: {page.url}")

        # Localizar especificamente o botão de certificado digital
        cert_locators = [
            "#login-certificate",
            "button:has-text('Seu certificado digital')",
            "button:has-text('certificado digital')",
            "a:has-text('Seu certificado digital')",
            "div:has-text('Seu certificado digital')",
            "[id*='cert']"
        ]
        for sel_test in cert_locators:
            loc = page.locator(sel_test)
            count = loc.count()
            print(f"Seletor '{sel_test}': count = {count}")
            if count > 0:
                for i in range(count):
                    el = loc.nth(i)
                    print(f"   -> visível: {el.is_visible()}, texto: '{el.inner_text().strip()}', tag: {el.evaluate('e => e.tagName')}")


        # Tenta clicar no botão 'Seu certificado digital'
        print("\n--- Clicando em 'Seu certificado digital' via #login-certificate ---")
        btn = page.locator("#login-certificate").first
        if btn.is_visible():
            print("Botão #login-certificate visível! Clicando...")
            btn.click()
            print("Clique efetuado. Aguardando até 15 segundos para observar redirecionamento...")
            for s in range(15):
                time.sleep(1)
                print(f"[{s+1}s] URL: {page.url}")
                if "fgtsdigital" in page.url:
                    print("--> REDIRECIONADO PARA FGTS DIGITAL COM SUCESSO!")
                    break
        else:
            print("Botão de certificado não está visível!")

        # Screenshot pós-clique
        pos_foto = Path("data/logs/apos_clique_cert.png")
        page.screenshot(path=str(pos_foto))
        print(f"Screenshot salva em: {pos_foto}")

    finally:
        browser_mgr.fechar()

if __name__ == "__main__":
    debug_govbr()
