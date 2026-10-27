"""
Falhas já confirmadas na auditoria v2.1 que serão corrigidas na Fase 2.
Marcadas como xfail(strict=True): quando a correção entrar, o teste passa a
"passar inesperadamente" e o pytest acusa — aí basta remover o marcador.
"""

import logging

import pytest

from src.modules.fgts_digital.parser import formatar_nome_documento
from src.utils.logger import setup_logger


@pytest.mark.xfail(strict=True, reason="Fase 2: setup_logger ignora log_dir quando o logger já existe")
def test_log_em_arquivo_criado_mesmo_com_logger_ja_configurado(tmp_path):
    lg = setup_logger(log_dir=tmp_path)
    try:
        lg.info("teste de escrita em arquivo")
        assert list(tmp_path.glob("execucao_*.log")), "nenhum arquivo de log criado"
    finally:
        for h in list(lg.handlers):
            if isinstance(h, logging.FileHandler) and str(tmp_path) in h.baseFilename:
                lg.removeHandler(h)
                h.close()


@pytest.mark.xfail(strict=True, reason="Fase 2: tag 'comp' substitui trechos dentro de outras palavras")
def test_nomenclatura_nao_altera_palavras_que_contem_tags():
    ctx = {"competencia": "09/2026", "cnpj": "12345678000190", "razao_social": "Alfa"}
    assert formatar_nome_documento("Comprovante - {competencia}", ctx) == "Comprovante - 09-2026.pdf"
