"""
Validação do conteúdo dos PDFs baixados do FGTS Digital (guia GFD e relatórios analíticos).
Um arquivo só é aceito se o texto contiver o CNPJ (raiz) da empresa, a competência
e, quando informado, o valor esperado. Na dúvida, rejeita.
"""

import re
from pathlib import Path
from typing import Optional, Tuple

from pypdf import PdfReader

from src.modules.fgts_digital.parser import limpar_cnpj

MESES_EXTENSO = [
    "JANEIRO", "FEVEREIRO", "MARCO", "ABRIL", "MAIO", "JUNHO",
    "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO",
]


def extrair_texto_pdf(caminho: Path) -> str:
    """Retorna o texto de todas as páginas do PDF (string vazia se não houver texto)."""
    leitor = PdfReader(str(caminho))
    return "\n".join((pagina.extract_text() or "") for pagina in leitor.pages)


def _contem_cnpj_raiz(texto: str, cnpj: str) -> bool:
    """Procura os 8 dígitos da raiz do CNPJ, com ou sem pontuação, sem fazer parte de número maior."""
    raiz = limpar_cnpj(cnpj)[:8]
    if len(raiz) != 8:
        return False
    padrao = rf"(?<![\d.]){raiz[:2]}\.?{raiz[2:5]}\.?{raiz[5:]}"
    return re.search(padrao, texto) is not None


def _contem_competencia(texto: str, competencia: str) -> bool:
    """Aceita MM/AAAA, MM-AAAA, MM.AAAA ou mês por extenso seguido do ano."""
    m = re.match(r"^\s*(\d{1,2})[/-](\d{4})\s*$", competencia)
    if not m:
        return False
    mes, ano = int(m.group(1)), m.group(2)
    if re.search(rf"(?<!\d)0?{mes}\s*[/.-]\s*{ano}(?!\d)", texto):
        return True
    texto_sem_acento = texto.upper().replace("Ç", "C")
    return re.search(rf"{MESES_EXTENSO[mes - 1]}\s*(?:/|DE)?\s*{ano}", texto_sem_acento) is not None


def _contem_valor(texto: str, valor: float) -> bool:
    """Procura o valor no formato brasileiro, com ou sem separador de milhar."""
    inteiro, centavos = f"{valor:.2f}".split(".")
    com_milhar = f"{int(inteiro):,}".replace(",", ".")
    for forma in {f"{com_milhar},{centavos}", f"{inteiro},{centavos}"}:
        if re.search(rf"(?<![\d.,]){re.escape(forma)}(?!\d)", texto):
            return True
    return False


def validar_pdf_documento(
    caminho: Path,
    cnpj: str,
    competencia: str,
    valor_esperado: Optional[float] = None,
) -> Tuple[bool, str]:
    """
    Confere se o PDF pertence à empresa/competência esperadas.
    Retorna (True, "") se aprovado, ou (False, motivo) se reprovado.
    """
    caminho = Path(caminho)
    try:
        with open(caminho, "rb") as f:
            if not f.read(5).startswith(b"%PDF"):
                return False, "Arquivo baixado não é um PDF"
        texto = extrair_texto_pdf(caminho)
    except Exception as e:
        return False, f"Não foi possível ler o PDF: {e}"

    if not texto.strip():
        return False, "PDF sem texto extraível (não é possível conferir CNPJ/competência)"
    if not _contem_cnpj_raiz(texto, cnpj):
        return False, "CNPJ da empresa não encontrado no PDF"
    if not _contem_competencia(texto, competencia):
        return False, f"Competência {competencia} não encontrada no PDF"
    if valor_esperado and valor_esperado > 0 and not _contem_valor(texto, valor_esperado):
        return False, f"Valor R$ {valor_esperado:.2f} não encontrado no PDF"
    return True, ""
