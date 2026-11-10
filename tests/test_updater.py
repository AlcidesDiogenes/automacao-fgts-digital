"""
Testes unitários do módulo de atualização OTA (Over-The-Air) via GitHub Releases.
Valida parsing de semver, detecção de novas versões, telemetria de download e flags do instalador.
"""

import io
import json
import urllib.error
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from src.core.updater import _parse_version, versao_maior, UpdaterManager


def test_parse_version():
    assert _parse_version("1.0.0") == (1, 0, 0)
    assert _parse_version("v1.0.1") == (1, 0, 1)
    assert _parse_version("v2.10.3") == (2, 10, 3)
    assert _parse_version("invalido") == (0, 0, 0)


def test_versao_maior():
    assert versao_maior("1.0.1", "1.0.0") is True
    assert versao_maior("v1.1.0", "1.0.9") is True
    assert versao_maior("2.0.0", "1.9.9") is True
    assert versao_maior("1.0.0", "1.0.0") is False
    assert versao_maior("0.9.9", "1.0.0") is False


def test_verificar_atualizacao_detecta_nova_versao(monkeypatch):
    mock_payload = {
        "tag_name": "v1.0.2",
        "name": "Versão 1.0.2 - Correções",
        "body": "Novidades da versão 1.0.2",
        "assets": [
            {
                "name": "FGTS_Digital_Instalador_v1.0.2.exe",
                "size": 18000000,
                "browser_download_url": "https://github.com/mock/download.exe"
            }
        ]
    }

    class MockResponse:
        status = 200
        def read(self):
            return json.dumps(mock_payload).encode("utf-8")
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=10: MockResponse())

    updater = UpdaterManager(versao_atual="1.0.1")
    info = updater.verificar_atualizacao()

    assert info is not None
    assert info["tem_atualizacao"] is True
    assert info["versao_remota"] == "1.0.2"
    assert info["nome_arquivo"] == "FGTS_Digital_Instalador_v1.0.2.exe"
    assert info["download_url"] == "https://github.com/mock/download.exe"


def test_verificar_atualizacao_quando_versao_atual_ja_e_recente(monkeypatch):
    mock_payload = {
        "tag_name": "v1.0.1",
        "name": "Versão 1.0.1",
        "assets": [{"name": "instalador.exe", "browser_download_url": "url"}]
    }

    class MockResponse:
        status = 200
        def read(self):
            return json.dumps(mock_payload).encode("utf-8")
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=10: MockResponse())

    updater = UpdaterManager(versao_atual="1.0.1")
    info = updater.verificar_atualizacao()
    assert info is None


def test_verificar_atualizacao_trata_erro_404(monkeypatch):
    def mock_urlopen(req, timeout=10):
        raise urllib.error.HTTPError("url", 404, "Not Found", {}, None)

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

    updater = UpdaterManager(versao_atual="1.0.1")
    assert updater.verificar_atualizacao() is None


def test_baixar_instalador_com_progresso(monkeypatch, tmp_path):
    conteudo_falso = b"EXECUTAVEL_FALSO_DE_TESTE" * 1000

    class MockDownloadResponse:
        def __init__(self):
            self.headers = {"Content-Length": str(len(conteudo_falso))}
            self.buffer = io.BytesIO(conteudo_falso)
        def read(self, chunk_size):
            return self.buffer.read(chunk_size)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr("urllib.request.urlopen", lambda req: MockDownloadResponse())

    progresso_registrado = []
    def callback(pct, baixados, total):
        progresso_registrado.append((pct, baixados, total))

    arquivo = UpdaterManager.baixar_instalador(
        "https://github.com/mock/download.exe",
        "teste_instalador.exe",
        callback_progresso=callback
    )

    assert arquivo.exists()
    assert arquivo.stat().st_size == len(conteudo_falso)
    assert len(progresso_registrado) > 0
    assert progresso_registrado[-1][0] == 100.0


def test_aplicar_atualizacao_dispara_inno_setup_silencioso(tmp_path, monkeypatch):
    exe_fake = tmp_path / "instalador_fake.exe"
    exe_fake.write_bytes(b"MZ")

    mock_popen = MagicMock()
    mock_exit = MagicMock()
    monkeypatch.setattr("subprocess.Popen", mock_popen)
    monkeypatch.setattr("sys.exit", mock_exit)

    UpdaterManager.aplicar_atualizacao_e_reiniciar(exe_fake, silencioso=True)

    mock_popen.assert_called_once()
    args_chamados = mock_popen.call_args[0][0]
    assert str(exe_fake) in args_chamados[0]
    assert "/SILENT" in args_chamados
    assert "/CLOSEAPPLICATIONS" in args_chamados
    assert "/RESTARTAPPLICATIONS" in args_chamados
    mock_exit.assert_called_once_with(0)
