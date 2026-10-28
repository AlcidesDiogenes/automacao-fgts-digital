"""
Linha de comando: a competência é obrigatória e digitada (MM/AAAA), e o robô não começa
se a planilha tiver empresa com outra competência (ADR-0007). O navegador é substituído
por um que falha se for aberto: nenhum desses casos pode chegar ao portal.
"""

import argparse

import pandas as pd
import pytest

import main
import src.core.browser as browser_mod


class NavegadorProibido:
    def __init__(self, *a, **k):
        raise AssertionError("o navegador não deveria ser aberto")


@pytest.fixture(autouse=True)
def sem_navegador(monkeypatch):
    monkeypatch.setattr(browser_mod, "BrowserManager", NavegadorProibido)


def _args(tmp_path, competencia, linhas=None):
    planilha = tmp_path / "fila.xlsx"
    pd.DataFrame(
        linhas or [["11444777000161", "ALFA COMERCIO FICTICIO LTDA", "09/2026"]],
        columns=["CNPJ", "Razao_Social", "Competencia"],
    ).to_excel(planilha, index=False)
    return argparse.Namespace(
        competencia=competencia, excel=str(planilha), output=str(tmp_path / "saida"),
        headless=False, conferir=True,
    )


@pytest.mark.parametrize("competencia", [None, "", "anterior", "atual", "13/2026", "2026/09"])
def test_cli_exige_competencia_valida(tmp_path, competencia):
    with pytest.raises(SystemExit) as saida:
        main.executar_modo_cli(_args(tmp_path, competencia))
    assert saida.value.code == 2


def test_cli_bloqueia_planilha_com_outra_competencia(tmp_path):
    args = _args(tmp_path, "09/2026", [
        ["11444777000161", "ALFA COMERCIO FICTICIO LTDA", "09/2026"],
        ["33222111000130", "GAMA INDUSTRIA MODELO S/A", "08/2026"],
    ])
    with pytest.raises(SystemExit) as saida:
        main.executar_modo_cli(args)
    assert saida.value.code == 3


def test_cli_com_competencia_valida_segue_para_o_navegador(tmp_path):
    # Competência certa e planilha coerente: só para ao tentar abrir o navegador
    with pytest.raises(AssertionError, match="navegador não deveria ser aberto"):
        main.executar_modo_cli(_args(tmp_path, "9/2026"))


def test_argumento_competencia_sem_valor_padrao():
    parser = main.criar_parser_argumentos()
    assert parser.parse_args(["--cli"]).competencia is None
