"""
Módulo de configurações centrais da aplicação.
Carrega variáveis de ambiente e define caminhos e padrões do sistema.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Diretório raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# Tenta carregar o arquivo .env do diretório config ou da raiz
env_config = BASE_DIR / "config" / ".env"
env_root = BASE_DIR / ".env"
if env_config.exists():
    load_dotenv(env_config)
elif env_root.exists():
    load_dotenv(env_root)

# Configurações de caminhos (sempre absolutos, a partir da raiz do projeto,
# para não depender da pasta de onde o programa foi aberto)
DATA_DIR = BASE_DIR / "data"
DEFAULT_OUTPUT_DIR = DATA_DIR / "output"
DEFAULT_EXCEL_PATH = DATA_DIR / "empresas_modelo.xlsx"
LOGS_DIR = DATA_DIR / "logs"
BROWSER_PROFILE_DIR = DATA_DIR / "browser_profile"
PARAMETROS_PATH = BASE_DIR / "config" / "parametros.json"


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
