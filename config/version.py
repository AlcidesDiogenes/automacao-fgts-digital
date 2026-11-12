"""
Informações centrais de versão e metadados para controle de atualizações OTA (Over-The-Air).
"""

VERSION = "1.0.2"
GITHUB_REPO = "AlcidesDiogenes/automacao-fgts-digital"
GITHUB_RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def obter_versao_atual() -> str:
    """Retorna a versão atual do sistema em formato string 'X.Y.Z'."""
    return VERSION
