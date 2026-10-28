"""
Diagnóstico manual: login real no FGTS Digital pelo robô (FGTSDigitalBot.login).
Usa o certificado instalado no Windows, informa SUCESSO/FALHA e salva um screenshot
da tela final em data/logs/tela_pos_login.png. Acessa o portal real (não é teste automático).

Uso (na raiz do projeto):
    venv/Scripts/python.exe scripts/diagnostico/login_real.py
"""

import sys
from pathlib import Path

# Garante inclusão do diretório raiz no PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parents[2]  # scripts/diagnostico/ -> raiz do projeto
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.browser import BrowserManager
from src.modules.fgts_digital.bot import FGTSDigitalBot
from config import settings

def testar_login_real():
    output_dir = Path(settings.DEFAULT_OUTPUT_DIR)

    print("Testando com o certificado instalado no Windows")
    browser_mgr = BrowserManager(
        headless=False,
        downloads_path=output_dir
    )

    try:
        page = browser_mgr.iniciar()
        bot = FGTSDigitalBot(page=page, output_base_dir=output_dir)
        sucesso = bot.login()
        print(f"\nResultado do Login: {'SUCESSO' if sucesso else 'FALHA'}")
        print(f"URL Final: {page.url}")
        
        # Salva screenshot da tela final pós-login
        foto = settings.LOGS_DIR / "tela_pos_login.png"
        foto.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(foto))
        print(f"Screenshot salva em: {foto}")
    finally:
        browser_mgr.fechar()

if __name__ == "__main__":
    testar_login_real()
