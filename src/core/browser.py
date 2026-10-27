"""
Módulo de inicialização e gerenciamento do navegador automatizado (Playwright).
Usa o certificado instalado no Windows: Google Chrome via CDP (porta 9222) ou perfil persistente.
Não injeta certificado por arquivo (.pfx): o client_certificates do Playwright quebra o captcha
do Gov.br (ERL0033800) — ver docs/decisoes/ADR-0004.
"""

import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Generator
from contextlib import contextmanager
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright
from playwright_stealth import Stealth

from src.utils.logger import logger
from config import settings


class BrowserManager:
    """Gerencia a criação e ciclo de vida do navegador configurado para o FGTS Digital."""

    def __init__(
        self,
        headless: bool = False,
        timeout_seconds: int = 60,
        downloads_path: Optional[Path] = None
    ):
        self.headless = headless
        self.timeout = timeout_seconds * 1000  # Playwright usa milissegundos
        self.downloads_path = downloads_path

        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._is_cdp: bool = False

    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

    def iniciar(self) -> Page:
        """
        Conecta/abre o Google Chrome na porta 9222 (CDP) e, se não houver Chrome, usa perfil
        persistente do Playwright com o repositório de certificados do Windows.
        """
        self._playwright = sync_playwright().start()

        page = self._conectar_chrome_cdp()
        if page is not None:
            return page
        return self._iniciar_persistente_windows()

    def _conectar_chrome_cdp(self) -> Optional[Page]:
        """Conecta a uma janela do Chrome na porta 9222 (abrindo o Chrome se necessário)."""
        # 1. Tenta conectar a uma janela ativa do Google Chrome (porta 9222)
        logger.info("Verificando se há janela do Google Chrome ativa (porta 9222)...")
        page = self._tentar_cdp("Conectado com sucesso à janela aberta do FGTS Digital")
        if page is not None:
            return page

        # 2. Se nenhuma janela estiver ativa, inicia o Google Chrome nativo automaticamente
        if _localizar_chrome() is None:
            return None

        logger.info("Iniciando Google Chrome automaticamente na porta 9222...")
        abrir_chrome_nativo_para_login()
        import time
        for _ in range(12):
            time.sleep(1.0)
            page = self._tentar_cdp("Conectado ao Chrome recém-aberto")
            if page is not None:
                return page
        return None

    def _tentar_cdp(self, mensagem: str) -> Optional[Page]:
        try:
            self._browser = self._playwright.chromium.connect_over_cdp("http://localhost:9222", timeout=2000)
        except Exception:
            return None
        if not self._browser.contexts:
            return None
        self._is_cdp = True
        self._context = self._browser.contexts[0]
        for p in self._context.pages:
            if "fgtsdigital" in p.url or "gov.br" in p.url:
                logger.info(f"{mensagem}: {p.url}")
                return p
        page = self._context.pages[0] if self._context.pages else self._context.new_page()
        logger.info("Conectado ao Chrome via CDP.")
        return page

    def _args_base(self) -> list:
        return [
            "--start-maximized",
            "--test-type",
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-infobars",
        ]

    def _iniciar_persistente_windows(self) -> Page:
        """Perfil persistente usando o repositório de certificados do Windows (reserva quando não há Chrome)."""
        logger.info(f"Iniciando navegador persistente padrão (Headless: {self.headless})...")
        logger.info("Utilizando Repositório Nativo de Certificados do Windows.")
        self._is_cdp = False

        # Diretório persistente de perfil para manter cookies e tokens de segurança do Gov.br / F5 ASM
        user_data_dir = settings.BROWSER_PROFILE_DIR
        user_data_dir.mkdir(parents=True, exist_ok=True)

        auto_select_rules = json.dumps([
            {"pattern": "https://[*.]acesso.gov.br", "filter": {}},
            {"pattern": "https://[*.]sistema.gov.br", "filter": {}}
        ])

        context_kwargs: Dict[str, Any] = {
            "user_data_dir": str(user_data_dir),
            "headless": self.headless,
            "ignore_default_args": ["--enable-automation"],
            "args": self._args_base() + [f"--auto-select-certificate-for-urls={auto_select_rules}"],
            "locale": "pt-BR",
            "timezone_id": "America/Sao_Paulo",
            "accept_downloads": True,
            "viewport": None,
            "user_agent": self.USER_AGENT
        }
        if _localizar_chrome() is not None:
            context_kwargs["channel"] = "chrome"
            logger.info("Utilizando perfil persistente do Google Chrome oficial com autenticação mTLS nativa do Windows.")

        self._context = self._playwright.chromium.launch_persistent_context(**context_kwargs)
        return self._preparar_contexto()

    def _preparar_contexto(self) -> Page:
        """Timeout padrão, mascaramento de automação e stealth no contexto persistente (ADR-0002)."""
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
    headless: bool = False,
    timeout_seconds: int = 60
) -> Generator[Page, None, None]:
    """Context manager para gerenciar o ciclo de vida do navegador automaticamente."""
    manager = BrowserManager(
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
    chrome_exe = _localizar_chrome()
    if chrome_exe is None:
        raise FileNotFoundError("Google Chrome não encontrado em Program Files.")

    user_data_dir = settings.BROWSER_PROFILE_DIR
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


def _localizar_chrome() -> Optional[Path]:
    """Caminho do Google Chrome instalado (64 ou 32 bits), ou None."""
    for caminho in (
        Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
        Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
    ):
        if caminho.exists():
            return caminho
    return None
