"""
Testes do logger central: o arquivo de log precisa ser criado mesmo quando o
logger já foi configurado na importação do módulo (bug corrigido em 27/10/2026).
"""

import logging

from src.utils.logger import setup_logger


def _remover_handlers_de(lg, pasta):
    for h in list(lg.handlers):
        if isinstance(h, logging.FileHandler) and str(pasta) in h.baseFilename:
            lg.removeHandler(h)
            h.close()


def test_log_em_arquivo_criado_mesmo_com_logger_ja_configurado(tmp_path):
    lg = setup_logger(log_dir=tmp_path)
    try:
        lg.info("teste de escrita em arquivo")
        arquivos = list(tmp_path.glob("execucao_*.log"))
        assert len(arquivos) == 1
        assert "teste de escrita em arquivo" in arquivos[0].read_text(encoding="utf-8")
    finally:
        _remover_handlers_de(lg, tmp_path)


def test_handler_de_arquivo_nao_duplica(tmp_path):
    lg = setup_logger(log_dir=tmp_path)
    setup_logger(log_dir=tmp_path)
    try:
        handlers = [h for h in lg.handlers if isinstance(h, logging.FileHandler) and str(tmp_path) in h.baseFilename]
        assert len(handlers) == 1
    finally:
        _remover_handlers_de(lg, tmp_path)
