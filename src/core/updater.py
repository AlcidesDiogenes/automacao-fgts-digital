"""
Módulo de Gerenciamento de Atualizações OTA (Over-The-Air) via GitHub Releases.
Verifica novas versões, efetua download assíncrono com telemetria de progresso
e aciona a instalação atômica via Inno Setup sem intervenção complexa do usuário.
"""

import sys
import os
import re
import tempfile
import urllib.request
import urllib.error
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from config.version import VERSION, GITHUB_RELEASES_API, GITHUB_REPO
from src.utils.logger import logger


def _parse_version(v_str: str) -> tuple:
    """Extrai tupla de inteiros de uma string de versão (ex.: 'v1.0.1' -> (1, 0, 1))."""
    numeros = re.findall(r"\d+", v_str)
    return tuple(map(int, numeros)) if numeros else (0, 0, 0)


def versao_maior(remota: str, local: str) -> bool:
    """Retorna True se a versão remota for estritamente superior à versão local."""
    return _parse_version(remota) > _parse_version(local)


class UpdaterManager:
    """Controlador de checagem, download e aplicação de atualizações do aplicativo."""

    def __init__(self, versao_atual: str = VERSION, api_url: str = GITHUB_RELEASES_API):
        self.versao_atual = versao_atual
        self.api_url = api_url

    def verificar_atualizacao(self, timeout_s: int = 10) -> Optional[Dict[str, Any]]:
        """
        Consulta a API do GitHub Releases para verificar se há uma versão mais recente disponível.
        Retorna dicionário com dados da release ou None se não houver atualização ou em caso de erro.
        """
        logger.info(f"Verificando atualizações OTA no repositório {GITHUB_REPO} (Versão atual: v{self.versao_atual})...")
        try:
            req = urllib.request.Request(
                self.api_url,
                headers={
                    "User-Agent": f"FGTS-Digital-Updater/{self.versao_atual}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                if resp.status != 200:
                    logger.warning(f"Resposta inesperada do GitHub Releases: Status {resp.status}")
                    return None
                data = json.loads(resp.read().decode("utf-8"))

            tag_name = data.get("tag_name", "").strip()
            versao_remota = tag_name.lstrip("vV")
            if not versao_remota:
                return None

            if not versao_maior(versao_remota, self.versao_atual):
                logger.info(f"O aplicativo já está na versão mais recente (v{self.versao_atual}).")
                return None

            # Localiza o arquivo .exe do instalador nos assets da release
            assets = data.get("assets", [])
            asset_instalador = None
            for asset in assets:
                nome = asset.get("name", "")
                if nome.lower().endswith(".exe") and ("instalador" in nome.lower() or "setup" in nome.lower() or "fgts" in nome.lower()):
                    asset_instalador = asset
                    break

            if not asset_instalador and assets:
                # Fallback: pega o primeiro .exe disponível
                for asset in assets:
                    if asset.get("name", "").lower().endswith(".exe"):
                        asset_instalador = asset
                        break

            if not asset_instalador:
                logger.warning(f"Nova versão v{versao_remota} detectada, mas nenhum executável de instalador foi anexado à release.")
                return None

            info_update = {
                "tem_atualizacao": True,
                "versao_remota": versao_remota,
                "tag_name": tag_name,
                "titulo": data.get("name") or f"Versão {tag_name}",
                "changelog": data.get("body", "Melhorias de desempenho e correções gerais."),
                "nome_arquivo": asset_instalador.get("name"),
                "tamanho_bytes": asset_instalador.get("size", 0),
                "download_url": asset_instalador.get("browser_download_url"),
                "publicado_em": data.get("published_at", "")
            }
            logger.info(f"Nova versão OTA encontrada: v{versao_remota} ({info_update['nome_arquivo']})")
            return info_update

        except urllib.error.HTTPError as e:
            if e.code == 404:
                logger.info("Nenhuma release publicada encontrada no repositório.")
            else:
                logger.warning(f"Falha HTTP ao consultar atualizações OTA: {e}")
            return None
        except Exception as e:
            logger.warning(f"Não foi possível verificar atualizações OTA: {e}")
            return None

    @staticmethod
    def baixar_instalador(
        download_url: str,
        nome_arquivo: str,
        callback_progresso: Optional[Callable[[float, int, int], None]] = None,
        cancelar_flag: Optional[Callable[[], bool]] = None
    ) -> Path:
        """
        Baixa o instalador (.exe) para o diretório temporário do Windows (%TEMP%).
        Reporta o progresso via callback_progresso(percentual, bytes_baixados, total_bytes).
        """
        temp_dir = Path(tempfile.gettempdir())
        destino = temp_dir / nome_arquivo

        logger.info(f"Baixando atualização de {download_url} para {destino}...")
        req = urllib.request.Request(
            download_url,
            headers={"User-Agent": "FGTS-Digital-Updater"}
        )

        with urllib.request.urlopen(req) as response:
            total_bytes = int(response.headers.get("Content-Length", 0))
            baixados = 0
            chunk_size = 64 * 1024  # 64 KB por leitura

            with open(destino, "wb") as f_out:
                while True:
                    if cancelar_flag and cancelar_flag():
                        f_out.close()
                        if destino.exists():
                            destino.unlink()
                        raise InterruptedError("Download cancelado pelo usuário.")

                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f_out.write(chunk)
                    baixados += len(chunk)

                    if callback_progresso and total_bytes > 0:
                        pct = (baixados / total_bytes) * 100.0
                        callback_progresso(pct, baixados, total_bytes)

        logger.info(f"Download do instalador concluído com sucesso: {destino} ({baixados} bytes).")
        return destino

    @staticmethod
    def aplicar_atualizacao_e_reiniciar(caminho_instalador: Path, silencioso: bool = True) -> None:
        """
        Executa o instalador do Inno Setup com flags de substituição limpa e encerra
        o aplicativo atual para liberar arquivos em uso.
        """
        caminho_exe = Path(caminho_instalador).resolve()
        if not caminho_exe.exists():
            raise FileNotFoundError(f"Instalador não encontrado em: {caminho_exe}")

        args = [str(caminho_exe)]
        if silencioso:
            # Flags oficiais do Inno Setup para update automático transparente
            args.extend([
                "/SILENT",
                "/SUPPRESSMSGBOXES",
                "/CLOSEAPPLICATIONS",
                "/RESTARTAPPLICATIONS"
            ])

        logger.info(f"Disparando instalação OTA via Inno Setup: {' '.join(args)}...")
        
        # Popen assíncrono para permitir que o app atual feche imediatamente
        subprocess.Popen(
            args,
            creationflags=subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0,
            close_fds=True
        )

        logger.info("Encerrando processo atual para permitir atualização atômica de arquivos...")
        sys.exit(0)
