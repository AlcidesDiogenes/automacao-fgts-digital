"""
Testes da abertura do navegador (sem abrir navegador de verdade).

Regressão protegida: o client_certificates do Playwright cria um proxy interno que
bloqueia os serviços de captcha e o Gov.br responde ERL0033800 ("Captcha inválido").
O robô usa SOMENTE o certificado instalado no Windows — ver docs/decisoes/ADR-0004.
"""

import inspect

import pytest

import src.core.browser as browser_mod


class PlaywrightFalso:
    def __init__(self, cdp_disponivel=False, abas=None):
        self.cdp_disponivel = cdp_disponivel
        self.abas = abas or []
        self.cdp_chamadas = 0
        self.persistente_kwargs = None
        self.chromium = self

    def start(self):
        return self

    def stop(self):
        pass

    def connect_over_cdp(self, *a, **k):
        self.cdp_chamadas += 1
        if not self.cdp_disponivel:
            raise RuntimeError("sem Chrome na porta 9222")
        return NavegadorCdpFalso(self.abas)

    def launch_persistent_context(self, **kwargs):
        self.persistente_kwargs = kwargs
        return ContextoFalso()


class AbaFalsa:
    def __init__(self, url):
        self.url = url


class ContextoFalso:
    def __init__(self, abas=None):
        self.pages = abas or []

    def set_default_timeout(self, t):
        pass

    def add_init_script(self, s):
        pass

    def new_page(self):
        return AbaFalsa("about:blank")

    def close(self):
        pass


class NavegadorCdpFalso:
    def __init__(self, abas):
        self.contexts = [ContextoFalso(abas)]


@pytest.fixture
def instalar(monkeypatch, tmp_path):
    def _instalar(falso, chrome_instalado=True):
        monkeypatch.setattr(browser_mod, "sync_playwright", lambda: falso)
        monkeypatch.setattr(browser_mod.settings, "BROWSER_PROFILE_DIR", tmp_path / "browser_profile")
        monkeypatch.setattr(browser_mod, "_localizar_chrome", lambda: (tmp_path / "chrome.exe") if chrome_instalado else None)
        monkeypatch.setattr(browser_mod, "abrir_chrome_nativo_para_login", lambda *a, **k: None)
        monkeypatch.setattr(browser_mod, "Stealth", lambda **k: type("S", (), {"apply_stealth_sync": lambda self, p: None})())
        monkeypatch.setattr("time.sleep", lambda s: None)
        return falso
    return _instalar


def test_browser_manager_nao_aceita_mais_certificado_em_arquivo():
    parametros = inspect.signature(browser_mod.BrowserManager.__init__).parameters
    assert "pfx_path" not in parametros and "pfx_password" not in parametros
    assert not hasattr(browser_mod.BrowserManager, "_iniciar_com_pfx")


def test_reaproveita_janela_do_chrome_ja_logada(instalar):
    pw = instalar(PlaywrightFalso(cdp_disponivel=True, abas=[AbaFalsa("https://www.google.com"), AbaFalsa("https://fgtsdigital.sistema.gov.br/portal/servicos")]))
    page = browser_mod.BrowserManager().iniciar()
    assert "fgtsdigital" in page.url
    assert pw.persistente_kwargs is None, "não deve abrir navegador do Playwright se o Chrome via CDP respondeu"


def test_chrome_instalado_mas_cdp_nao_responde_cai_no_perfil_persistente_do_chrome(instalar):
    pw = instalar(PlaywrightFalso(cdp_disponivel=False), chrome_instalado=True)
    browser_mod.BrowserManager().iniciar()
    assert pw.cdp_chamadas == 13  # 1 tentativa inicial + 12 após abrir o Chrome
    kw = pw.persistente_kwargs
    assert kw["channel"] == "chrome"
    assert "client_certificates" not in kw


def test_sem_chrome_usa_chromium_persistente_sem_certificado_em_arquivo(instalar):
    pw = instalar(PlaywrightFalso(cdp_disponivel=False), chrome_instalado=False)
    browser_mod.BrowserManager().iniciar()
    kw = pw.persistente_kwargs
    assert "channel" not in kw
    assert "client_certificates" not in kw
    assert any(a.startswith("--auto-select-certificate-for-urls=") for a in kw["args"])


def test_nenhum_codigo_do_navegador_usa_client_certificates():
    fonte = inspect.getsource(browser_mod)
    linhas_de_codigo = [l for l in fonte.splitlines() if not l.strip().startswith("#") and "client_certificates" in l]
    # Só a docstring do módulo pode citar o termo (explicando por que não é usado)
    assert all("quebra o captcha" in l for l in linhas_de_codigo), linhas_de_codigo
