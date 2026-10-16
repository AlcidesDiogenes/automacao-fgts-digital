import pytest
from pathlib import Path
from src.modules.folha_relatorio.parser_pdf import RelatorioFolhaParser

def test_parse_relatorio_pdf_real():
    pdf_path = Path("data/relatorio_encargos_exemplo.pdf")
    if not pdf_path.exists():
        pytest.skip("Arquivo local de teste ignorado no repositório por sigilo de dados (LGPD).")
    
    empresas = RelatorioFolhaParser.parse_pdf(pdf_path)
    assert len(empresas) == 18, f"Esperava 18 entidades, obteve {len(empresas)}"
    
    # Verifica EMPRESA A
    empresa_a = next((e for e in empresas if "11444777000161" in e["documento_limpo"]), None)
    assert empresa_a is not None
    assert empresa_a["competencia"] == "09/2026"
    assert empresa_a["fgts_mensal"] == 1500.00
    assert empresa_a["consignado"] == 250.50
    assert empresa_a["total_fgts"] == 1750.50  # 1500.00 + 250.50 na guia única
    assert empresa_a["fgts_rescisorio"] == 2000.00
    assert len(empresa_a["funcionarios_rescisorios"]) == 1
    assert "FULANO" in empresa_a["funcionarios_rescisorios"][0]["nome"]

    # Verifica ALFA COMERCIO FICTICIO (filiais 1 e 3)
    empresa_b = next((e for e in empresas if "11444777000161" in e["documento_limpo"]), None)
    assert empresa_b is not None
    assert empresa_b["competencia"] == "09/2026"
    assert empresa_b["fgts_mensal"] == 4000.00
    assert empresa_b["consignado"] == 1100.00
    assert empresa_b["total_fgts"] == 5100.00

    # Verifica exportação Excel
    out_xlsx = Path("data/output/teste_export_encargos.xlsx")
    RelatorioFolhaParser.exportar_para_excel(empresas, out_xlsx)
    assert out_xlsx.exists()
    assert out_xlsx.stat().st_size > 0

    # Verifica exportação PDF
    out_pdf = Path("data/output/teste_export_encargos.pdf")
    RelatorioFolhaParser.exportar_para_pdf(empresas, out_pdf)
    assert out_pdf.exists()
    assert out_pdf.stat().st_size > 0


def test_carregar_regras_parametros():
    regras = RelatorioFolhaParser.carregar_regras_parametros()
    assert isinstance(regras, dict)
    assert "fgts_mensal" in regras
    assert "emp_cred_trab" in regras
    assert "fgts_compl" in regras
    assert "emp_cred_tr_resc" in regras
    assert "simples_dom" in regras
    assert regras["fgts_mensal"] is True
    assert regras["emp_cred_trab"] is True


def test_parse_com_regras_sem_consignado():
    pdf_path = Path("data/relatorio_encargos_exemplo.pdf")
    if not pdf_path.exists():
        pytest.skip("Arquivo local de teste ignorado.")

    regras = {
        "fgts_mensal": True,
        "emp_cred_trab": False,
        "fgts_compl": True,
        "emp_cred_tr_resc": False,
        "simples_dom": False
    }
    empresas = RelatorioFolhaParser.parse_pdf(pdf_path, regras_encargos=regras)
    empresa_a = next((e for e in empresas if "11444777000161" in e["documento_limpo"]), None)
    assert empresa_a is not None
    # Como emp_cred_trab está desativado nesta regra, total_fgts deve ser apenas fgts_mensal
    assert empresa_a["total_fgts"] == 1500.00

