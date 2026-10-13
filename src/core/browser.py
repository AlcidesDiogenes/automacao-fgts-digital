"""
Módulo de inicialização e gerenciamento do navegador automatizado (Playwright).
Configura injeção do Certificado Digital A1 (.pfx) em conexões seguras SSL/TLS do Gov.br e FGTS Digital.
"""

import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Generator
from contextlib import contextmanager
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright
from playwright_stealth import Stealth

from src.utils.logger import logger


class BrowserManager:
    """Gerencia a criação e ciclo de vida do navegador configurado para o FGTS Digital."""

    def __init__(
        self,
        pfx_path: Optional[Path] = None,
        pfx_password: str = "",
        headless: bool = False,
        timeout_seconds: int = 60,
        downloads_path: Optional[Path] = None
    ):
        self.pfx_path = Path(pfx_path) if pfx_path and str(pfx_path).strip() else None
        self.pfx_password = pfx_password or ""
        self.headless = headless
        self.timeout = timeout_seconds * 1000  # Playwright usa milissegundos
        self.downloads_path = downloads_path

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._is_cdp: bool = False

    def iniciar(self) -> Page:
        """Inicializa o navegador com perfil persistente ou conecta a uma janela ativa na porta 9222."""
        self._playwright = sync_playwright().start()

        # 1. Tenta conectar a uma janela ativa do Google Chrome (porta 9222)
        try:
            logger.info("Verificando se há janela do Google Chrome ativa (porta 9222)...")
            self._browser = self._playwright.chromium.connect_over_cdp("http://localhost:9222", timeout=2000)
            if self._browser.contexts:
                self._is_cdp = True
                self._context = self._browser.contexts[0]
                for p in self._context.pages:
                    if "fgtsdigital" in p.url or "gov.br" in p.url:
                        logger.info(f"Conectado com sucesso à janela aberta do FGTS Digital: {p.url}")
                        return p
                page = self._context.pages[0] if self._context.pages else self._context.new_page()
                logger.info("Conectado à janela ativa do Chrome via CDP.")
                return page
        except Exception:
            pass

        # 2. Se nenhuma janela estiver ativa, inicia o Google Chrome nativo automaticamente
        chrome_exe = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
        if not chrome_exe.exists():
            chrome_exe = Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe")

        if chrome_exe.exists():
            logger.info("Iniciando Google Chrome automaticamente na porta 9222...")
            abrir_chrome_nativo_para_login()
            import time
            for _ in range(12):
                time.sleep(1.0)
                try:
                    self._browser = self._playwright.chromium.connect_over_cdp("http://localhost:9222", timeout=2000)
                    if self._browser.contexts:
                        self._is_cdp = True
                        self._context = self._browser.contexts[0]
                        for p in self._context.pages:
                            if "fgtsdigital" in p.url or "gov.br" in p.url:
                                logger.info(f"Conectado ao Chrome recém-aberto: {p.url}")
                                return p
                        page = self._context.pages[0] if self._context.pages else self._context.new_page()
                        logger.info("Conectado ao Chrome aberto via CDP.")
                        return page
                except Exception:
                    continue

        logger.info(f"Iniciando navegador persistente padrão (Headless: {self.headless})...")
        self._is_cdp = False

        # Configura certificados de cliente para todos os domínios e subdomínios do governo
        client_certs = []
        cert_cn = ""
        if self.pfx_path and self.pfx_path.exists():
            resolved_pfx = str(self.pfx_path.resolve())
            origens_gov = [
                "https://sso.acesso.gov.br",
                "https://certificado.sso.acesso.gov.br",
                "https://certificados.acesso.gov.br",
                "https://acesso.gov.br",
                "https://contas.acesso.gov.br",
                "https://confiabilidade.acesso.gov.br",
                "https://fgtsdigital.sistema.gov.br"
            ]
            for origem in origens_gov:
                client_certs.append({
                    "origin": origem,
                    "pfxPath": resolved_pfx,
                    "passphrase": self.pfx_password,
                })
            logger.info("Certificado Digital A1 (.pfx) configurado para origens mTLS do Gov.br e FGTS Digital.")

            # Identifica o CN exato do titular para auto-seleção instantânea sem popup modal do Windows
            try:
                from src.auth.cert_manager import CertManager
                cm = CertManager(self.pfx_path, self.pfx_password)
                info = cm.inspecionar()
                if info.get("valido") and info.get("titular"):
                    cert_cn = info["titular"]
                    logger.info(f"Auto-seleção mTLS configurada para o titular: {cert_cn}")
            except Exception:
                pass
        else:
            logger.info("Utilizando Repositório Nativo de Certificados do Windows.")

        # Diretório persistente de perfil para manter cookies e tokens de segurança do Gov.br / F5 ASM
        user_data_dir = Path("data/browser_profile").resolve()
        user_data_dir.mkdir(parents=True, exist_ok=True)

        filter_rule = {"SUBJECT": {"CN": cert_cn}} if cert_cn else {}

        auto_select_rules = json.dumps([
            {"pattern": "https://[*.]acesso.gov.br", "filter": filter_rule},
            {"pattern": "https://[*.]sistema.gov.br", "filter": filter_rule}
        ])

        launch_args = [
            "--start-maximized",
            "--test-type",
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
            f"--auto-select-certificate-for-urls={auto_select_rules}"
        ]

        context_kwargs: Dict[str, Any] = {
            "user_data_dir": str(user_data_dir),
            "headless": self.headless,
            "ignore_default_args": ["--enable-automation"],
            "args": launch_args,
            "locale": "pt-BR",
            "timezone_id": "America/Sao_Paulo",
            "accept_downloads": True,
            "viewport": None,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        }

        chrome_exe = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
        if chrome_exe.exists():
            context_kwargs["channel"] = "chrome"
            logger.info("Utilizando perfil persistente do Google Chrome oficial com autenticação mTLS nativa do Windows.")
        else:
            # Fallback para Chromium interno caso não haja Google Chrome
            context_kwargs["client_certificates"] = client_certs

        self._context = self._playwright.chromium.launch_persistent_context(**context_kwargs)
        self._context.set_default_timeout(self.timeout)

        # Mascara a propriedade navigator.webdriver para mitigar disparos do WAF do Gov.br
        self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        # Obtém a página ativa do contexto persistente ou cria uma nova
        page = self._context.pages[0] if self._context.pages else self._context.new_page()

        # Aplica conjunto completo de evasões de detecção (plugins, WebGL, hairline, iframes)
        try:
            stealth = Stealth(navigator_languages_override=("pt-BR", "pt"))
            stealth.apply_stealth_sync(page)
            logger.info("Proteções anti-detecção (Stealth) aplicadas à sessão persistente.")
        except Exception as e:
            logger.warning(f"Não foi possível aplicar módulo stealth completo: {e}")

        return page

    def fechar(self):
        """Encerra a sessão do navegador e limpa os recursos."""
        try:
            if self._is_cdp:
                if self._playwright:
                    self._playwright.stop()
                logger.info("Desconectado da sessão CDP do Google Chrome (janela mantida aberta para uso contínuo).")
                return

            if self._context:
                self._context.close()
            if self._playwright:
                self._playwright.stop()
            logger.info("Sessão do navegador finalizada.")
        except Exception as e:
            logger.error(f"Erro ao fechar navegador: {e}")


@contextmanager
def sessao_navegador(
    pfx_path: Path,
    pfx_password: str,
    headless: bool = False,
    timeout_seconds: int = 60
) -> Generator[Page, None, None]:
    """Context manager para gerenciar o ciclo de vida do navegador automaticamente."""
    manager = BrowserManager(
        pfx_path=pfx_path,
        pfx_password=pfx_password,
        headless=headless,
        timeout_seconds=timeout_seconds
    )
    page = manager.iniciar()
    try:
        yield page
    finally:
        manager.fechar()


def abrir_chrome_nativo_para_login(url: str = "https://fgtsdigital.sistema.gov.br/portal") -> subprocess.Popen:
    """
    Abre o Google Chrome nativo do sistema operacional sem nenhum canal de automação
    para permitir autenticação humana limpa e instantânea no Gov.br.
    Os cookies de sessão e a autenticação são persistidos em 'data/browser_profile'.
    """
    chrome_exe = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
    if not chrome_exe.exists():
        chrome_exe = Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe")

    user_data_dir = Path("data/browser_profile").resolve()
    user_data_dir.mkdir(parents=True, exist_ok=True)

    args = [
        str(chrome_exe),
        "--remote-debugging-port=9222",
        f"--user-data-dir={user_data_dir}",
        "--start-maximized",
        "--no-first-run",
        "--no-default-browser-check",
        '--auto-select-certificate-for-urls=[{"pattern":"https://[*.]acesso.gov.br","filter":{}},{"pattern":"https://[*.]sistema.gov.br","filter":{}}]',
        url
    ]
    logger.info("Abrindo Google Chrome nativo na porta 9222 para login e automação...")
    return subprocess.Popen(args)
