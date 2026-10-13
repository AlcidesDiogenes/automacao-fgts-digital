"""
Testes unitários para o gerenciador de Certificado Digital A1.
"""

from pathlib import Path
from datetime import datetime, timedelta, timezone
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives.serialization.pkcs12 import serialize_key_and_certificates

from src.auth.cert_manager import CertManager


def criar_pfx_temporario(caminho: Path, senha: str, dias_validade: int = 365) -> Path:
    """Gera um arquivo .pfx de teste autoassinado."""
    chave_privada = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    nome = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "CONTADOR TESTE:12345678900"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "ESCRITORIO TESTE LTDA"),
    ])

    agora = datetime.now(timezone.utc)
    certificado = (
        x509.CertificateBuilder()
        .subject_name(nome)
        .issuer_name(nome)
        .public_key(chave_privada.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(agora - timedelta(days=1))
        .not_valid_after(agora + timedelta(days=dias_validade))
        .sign(chave_privada, hashes.SHA256())
    )

    pfx_bytes = serialize_key_and_certificates(
        name=b"certificado_teste",
        key=chave_privada,
        cert=certificado,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(senha.encode())
    )

    with open(caminho, "wb") as f:
        f.write(pfx_bytes)

    return caminho


def test_cert_manager_valido(tmp_path):
    pfx_file = tmp_path / "cert_valido.pfx"
    senha = "senha_teste_123"
    criar_pfx_temporario(pfx_file, senha, dias_validade=90)

    mgr = CertManager(str(pfx_file), senha)
    info = mgr.inspecionar()

    assert info["valido"] is True
    assert "CONTADOR TESTE" in info["titular"]
    assert info["expirado"] is False
    assert info["dias_restantes"] > 0
    assert info["tem_chave_privada"] is True


def test_cert_manager_senha_errada(tmp_path):
    pfx_file = tmp_path / "cert_valido.pfx"
    senha_correta = "senha_correta"
    criar_pfx_temporario(pfx_file, senha_correta)

    mgr = CertManager(str(pfx_file), "senha_incorreta")
    info = mgr.inspecionar()

    assert info["valido"] is False
    assert "Senha" in info["erro"]


def test_cert_manager_arquivo_inexistente():
    mgr = CertManager("arquivo_inexistente.pfx", "qualquer")
    info = mgr.inspecionar()

    assert info["valido"] is False
    assert "não encontrado" in info["erro"]
