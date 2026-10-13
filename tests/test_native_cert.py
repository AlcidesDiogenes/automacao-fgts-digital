import sys
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from playwright.sync_api import sync_playwright

def test_native():
    user_data_dir = Path("data/chrome_profile").resolve()
    user_data_dir.mkdir(parents=True, exist_ok=True)

    # Configuração de auto-seleção nativa de certificados do Windows para o Chrome
    auto_select = [
        {"pattern": "https://*.acesso.gov.br", "filter": {}},
        {"pattern": "https://*.sistema.gov.br", "filter": {}}
    ]

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            channel="chrome",
            headless=False,
            ignore_default_args=["--enable-automation"],
            args=[
                "--start-maximized",
                "--test-type",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
                f"--auto-select-certificate-for-urls={json.dumps(auto_select)}"
            ]
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        print("Navegando para o FGTS Digital com certificado nativo do Windows...")
        page.goto("https://fgtsdigital.sistema.gov.br/portal", wait_until="domcontentloaded")
        page.locator("button:has-text('Entrar com gov.br')").first.click()
        print("Aguardando SSO Gov.br...")
        page.wait_for_url("**/sso.acesso.gov.br/login**", timeout=25000)
        print("Página de login carregada sem restrições de proxy!")
        import time
        btn = page.locator("#login-certificate").first
        if btn.is_visible():
            print("Clicando no botão de certificado com Schannel nativo do Windows...")
            btn.click()
            print("Aguardando 15s para observar redirecionamento...")
            for s in range(15):
                time.sleep(1)
                print(f"[{s+1}s] URL: {page.url}")
                if "fgtsdigital" in page.url and "acessogov" not in page.url:
                    print("--> AUTENTICADO NO FGTS DIGITAL COM SUCESSO!")
                    break

        page.screenshot(path="data/logs/apos_clique_nativo.png")
        print("Screenshot salva em data/logs/apos_clique_nativo.png")
        ctx.close()

if __name__ == "__main__":
    test_native()
