import pytest
from pathlib import Path
from src.modules.folha_relatorio.parser_pdf import RelatorioFolhaParser

def test_parse_relatorio_pdf_real():
    pdf_path = Path("data/relatorio_encargos_exemplo.pdf")
    if not pdf_path.exists():
        pytest.skip("Arquivo local de teste ignorado no repositório por sigilo de dados (LGPD).")
    
    empresas = RelatorioFolhaParser.parse_pdf(pdf_path)
    assert len(empresas) == 18, f"Esperava 18 entidades, obteve {len(empresas)}"
    
    # Verifica PURO AÇAI
    puro_acai = next((e for e in empresas if "18181688000119" in e["documento_limpo"]), None)
    assert puro_acai is not None
    assert puro_acai["competencia"] == "09/2026"
    assert puro_acai["fgts_mensal"] == 1665.84
    assert puro_acai["consignado"] == 245.46
    assert puro_acai["total_fgts"] == 1911.30  # 1665.84 + 245.46 na guia única
    assert puro_acai["fgts_rescisorio"] == 3914.74
    assert len(puro_acai["funcionarios_rescisorios"]) == 1
    assert "JOCINEIDE" in puro_acai["funcionarios_rescisorios"][0]["nome"]

    # Verifica SMART LABORATORIO (filiais 1 e 3)
    smart = next((e for e in empresas if "22070849000174" in e["documento_limpo"]), None)
    assert smart is not None
    assert smart["competencia"] == "09/2026"
    assert smart["fgts_mensal"] == 5400.03
    assert smart["consignado"] == 1690.06
    assert smart["total_fgts"] == 7090.09

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
