"""
Scripts de inicialização do Windows (.bat/.cmd), conforme o padrão do workspace
(Skills/Padrões/padrao-geracao-scripts-windows-crlf.md):

- CRLF em todas as linhas: com LF puro o cmd.exe executa pedaços de linha como comandos;
- o .gitattributes força CRLF na extração (vale também para clones sem core.autocrlf);
- só ASCII: o console usa a página de código 850 e um acento gravado em ANSI aparece
  trocado (ex.: "Automação" vira "AutomaþÒo" no título);
- entra na pasta do script com aspas (a pasta do projeto tem espaço e acento).
"""

from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS = sorted(list(RAIZ.glob("*.bat")) + list(RAIZ.glob("*.cmd")))


def test_existem_scripts_de_inicializacao():
    assert {p.name for p in SCRIPTS} >= {"iniciar.bat", "iniciar_com_console.bat"}


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_todas_as_linhas_terminam_em_crlf(script):
    dados = script.read_bytes()
    assert dados.endswith(b"\r\n"), "a última linha também precisa de CRLF"
    assert dados.count(b"\n") == dados.count(b"\r\n"), "há linha terminada só com LF"


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_somente_ascii(script):
    dados = script.read_bytes()
    fora = sorted({b for b in dados if b > 127})
    assert not fora, f"bytes fora do ASCII (acentos aparecem trocados no console): {fora}"


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_entra_na_pasta_do_script_com_aspas(script):
    assert 'cd /d "%~dp0"' in script.read_text(encoding="ascii", errors="replace")


def test_gitattributes_forca_crlf_nos_scripts():
    regras = (RAIZ / ".gitattributes").read_text(encoding="utf-8").splitlines()
    for padrao in ("*.bat", "*.cmd"):
        assert any(l.split()[:1] == [padrao] and "eol=crlf" in l.split() for l in regras), padrao
