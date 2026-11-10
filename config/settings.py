"""
Módulo de configurações centrais da aplicação.
Carrega variáveis de ambiente e define caminhos e padrões do sistema.
"""

from pathlib import Path
import os
import sys
from dotenv import load_dotenv

# Diretório raiz do projeto e diretório de recursos estáticos (PyInstaller)
if getattr(sys, "frozen", False):
    # Executável empacotado via PyInstaller
    BASE_DIR = Path(sys.executable).resolve().parent
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    RESOURCE_DIR = BASE_DIR

# Tenta carregar o arquivo .env do diretório config ou da raiz
env_config = BASE_DIR / "config" / ".env"
env_root = BASE_DIR / ".env"
if env_config.exists():
    load_dotenv(env_config)
elif env_root.exists():
    load_dotenv(env_root)

# Configurações de caminhos com verificação de permissão de escrita para ambientes instalados
def _resolver_pasta_dados() -> Path:
    padrao = BASE_DIR / "data"
    try:
        padrao.mkdir(parents=True, exist_ok=True)
        teste = padrao / ".perm_check"
        teste.write_text("ok", encoding="utf-8")
        teste.unlink()
        return padrao
    except (PermissionError, OSError):
        appdata = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "FGTS Digital" / "data"
        appdata.mkdir(parents=True, exist_ok=True)
        return appdata

DATA_DIR = _resolver_pasta_dados()
DEFAULT_OUTPUT_DIR = DATA_DIR / "output"
DEFAULT_EXCEL_PATH = DATA_DIR / "empresas_modelo.xlsx"
LOGS_DIR = DATA_DIR / "logs"
BROWSER_PROFILE_DIR = DATA_DIR / "browser_profile"

def _resolver_parametros_path() -> Path:
    padrao = BASE_DIR / "config" / "parametros.json"
    try:
        padrao.parent.mkdir(parents=True, exist_ok=True)
        if padrao.exists():
            return padrao
        teste = padrao.parent / ".perm_check"
        teste.write_text("ok", encoding="utf-8")
        teste.unlink()
        return padrao
    except (PermissionError, OSError):
        appdata_cfg = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "FGTS Digital" / "config"
        appdata_cfg.mkdir(parents=True, exist_ok=True)
        return appdata_cfg / "parametros.json"

PARAMETROS_PATH = _resolver_parametros_path()


def carregar_parametros() -> dict:
    """Lê config/parametros.json (dicionário vazio se não existir ou estiver inválido)."""
    import json
    try:
        with open(PARAMETROS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def resolver_caminho(caminho) -> Path:
    """Converte um caminho relativo (ex.: 'data/output' do parametros.json) em absoluto a partir de BASE_DIR."""
    p = Path(str(caminho).strip())
    return p if p.is_absolute() else BASE_DIR / p


# Configurações do Navegador
HEADLESS = os.getenv("HEADLESS", "false").lower() in ("true", "1", "yes")
BROWSER_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "60"))

# URLs do Governo
GOV_BR_SSO_URL = "https://sso.acesso.gov.br"
FGTS_DIGITAL_URL = "https://fgtsdigital.sistema.gov.br"
FGTS_DIGITAL_PORTAL_URL = "https://fgtsdigital.sistema.gov.br/portal"

# Garante que a pasta de saída exista
DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
