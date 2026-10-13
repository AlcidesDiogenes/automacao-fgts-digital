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


def test_gerar_relatorio_divergencias(tmp_path):
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

    # Verifica se gerou o arquivo de divergências
    arquivos_div = list(tmp_path.glob("DIVERGENCIAS_FGTS_*.xlsx"))
    assert len(arquivos_div) == 1
    assert arquivos_div[0].exists()


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
    assert list(tmp_path.glob("DIVERGENCIAS_FGTS_*.xlsx"))
