"""
Testes unitários para o módulo de parsing e utilitários do FGTS Digital.
"""

from datetime import datetime
import pytest
from src.modules.fgts_digital.parser import (
    limpar_cnpj,
    formatar_cnpj,
    validar_cnpj,
    calcular_competencia,
    converter_valor_br,
    sanitizar_nome_arquivo
)


def test_limpar_cnpj():
    assert limpar_cnpj("12.345.678/0001-90") == "12345678000190"
    assert limpar_cnpj("12345678000190") == "12345678000190"
    assert limpar_cnpj(" 12.345.678/0001-90 ") == "12345678000190"
    assert limpar_cnpj("") == ""


def test_formatar_cnpj():
    assert formatar_cnpj("12345678000190") == "12.345.678/0001-90"
    assert formatar_cnpj("12.345.678/0001-90") == "12.345.678/0001-90"


def test_validar_cnpj():
    assert validar_cnpj("12345678000190") is True
    assert validar_cnpj("12.345.678/0001-90") is True
    # Inválidos
    assert validar_cnpj("11111111111111") is False
    assert validar_cnpj("123") is False
    assert validar_cnpj("") is False


def test_calcular_competencia():
    # Mês de referência: Outubro de 2026
    data_ref = datetime(2026, 10, 15)

    assert calcular_competencia("atual", data_ref) == "10/2026"
    assert calcular_competencia("anterior", data_ref) == "09/2026"

    # Virada de ano: Janeiro de 2027
    data_jan = datetime(2027, 1, 10)
    assert calcular_competencia("anterior", data_jan) == "12/2026"

    # Competência customizada
    assert calcular_competencia("05/2026", data_ref) == "05/2026"
    assert calcular_competencia("05-2026", data_ref) == "05/2026"


def test_converter_valor_br():
    assert converter_valor_br("R$ 1.250,45") == 1250.45
    assert converter_valor_br("1.250,45") == 1250.45
    assert converter_valor_br("250,00") == 250.00
    assert converter_valor_br("R$ 0,00") == 0.0
    assert converter_valor_br("") == 0.0


def test_sanitizar_nome_arquivo():
    assert sanitizar_nome_arquivo('Empresa/Alfa: Ltda*? "Teste"') == "EmpresaAlfa Ltda Teste"


def test_formatar_nome_documento():
    from src.modules.fgts_digital.parser import formatar_nome_documento
    ctx = {
        "competencia": "09/2026",
        "cnpj": "11.444.777/0001-61",
        "razao_social": "ALFA COMERCIO FICTICIO"
    }
    # Padrões solicitados pelo usuário
    assert formatar_nome_documento("FGTS - Competencia", ctx) == "FGTS - 09-2026.pdf"
    assert formatar_nome_documento("RE FGTS - Competencia", ctx) == "RE FGTS - 09-2026.pdf"
    assert formatar_nome_documento("Consignado FGTS - Competencia", ctx) == "Consignado FGTS - 09-2026.pdf"

    # Com chaves
    assert formatar_nome_documento("FGTS - {competencia}", ctx) == "FGTS - 09-2026.pdf"

    # Com Empresa e CNPJ
    assert formatar_nome_documento("FGTS - Competencia - Empresa", ctx) == "FGTS - 09-2026 - ALFA COMERCIO FICTICIO.pdf"
    assert formatar_nome_documento("FGTS_Competencia_CNPJ", ctx) == "FGTS_09-2026_11444777000161.pdf"

