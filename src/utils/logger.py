"""
Módulo de logs centralizados.
Suporta escrita em arquivo de log, console com formatação e callbacks para atualizar a interface gráfica.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Callable, List, Optional

# Lista de ouvintes (callbacks) para atualizar a interface em tempo real
_log_listeners: List[Callable[[str, str], None]] = []


class CallbackHandler(logging.Handler):
    """Handler personalizado para despachar mensagens de log para a UI."""
    def emit(self, record):
        try:
            msg = self.format(record)
            level = record.levelname
            for listener in _log_listeners:
                try:
                    listener(msg, level)
                except Exception:
                    pass
        except Exception:
            self.handleError(record)


def add_log_listener(callback: Callable[[str, str], None]):
    """Registra uma função callback que recebe (mensagem, nivel) para a UI."""
    if callback not in _log_listeners:
        _log_listeners.append(callback)


def remove_log_listener(callback: Callable[[str, str], None]):
    """Remove uma função callback da lista."""
    if callback in _log_listeners:
        _log_listeners.remove(callback)


def setup_logger(name: str = "AutomacoesEncargos", log_dir: Optional[Path] = None) -> logging.Logger:
    """Configura e retorna o logger da aplicação."""
    logger = logging.getLogger(name)
    if logger.handlers:
        # Logger já criado na importação: só acrescenta o arquivo de log, se pedido
        if log_dir:
            _adicionar_handler_arquivo(logger, log_dir)
        return logger

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )

    # Handler de Console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler da UI
    ui_handler = CallbackHandler()
    ui_handler.setLevel(logging.INFO)
    ui_handler.setFormatter(formatter)
    logger.addHandler(ui_handler)

    # Handler de Arquivo se diretório for fornecido
    if log_dir:
        _adicionar_handler_arquivo(logger, log_dir)

    return logger


def _adicionar_handler_arquivo(logger: logging.Logger, log_dir: Path):
    """Adiciona o arquivo execucao_AAAA-MM-DD.log em log_dir (sem duplicar o mesmo arquivo)."""
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    file_path = (log_dir / f"execucao_{today}.log").resolve()
    for h in logger.handlers:
        if isinstance(h, logging.FileHandler) and Path(h.baseFilename).resolve() == file_path:
            return
    file_handler = logging.FileHandler(file_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s"
    ))
    logger.addHandler(file_handler)

# Logger padrão
logger = setup_logger()
