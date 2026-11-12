"""
Testes do validador de conteúdo dos PDFs baixados do FGTS Digital.
"""

from src.modules.fgts_digital.validacao_pdf import validar_pdf_documento

CNPJ = "12345678000190"


def test_aceita_pdf_com_cnpj_competencia_e_valor(pdf_factory):
    pdf = pdf_factory("ok.pdf", ["Empregador 12.345.678/0001-90", "Competencia 09/2026", "Total 12.345,67"])
    ok, motivo = validar_pdf_documento(pdf, CNPJ, "09/2026", valor_esperado=12345.67)
    assert ok, motivo


def test_aceita_cnpj_raiz_sem_pontuacao(pdf_factory):
    pdf = pdf_factory("raiz.pdf", ["CNPJ raiz 12345678", "Periodo 09-2026"])
    ok, motivo = validar_pdf_documento(pdf, CNPJ, "09/2026")
    assert ok, motivo


def test_rejeita_cnpj_de_outra_empresa(pdf_factory):
    pdf = pdf_factory("outro.pdf", ["Empregador 98.765.432/0001-10", "Competencia 09/2026"])
    ok, motivo = validar_pdf_documento(pdf, CNPJ, "09/2026")
    assert not ok
    assert "CNPJ" in motivo


def test_rejeita_cnpj_alvo_dentro_de_numero_maior(pdf_factory):
    pdf = pdf_factory("colado.pdf", ["Protocolo 9912345678000190", "Competencia 09/2026"])
    ok, _ = validar_pdf_documento(pdf, CNPJ, "09/2026")
    assert not ok


def test_rejeita_competencia_diferente(pdf_factory):
    pdf = pdf_factory("comp.pdf", ["Empregador 12.345.678/0001-90", "Competencia 08/2026"])
    ok, motivo = validar_pdf_documento(pdf, CNPJ, "09/2026")
    assert not ok
    assert "competência" in motivo.lower()


def test_aceita_competencia_por_extenso(pdf_factory):
    pdf = pdf_factory("extenso.pdf", ["Empregador 12.345.678/0001-90", "Competencia SETEMBRO/2026"])
    ok, motivo = validar_pdf_documento(pdf, CNPJ, "09/2026")
    assert ok, motivo


def test_rejeita_valor_diferente(pdf_factory):
    pdf = pdf_factory("valor.pdf", ["Empregador 12.345.678/0001-90", "Competencia 09/2026", "Total 23,45"])
    ok, motivo = validar_pdf_documento(pdf, CNPJ, "09/2026", valor_esperado=12345.67)
    assert not ok
    assert "valor" in motivo.lower()


def test_rejeita_arquivo_que_nao_e_pdf(tmp_path):
    arq = tmp_path / "falso.pdf"
    arq.write_bytes(b"<html>erro</html>")
    ok, _ = validar_pdf_documento(arq, CNPJ, "09/2026")
    assert not ok


def test_rejeita_pdf_sem_texto(tmp_path):
    from reportlab.pdfgen import canvas
    arq = tmp_path / "vazio.pdf"
    c = canvas.Canvas(str(arq))
    c.rect(10, 10, 100, 100)
    c.save()
    ok, motivo = validar_pdf_documento(arq, CNPJ, "09/2026")
    assert not ok
    assert "texto" in motivo.lower()


# Tipo de relatório (12/11/2026): nos PDFs reais, "Qtd. Trabalhadores Consignado" aparece em 9 de 9
# relatórios de consignado e em 0 de 13 detalhes FGTS (varredura de 11/11/2026).
BASE = ["Detalhe da Guia a Ser Emitida", "Empregador 12.345.678/0001-90", "Competencia 09/2026"]


def test_relatorio_consignado_exige_marcador_de_consignado(pdf_factory):
    pdf = pdf_factory("consig.pdf", BASE + ["Qtd. Trabalhadores Consignado: 2"])
    ok, motivo = validar_pdf_documento(pdf, CNPJ, "09/2026", tipo_relatorio="consignado")
    assert ok, motivo


def test_detalhe_fgts_nao_passa_como_relatorio_consignado(pdf_factory):
    pdf = pdf_factory("fgts.pdf", BASE + ["Total da Guia (FGTS + Consignado): 1.000,00"])
    ok, motivo = validar_pdf_documento(pdf, CNPJ, "09/2026", tipo_relatorio="consignado")
    assert not ok
    assert "consignado" in motivo.lower()


def test_relatorio_de_consignado_nao_passa_como_relatorio_fgts(pdf_factory):
    pdf = pdf_factory("trocado.pdf", BASE + ["Qtd. Trabalhadores Consignado: 2"])
    ok, motivo = validar_pdf_documento(pdf, CNPJ, "09/2026", tipo_relatorio="fgts")
    assert not ok


def test_detalhe_fgts_passa_como_relatorio_fgts(pdf_factory):
    pdf = pdf_factory("fgts_ok.pdf", BASE + ["Total da Guia (FGTS + Consignado): 1.000,00"])
    ok, motivo = validar_pdf_documento(pdf, CNPJ, "09/2026", tipo_relatorio="fgts")
    assert ok, motivo


# Relatório de Consignado real (12/11/2026): o extrator de texto cola as colunas da tabela e a
# competência vem grudada no CPF do trabalhador ("...-0910/2026"). Dados fictícios.
def test_competencia_colada_no_cpf_do_relatorio_consignado(pdf_factory):
    pdf = pdf_factory("colada.pdf", BASE + ["Qtd. Trabalhadores Consignado: 1",
                                            "139,2819/11/2026 657 123.456.789-0910/2026 2810676656 341"])
    ok, motivo = validar_pdf_documento(pdf, CNPJ, "10/2026", tipo_relatorio="consignado")
    assert ok, motivo


def test_competencia_colada_em_numero_qualquer_continua_rejeitada(pdf_factory):
    pdf = pdf_factory("numero.pdf", ["Empregador 12.345.678/0001-90", "Protocolo 98765410/2026"])
    ok, _ = validar_pdf_documento(pdf, CNPJ, "10/2026")
    assert not ok
