"""
Empacotamento (PyInstaller + Inno Setup) e versão do instalador.

O instalador é distribuído por Release pública no GitHub (atualização OTA): nada de dados de
clientes pode ir junto. Em 12/11/2026 o `fgts_digital.spec` empacotava
`data/relatorio_encargos_exemplo.pdf`, que era um relatório REAL do Domínio (LGPD).
"""

import re
from pathlib import Path

from config.version import VERSION

RAIZ = Path(__file__).resolve().parents[1]
SPEC = (RAIZ / "fgts_digital.spec").read_text(encoding="utf-8")
ISS = (RAIZ / "installer" / "FGTS_Digital_Setup.iss").read_text(encoding="utf-8")


def test_spec_nao_empacota_nada_da_pasta_data():
    # data/ guarda relatórios, planilhas, logs e perfis do navegador do usuário (fora do Git).
    assert not re.search(r"""['"]data[/\\]""", SPEC), "o instalador não pode levar arquivos de data/"


def test_spec_nao_empacota_planilhas_pdfs_ou_env_reais():
    for proibido in (".xlsx", ".xls", ".csv", ".db", "config/.env'", 'config/.env"', ".pfx"):
        assert proibido not in SPEC, f"o spec não pode empacotar {proibido}"


def test_atualizacao_apaga_o_relatorio_real_das_versoes_antigas():
    # O Inno Setup não remove arquivos que saíram do pacote; sem isso a cópia da v1.0.1 ficaria no PC.
    assert "[InstallDelete]" in ISS
    assert r'Type: files; Name: "{app}\_internal\data\relatorio_encargos_exemplo.pdf"' in ISS


def test_versao_do_instalador_igual_a_do_app():
    m = re.search(r'#define MyAppVersion "([^"]+)"', ISS)
    assert m and m.group(1) == VERSION
    assert f"OutputBaseFilename=FGTS_Digital_Instalador_v{VERSION}" in ISS
