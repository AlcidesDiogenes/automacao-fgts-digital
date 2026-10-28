"""
Fixtures compartilhadas: geração de PDFs sintéticos e um "portal FGTS Digital falso"
servido pelo Playwright via interceptação de rotas (nenhuma requisição sai para a rede).
"""

from pathlib import Path
from typing import Callable, Dict, Optional

import pytest
from reportlab.pdfgen import canvas


def gerar_pdf(destino: Path, linhas) -> Path:
    """Gera um PDF simples com uma linha de texto por item."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(destino))
    y = 800
    for linha in linhas:
        c.drawString(40, y, linha)
        y -= 18
    c.save()
    return destino


def gerar_pdf_dominio(destino: Path, paginas) -> Path:
    """
    Gera um PDF que imita o layout do relatório "PAGAMENTO DE ENCARGOS" do Sistema Domínio
    (estrutura copiada do relatório real, com TODOS os dados fictícios — LGPD).
    Cada página é um dict: doc ("11.444.777/0001-61" ou CPF), tipo_doc ("CNPJ"/"CPF"),
    razao, competencia ("09/2026") e linhas (corpo do relatório, uma string por linha).
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(destino))
    for pag in paginas:
        comp = pag.get("competencia", "09/2026")
        cabecalho = [
            pag["doc"],
            f"{comp} a {comp}",
            "Empresa:",
            f"{pag.get('tipo_doc', 'CNPJ')}:",
            "Competência:",
            pag["razao"],
            "PAGAMENTO DE ENCARGOS",
            "10:00:00",
            "01/10/2026",
            "1/1Página:",
            "Emissão:",
            "Horas:",
        ]
        y = 800
        for linha in cabecalho + list(pag["linhas"]) + ["ESCRITORIO CONTABIL FICTICIO S/S"]:
            c.drawString(40, y, linha)
            y -= 16
        c.showPage()
    c.save()
    return destino


@pytest.fixture
def pdf_factory(tmp_path):
    def _criar(nome: str, linhas) -> Path:
        return gerar_pdf(tmp_path / "pdfs" / nome, linhas)
    return _criar


@pytest.fixture(scope="session")
def _browser():
    playwright_api = pytest.importorskip("playwright.sync_api")
    pw = playwright_api.sync_playwright().start()
    try:
        browser = pw.chromium.launch(headless=True)
    except Exception as e:
        pw.stop()
        pytest.skip(f"Chromium do Playwright indisponível: {e}")
    yield browser
    browser.close()
    pw.stop()


class PortalFalso:
    """
    Responde às URLs do FGTS Digital com HTML controlado pelo teste.
    `paginas` mapeia um trecho da URL -> HTML; `arquivos` mapeia trecho -> bytes de PDF (download).
    Qualquer outra requisição é abortada.
    """

    def __init__(self, page):
        self.page = page
        self.paginas: Dict[str, str] = {}
        self.arquivos: Dict[str, bytes] = {}
        self.requisicoes = []
        page.context.route("**/*", self._responder)

    def _responder(self, route):
        url = route.request.url
        self.requisicoes.append(url)
        for trecho, conteudo in self.arquivos.items():
            if trecho in url:
                route.fulfill(
                    status=200,
                    headers={
                        "Content-Type": "application/pdf",
                        "Content-Disposition": 'attachment; filename="guia.pdf"',
                    },
                    body=conteudo,
                )
                return
        for trecho, html in self.paginas.items():
            if trecho in url:
                route.fulfill(status=200, content_type="text/html; charset=utf-8", body=html)
                return
        route.abort()

    def avaliar(self, js: str):
        return self.page.evaluate(js)


@pytest.fixture
def portal(_browser):
    context = _browser.new_context(accept_downloads=True)
    context.set_default_timeout(5000)
    page = context.new_page()
    yield PortalFalso(page)
    context.close()
