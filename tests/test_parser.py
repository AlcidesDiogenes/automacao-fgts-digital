"""
Testes unitários para o módulo de parsing e utilitários do FGTS Digital.
"""

from datetime import datetime
import pytest
from src.modules.fgts_digital.parser import (
    limpar_cnpj,
    formatar_cnpj,
    validar_cnpj,
    normalizar_competencia,
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


def test_normalizar_competencia_formatos_aceitos():
    assert normalizar_competencia("09/2026") == "09/2026"
    assert normalizar_competencia("9/2026") == "09/2026"
    assert normalizar_competencia(" 09-2026 ") == "09/2026"
    assert normalizar_competencia("09.2026") == "09/2026"
    # Célula de data do Excel lida como texto
    assert normalizar_competencia("2026-09-01 00:00:00") == "09/2026"
    assert normalizar_competencia("2026-12-01") == "12/2026"


def test_normalizar_competencia_rejeita_invalidas():
    # "anterior"/"atual" não são mais aceitos: a competência é sempre digitada
    for invalida in ("", None, "anterior", "atual", "13/2026", "00/2026", "2026/09", "09/26",
                     "setembro/2026", "09/1999", "09/2101", "nan"):
        assert normalizar_competencia(invalida) is None, invalida


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


def test_extrair_valor_fgts_com_rescisoria_e_mensal():
    from src.modules.fgts_digital.parser import extrair_valor_fgts_de_texto
    texto_tela = """
    Competência de Apuração
    09/2026
    Total Devedor
    R$ 2.585,09

    Rescisória - Vencimento da Guia: 14/10/2026
    FGTS
    Todos os valores exibidos estão expressos em reais (R$).
    Competência de Referência  Vencimento dos Débitos  Quantidade de Trabalhadores  FGTS Mensal  FGTS Rescisório  Indenização Compensatória  Encargos FGTS
    11/09/2026  1  0,00  0,00  327,26  36,60
    Total  0,00  0,00  327,26  36,60

    Mensal - Vencimento da Guia: 20/10/2026
    Guias relacionadas aguardando pagamento
    0126101366600671-1
    FGTS
    Todos os valores exibidos estão expressos em reais (R$).
    Competência de Referência  Vencimento dos Débitos  Quantidade de Trabalhadores  FGTS Mensal  FGTS Rescisório
    20/10/2026  6  1.805,65  0,00
    Total  1.805,65  0,00

    Consignado
    Vencimento dos Débitos  Quantidade de Trabalhadores  Consignado  Total
    20/10/2026  1  415,58  415,58
    Total Consignado  415,58

    Total Guia  2.221,23
    """
    # Deve ignorar o Total Devedor de 2.585,09 e a Rescisória de 327,26, pegando o Total Guia do Mensal de 2.221,23!
    val = extrair_valor_fgts_de_texto(texto_tela)
    assert val == 2221.23


def test_extrair_valor_fgts_apenas_mensal():
    from src.modules.fgts_digital.parser import extrair_valor_fgts_de_texto
    texto_tela = """
    Competência de Apuração: 09/2026
    Total Devedor: R$ 1.805,65

    Mensal - Vencimento da Guia: 20/10/2026
    FGTS
    Competência  Trabalhadores  FGTS Mensal
    20/10/2026   6              1.805,65
    Total Guia   1.805,65
    """
    assert extrair_valor_fgts_de_texto(texto_tela) == 1805.65


def test_extrair_valor_fgts_multiplos_cards_mensais():
    """
    Testa o cenário real com 2 cards mensais na mesma competência:
    Card 1: Guia residual (1 trabalhador) -> Total Guia: R$ 23,45 (vencimento 19/10/2026)
    Card 2: Guia principal (96 trabalhadores) -> FGTS: 10.000,00 + Consignado: 2.345,67 -> Total Guia: R$ 12.345,67 (vencimento 20/10/2026)
    Total Devedor da página: R$ 12.369,12 (soma de ambos)
    """
    from src.modules.fgts_digital.parser import extrair_valor_fgts_de_texto
    texto_tela = """
    Competência de Apuração
    09/2026
    Total Devedor
    R$ 12.369,12

    Mensal - Vencimento da Guia: 19/10/2026
    FGTS
    Todos os valores exibidos estão expressos em reais (R$).
    Competência de Referência Vencimento dos Débitos Quantidade de Trabalhadores FGTS Mensal FGTS Rescisório Indenização Compensatória Encargos FGTS
    09/2026 19/10/2026 1 23,45 0,00 0,00 0,00
    Total 23,45 0,00 0,00 0,00
    Total Guia 23,45

    Mensal - Vencimento da Guia: 20/10/2026
    Guias relacionadas aguardando pagamento
    0126101344400555-1
    FGTS
    Todos os valores exibidos estão expressos em reais (R$).
    Competência de Referência Vencimento dos Débitos Quantidade de Trabalhadores FGTS Mensal FGTS Rescisório Indenização Compensatória Encargos FGTS
    09/2026 20/10/2026 96 10.000,00 0,00 0,00 0,00
    Total 10.000,00 0,00 0,00 0,00

    Consignado
    Vencimento dos Débitos Quantidade de Trabalhadores Consignado Total
    20/10/2026 23 2.345,67 2.345,67
    Total Consignado 2.345,67

    Total Guia 12.345,67
    """

    # 1. Com fgts_esperado da folha (12.345,67 = FGTS + Consignado), deve selecionar Card 2 perfeitamente
    val = extrair_valor_fgts_de_texto(texto_tela, fgts_esperado=12345.67)
    assert val == 12345.67

    # 2. Sem fgts_esperado (0.0), deve selecionar o card principal de maior valor
    val_max = extrair_valor_fgts_de_texto(texto_tela, fgts_esperado=0.0)
    assert val_max == 12345.67




def test_nomenclatura_nao_altera_palavras_que_contem_tags():
    from src.modules.fgts_digital.parser import formatar_nome_documento
    ctx = {"competencia": "09/2026", "cnpj": "12345678000190", "razao_social": "Alfa"}
    assert formatar_nome_documento("Comprovante - {competencia}", ctx) == "Comprovante - 09-2026.pdf"
    assert formatar_nome_documento("Guia Empresarial - Comp", ctx) == "Guia Empresarial - 09-2026.pdf"
    assert formatar_nome_documento("{cnpj}_{empresa}", ctx) == "12345678000190_Alfa.pdf"
