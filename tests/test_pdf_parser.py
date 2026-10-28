"""
Testes do leitor do relatório "PAGAMENTO DE ENCARGOS" do Sistema Domínio.

Usa um PDF sintético no mesmo layout do relatório real (tests/conftest.py::gerar_pdf_dominio),
com empresas, empregados e valores FICTÍCIOS. Substitui a versão anterior, que lia o PDF real
de clientes em data/ (LGPD; ver docs/decisoes/ADR-0006).

Cenários cobertos: FGTS em várias linhas, mesma empresa em duas páginas (filiais), FGTS
complementar, consignado do trabalhador ativo e rescindido, página de FGTS rescisório com nome
do empregado, empregador doméstico (CPF), regras de leitura ligadas/desligadas, página sem
documento e exportação para Excel/PDF.
"""

import pytest

from conftest import gerar_pdf_dominio
from src.modules.folha_relatorio.parser_pdf import RelatorioFolhaParser

CNPJ_ALFA = "11.444.777/0001-61"
CPF_DOMESTICO = "123.456.789-09"

REGRAS_PADRAO = {
    "fgts_mensal": True,
    "emp_cred_trab": True,
    "fgts_compl": True,
    "emp_cred_tr_resc": False,
    "simples_dom": False,
}

PAGINAS = [
    {   # Matriz: FGTS em 2 linhas, consignado ativo e rescindido, FGTS complementar
        "doc": CNPJ_ALFA, "razao": "ALFA COMERCIO FICTICIO LTDA", "linhas": [
            "Encargo / Valor Base Valor Vencimento",
            "FGTS 1 800,00 09/2026 20/10/2026 800,00",
            "FGTS 2 400,00 09/2026 20/10/2026 400,00",
            "Total: 1.200,00 1.200,00",
            "FGTS Compl. 1 50,00 09/2026 20/10/2026 50,00",
            "Total: 50,00 50,00",
            "Emp. Créd. Trab. 1 150,50 09/2026 20/10/2026 150,50",
            "Total: 150,50 150,50",
            "Emp. Créd. Tr. Resc. 1 30,00 09/2026 20/10/2026 30,00",
            "Total: 30,00 30,00",
            "Total Geral: 1.430,50 1.430,50",
        ],
    },
    {   # Filial com o mesmo CNPJ em outra página: deve acumular
        "doc": CNPJ_ALFA, "razao": "ALFA COMERCIO FICTICIO LTDA", "linhas": [
            "FGTS 3 100,00 09/2026 20/10/2026 100,00",
            "Total: 100,00 100,00",
            "Total Geral: 100,00 100,00",
        ],
    },
    {   # Página de FGTS rescisório
        "doc": CNPJ_ALFA, "razao": "ALFA COMERCIO FICTICIO LTDA", "linhas": [
            "Código Empregado Valor Competência Vencimento",
            "FULANO DE TAL FICTICIO 1001 2.000,00 2.000,00 FGTS Rescisório 09/2026 10/10/2026",
            "Total: 2.000,00",
            "Total Geral: 2.000,00",
        ],
    },
    {   # Empregador doméstico identificado por CPF
        "doc": CPF_DOMESTICO, "tipo_doc": "CPF", "razao": "EMPREGADOR DOMESTICO FICTICIO", "linhas": [
            "Simples doméstico 1 300,00 09/2026 07/10/2026 300,00",
            "Total: 300,00 300,00",
            "Total Geral: 300,00 300,00",
        ],
    },
]


@pytest.fixture
def pdf_dominio(tmp_path):
    return gerar_pdf_dominio(tmp_path / "relatorio_dominio_ficticio.pdf", PAGINAS)


def _por_doc(empresas, digitos):
    return next(e for e in empresas if e["documento_limpo"] == digitos)


def test_identifica_empresas_por_cnpj_e_cpf(pdf_dominio):
    empresas = RelatorioFolhaParser.parse_pdf(pdf_dominio, regras_encargos=REGRAS_PADRAO)
    assert sorted(e["documento_limpo"] for e in empresas) == ["11444777000161", "12345678909"]
    alfa = _por_doc(empresas, "11444777000161")
    assert alfa["tipo_doc"] == "CNPJ"
    assert alfa["razao_social"] == "ALFA COMERCIO FICTICIO LTDA"
    assert alfa["competencia"] == "09/2026"
    dom = _por_doc(empresas, "12345678909")
    assert dom["tipo_doc"] == "CPF"
    assert dom["razao_social"] == "EMPREGADOR DOMESTICO FICTICIO"


def test_soma_fgts_de_varias_linhas_e_paginas_da_mesma_empresa(pdf_dominio):
    alfa = _por_doc(RelatorioFolhaParser.parse_pdf(pdf_dominio, regras_encargos=REGRAS_PADRAO), "11444777000161")
    assert alfa["fgts_mensal_regular"] == 1300.00   # 1.200,00 (matriz) + 100,00 (filial)
    assert alfa["fgts_compl"] == 50.00
    assert alfa["fgts_mensal"] == 1350.00


def test_consignado_ativo_e_rescindido_separados(pdf_dominio):
    alfa = _por_doc(RelatorioFolhaParser.parse_pdf(pdf_dominio, regras_encargos=REGRAS_PADRAO), "11444777000161")
    assert alfa["consignado_trabalhador"] == 150.50
    assert alfa["consignado_resc"] == 30.00
    assert alfa["consignado"] == 150.50   # rescindido fora por padrão


def test_total_da_guia_com_regras_padrao(pdf_dominio):
    alfa = _por_doc(RelatorioFolhaParser.parse_pdf(pdf_dominio, regras_encargos=REGRAS_PADRAO), "11444777000161")
    assert alfa["total_fgts"] == 1500.50  # 1.300,00 + 50,00 + 150,50


def test_rescisorio_fica_fora_da_guia_mensal_e_guarda_empregado(pdf_dominio):
    alfa = _por_doc(RelatorioFolhaParser.parse_pdf(pdf_dominio, regras_encargos=REGRAS_PADRAO), "11444777000161")
    assert alfa["fgts_rescisorio"] == 2000.00
    assert [f["nome"] for f in alfa["funcionarios_rescisorios"]] == ["FULANO DE TAL FICTICIO"]
    assert alfa["total_geral"] == 3500.50  # guia mensal + rescisório


def test_regra_sem_consignado_ativo(pdf_dominio):
    regras = {**REGRAS_PADRAO, "emp_cred_trab": False}
    alfa = _por_doc(RelatorioFolhaParser.parse_pdf(pdf_dominio, regras_encargos=regras), "11444777000161")
    assert alfa["total_fgts"] == 1350.00


def test_regra_com_consignado_rescindido(pdf_dominio):
    regras = {**REGRAS_PADRAO, "emp_cred_tr_resc": True}
    alfa = _por_doc(RelatorioFolhaParser.parse_pdf(pdf_dominio, regras_encargos=regras), "11444777000161")
    assert alfa["consignado"] == 180.50
    assert alfa["total_fgts"] == 1530.50


def test_simples_domestico_so_entra_na_guia_se_a_regra_estiver_ligada(pdf_dominio):
    dom = _por_doc(RelatorioFolhaParser.parse_pdf(pdf_dominio, regras_encargos=REGRAS_PADRAO), "12345678909")
    assert dom["outros_encargos"] == 300.00
    assert dom["total_fgts"] == 0.00
    dom_ligado = _por_doc(
        RelatorioFolhaParser.parse_pdf(pdf_dominio, regras_encargos={**REGRAS_PADRAO, "simples_dom": True}),
        "12345678909",
    )
    assert dom_ligado["total_fgts"] == 300.00


def test_pagina_sem_cnpj_nem_cpf_e_ignorada(tmp_path):
    pdf = gerar_pdf_dominio(tmp_path / "sem_doc.pdf", [
        {"doc": "SEM DOCUMENTO", "razao": "CAPA DO RELATORIO", "linhas": ["Total: 10,00"]},
        PAGINAS[1],
    ])
    empresas = RelatorioFolhaParser.parse_pdf(pdf, regras_encargos=REGRAS_PADRAO)
    assert [e["documento_limpo"] for e in empresas] == ["11444777000161"]


def test_arquivo_inexistente(tmp_path):
    with pytest.raises(FileNotFoundError):
        RelatorioFolhaParser.parse_pdf(tmp_path / "nao_existe.pdf")


def test_exporta_para_excel_e_pdf(pdf_dominio, tmp_path):
    empresas = RelatorioFolhaParser.parse_pdf(pdf_dominio, regras_encargos=REGRAS_PADRAO)
    xlsx = RelatorioFolhaParser.exportar_para_excel(empresas, tmp_path / "encargos.xlsx")
    pdf = RelatorioFolhaParser.exportar_para_pdf(empresas, tmp_path / "encargos.pdf")
    assert xlsx.exists() and xlsx.stat().st_size > 0
    assert pdf.exists() and pdf.stat().st_size > 0


def test_carregar_regras_parametros():
    regras = RelatorioFolhaParser.carregar_regras_parametros()
    assert isinstance(regras, dict)
    for chave in ("fgts_mensal", "emp_cred_trab", "fgts_compl", "emp_cred_tr_resc", "simples_dom"):
        assert chave in regras
