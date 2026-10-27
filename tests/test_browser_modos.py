"""
Testes da escolha do navegador conforme o modo de certificado (sem abrir navegador):
no modo PFX o arquivo precisa chegar ao Playwright via client_certificates e a janela
do Chrome via CDP (que só enxerga certificados do Windows) não pode ser usada.
"""

import datetime

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

import src.core.browser as browser_mod


def gerar_pfx(destino, senha=b"1234", dias=365):
    chave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nome = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "CONTADOR TESTE:12345678900")])
    agora = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(nome).issuer_name(nome).public_key(chave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(agora - datetime.timedelta(days=1))
        .not_valid_after(agora + datetime.timedelta(days=dias))
        .sign(chave, hashes.SHA256())
    )
    destino.write_bytes(pkcs12.serialize_key_and_certificates(
        b"teste", chave, cert, None, serialization.BestAvailableEncryption(senha)
    ))
    return destino


class PlaywrightFalso:
    def __init__(self):
        self.cdp_chamadas = 0
        self.persistente_kwargs = None
        self.chromium = self

    # API usada pelo BrowserManager
    def start(self):
        return self

    def stop(self):
        pass

    def connect_over_cdp(self, *a, **k):
        self.cdp_chamadas += 1
        raise RuntimeError("sem Chrome na porta 9222")

    def launch_persistent_context(self, **kwargs):
        self.persistente_kwargs = kwargs
        return ContextoFalso()


class ContextoFalso:
    pages = []

    def set_default_timeout(self, t):
        pass

    def add_init_script(self, s):
        pass

    def new_page(self):
        return object()

    def close(self):
        pass


@pytest.fixture
def pw(monkeypatch, tmp_path):
    falso = PlaywrightFalso()
    monkeypatch.setattr(browser_mod, "sync_playwright", lambda: falso)
    monkeypatch.setattr(browser_mod.settings, "DATA_DIR", tmp_path)
    monkeypatch.setattr(browser_mod.settings, "BROWSER_PROFILE_DIR", tmp_path / "browser_profile")
    monkeypatch.setattr(browser_mod, "Stealth", lambda **k: type("S", (), {"apply_stealth_sync": lambda self, p: None})())
    return falso


def test_modo_pfx_injeta_certificado_e_ignora_cdp(pw, tmp_path):
    pfx = gerar_pfx(tmp_path / "cert.pfx")
    bm = browser_mod.BrowserManager(pfx_path=pfx, pfx_password="1234")
    bm.iniciar()

    assert pw.cdp_chamadas == 0
    kw = pw.persistente_kwargs
    assert "channel" not in kw, "modo PFX deve usar o Chromium do Playwright"
    origens = {c["origin"] for c in kw["client_certificates"]}
    assert "https://certificado.sso.acesso.gov.br" in origens
    assert "https://fgtsdigital.sistema.gov.br" in origens
    assert all(c["pfxPath"] == str(pfx.resolve()) and c["passphrase"] == "1234" for c in kw["client_certificates"])
    assert kw["user_data_dir"].endswith("pfx_profile")


def test_modo_pfx_com_senha_errada_nao_abre_navegador(pw, tmp_path):
    pfx = gerar_pfx(tmp_path / "cert.pfx")
    bm = browser_mod.BrowserManager(pfx_path=pfx, pfx_password="errada")
    with pytest.raises(ValueError):
        bm.iniciar()
    assert pw.persistente_kwargs is None


def test_modo_pfx_arquivo_inexistente(pw, tmp_path):
    bm = browser_mod.BrowserManager(pfx_path=tmp_path / "nao_existe.pfx", pfx_password="1234")
    with pytest.raises(FileNotFoundError):
        bm.iniciar()


def test_modo_windows_sem_chrome_usa_perfil_persistente_sem_pfx(pw, monkeypatch):
    monkeypatch.setattr(browser_mod, "_localizar_chrome", lambda: None)
    bm = browser_mod.BrowserManager(pfx_path=None)
    bm.iniciar()
    assert pw.cdp_chamadas == 1
    assert "client_certificates" not in pw.persistente_kwargs
