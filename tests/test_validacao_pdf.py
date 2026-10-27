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
