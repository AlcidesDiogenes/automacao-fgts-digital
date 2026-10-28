"""
Testes para leitura e escrita de planilhas Excel.
"""

from pathlib import Path
import pytest
from src.core.excel_manager import ExcelManager


def test_ler_planilha_modelo(tmp_path):
    caminho_modelo = tmp_path / "modelo.xlsx"
    ExcelManager.criar_planilha_modelo(caminho_modelo)

    assert caminho_modelo.exists()

    empresas = ExcelManager.ler_empresas(caminho_modelo, competencia_padrao="09/2026")
    assert len(empresas) >= 2
    assert empresas[0]["cnpj"] == "12345678000190"
    assert empresas[0]["competencia"] == "09/2026"
    assert "Empresa Exemplo Alfa" in empresas[0]["razao_social"]


def test_gerar_relatorio_execucao(tmp_path):
    resultados = [
        {
            "cnpj": "12345678000190",
            "razao_social": "Empresa Alfa Ltda",
            "competencia": "09/2026",
            "status": "Sucesso - Guia Emitida",
            "valor_guia": 1450.50,
            "arquivo_guia": "GFD_09-2026_12345678000190.pdf",
            "arquivo_relatorio": "Relatorio_09-2026_12345678000190.pdf",
            "detalhes": "Guia gerada com sucesso"
        },
        {
            "cnpj": "98765432000110",
            "razao_social": "Empresa Beta S/A",
            "competencia": "09/2026",
            "status": "Pendente eSocial",
            "valor_guia": 0.0,
            "arquivo_guia": "",
            "arquivo_relatorio": "",
            "detalhes": "Folha não fechada no eSocial"
        }
    ]

    rel_path = ExcelManager.gerar_relatorio_execucao(resultados, tmp_path, "09/2026")
    assert rel_path.exists()
    assert rel_path.suffix == ".xlsx"


def test_gerar_relatorio_apenas_um_arquivo(tmp_path):
    resultados = [
        {
            "cnpj": "12345678000190",
            "razao_social": "Empresa Alfa Ltda",
            "competencia": "09/2026",
            "status": "Sucesso - Guia Emitida",
            "fgts_esperado": 1450.50,
            "valor_guia": 1450.50,
            "arquivo_guia": "GFD_09-2026_12345678000190.pdf",
            "detalhes": "Guia gerada com sucesso"
        },
        {
            "cnpj": "98765432000110",
            "razao_social": "Empresa Beta S/A",
            "competencia": "09/2026",
            "status": "Divergência de Valores (Não Emitida)",
            "fgts_esperado": 3500.00,
            "valor_guia": 3800.00,
            "arquivo_guia": "",
            "detalhes": "Divergência detectada: folha R$ 3500.00 vs portal R$ 3800.00"
        }
    ]

    rel_path = ExcelManager.gerar_relatorio_execucao(resultados, tmp_path, "09/2026")
    assert rel_path.exists()
    assert rel_path.name.startswith("Relatorio_FGTS_Digital_")

    # Garante que NÃO gera relatório duplicado de divergências (apenas o Relatorio_FGTS_Digital)
    arquivos_div = list(tmp_path.glob("DIVERGENCIAS_FGTS_*.xlsx"))
    assert len(arquivos_div) == 0

    # Verifica que o diretório contém exatamente 1 arquivo gerado
    todos_xlsx = list(tmp_path.glob("*.xlsx"))
    assert len(todos_xlsx) == 1
    assert todos_xlsx[0] == rel_path


def test_gerar_relatorio_conferencia(tmp_path):
    resultados = [
        {
            "cnpj": "12345678000190",
            "razao_social": "Empresa Alfa Ltda",
            "competencia": "09/2026",
            "status": "Conferido (Valores Iguais)",
            "fgts_esperado": 1450.50,
            "valor_guia": 1450.50,
            "diferenca": 0.0,
            "arquivo_guia": "",
            "arquivo_relatorio": "",
            "detalhes": "Valores idênticos! Relatório: R$ 1450.50 | FGTS Digital: R$ 1450.50."
        },
        {
            "cnpj": "98765432000110",
            "razao_social": "Empresa Beta S/A",
            "competencia": "09/2026",
            "status": "Divergência de Valores",
            "fgts_esperado": 3500.00,
            "valor_guia": 3800.00,
            "diferenca": 300.0,
            "arquivo_guia": "",
            "arquivo_relatorio": "",
            "detalhes": "DIVERGÊNCIA! Relatório: R$ 3500.00 | FGTS Digital: R$ 3800.00"
        }
    ]

    rel_path = ExcelManager.gerar_relatorio_execucao(resultados, tmp_path, "09/2026")
    assert rel_path.exists()
    assert rel_path.name.startswith("Relatorio_FGTS_Digital_")
    assert not list(tmp_path.glob("DIVERGENCIAS_FGTS_*.xlsx"))



def _planilha(destino, linhas):
    import pandas as pd
    pd.DataFrame(linhas, columns=["CNPJ", "Razao_Social", "Competencia"]).to_excel(destino, index=False)
    return destino


def test_competencias_divergentes_lista_so_as_diferentes(tmp_path):
    caminho = _planilha(tmp_path / "fila.xlsx", [
        ["11444777000161", "ALFA COMERCIO FICTICIO LTDA", "09/2026"],
        ["22333444000181", "BETA SERVICOS EXEMPLO LTDA", ""],          # sem competência: usa a digitada
        ["33222111000130", "GAMA INDUSTRIA MODELO S/A", "08/2026"],    # diferente
        ["44555666000102", "DELTA TRANSPORTES TESTE LTDA", "9/2026"],  # mesmo mês, outro formato
    ])
    empresas = ExcelManager.ler_empresas(caminho, competencia_padrao="09/2026")
    divergentes = ExcelManager.competencias_divergentes(empresas, "09/2026")
    assert [(e["cnpj"], e["competencia"]) for e in divergentes] == [("33222111000130", "08/2026")]


def test_competencias_divergentes_trata_valor_invalido_como_divergente(tmp_path):
    caminho = _planilha(tmp_path / "fila.xlsx", [["11444777000161", "ALFA COMERCIO FICTICIO LTDA", "setembro"]])
    empresas = ExcelManager.ler_empresas(caminho, competencia_padrao="09/2026")
    assert len(ExcelManager.competencias_divergentes(empresas, "09/2026")) == 1


def test_competencia_em_celula_de_data_do_excel(tmp_path):
    import datetime as dt
    caminho = _planilha(tmp_path / "fila.xlsx", [["11444777000161", "ALFA COMERCIO FICTICIO LTDA", dt.datetime(2026, 9, 1)]])
    empresas = ExcelManager.ler_empresas(caminho, competencia_padrao="09/2026")
    assert ExcelManager.competencias_divergentes(empresas, "09/2026") == []
