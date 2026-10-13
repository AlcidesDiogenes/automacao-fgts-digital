"""
Módulo de Gerenciamento e Validação de Certificado Digital A1 (.pfx).
Lê os metadados do certificado, verifica senha e data de expiração.
"""

from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
from cryptography.x509.oid import NameOID
from src.utils.logger import logger


class CertManager:
    """Gerencia a validação e metadados de certificados digitais A1 em formato PKCS#12 (.pfx/.p12)."""

    def __init__(self, pfx_path: str, password: str):
        self.pfx_path = Path(pfx_path)
        self.password = password.encode("utf-8") if isinstance(password, str) else password
        self._cert_data: Optional[Dict[str, Any]] = None

    def validar_arquivo(self) -> bool:
        """Verifica se o arquivo do certificado existe e tem extensão válida."""
        if not self.pfx_path.exists():
            logger.error(f"Arquivo do certificado não encontrado: {self.pfx_path}")
            return False
        if self.pfx_path.suffix.lower() not in [".pfx", ".p12"]:
            logger.warning(f"Extensão incomum para certificado A1: {self.pfx_path.suffix}")
        return True

    def inspecionar(self) -> Dict[str, Any]:
        """
        Carrega o certificado com a senha fornecida e extrai metadados.
        Retorna dicionário com status, titular, emissor, validade e dias restantes.
        """
        if not self.validar_arquivo():
            return {
                "valido": False,
                "erro": "Arquivo não encontrado",
                "detalhes": str(self.pfx_path)
            }

        try:
            with open(self.pfx_path, "rb") as f:
                pfx_bytes = f.read()

            private_key, cert, additional_certs = load_key_and_certificates(
                pfx_bytes,
                self.password
            )

            if cert is None:
                return {
                    "valido": False,
                    "erro": "Nenhum certificado encontrado dentro do arquivo PKCS#12"
                }

            # Extrai o Common Name (CN) do titular
            subject_cns = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
            titular = subject_cns[0].value if subject_cns else "Titular não identificado"

            # Extrai o emissor
            issuer_cns = cert.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)
            emissor = issuer_cns[0].value if issuer_cns else "Emissor não identificado"

            # Validade
            # Na cryptography mais recente, not_valid_after_utc é preferível
            if hasattr(cert, "not_valid_after_utc"):
                val_ate = cert.not_valid_after_utc
                agora = datetime.now(timezone.utc)
            else:
                val_ate = cert.not_valid_after
                agora = datetime.now()

            dias_restantes = (val_ate - agora).days

            expirado = dias_restantes < 0
            valido = not expirado and private_key is not None

            self._cert_data = {
                "valido": valido,
                "titular": titular,
                "emissor": emissor,
                "validade": val_ate.strftime("%d/%m/%Y %H:%M:%S"),
                "dias_restantes": dias_restantes,
                "expirado": expirado,
                "tem_chave_privada": private_key is not None
            }

            if expirado:
                logger.error(f"Certificado EXPIRADO em {self._cert_data['validade']} ({abs(dias_restantes)} dias atrás)!")
            elif dias_restantes <= 30:
                logger.warning(f"Certificado próximo do vencimento: restam {dias_restantes} dias.")
            else:
                logger.info(f"Certificado A1 válido para '{titular}' (Válido até: {self._cert_data['validade']})")

            return self._cert_data

        except ValueError as e:
            msg = "Senha do certificado incorreta ou arquivo corrompido"
            logger.error(f"{msg}: {e}")
            return {
                "valido": False,
                "erro": msg
            }
        except Exception as e:
            logger.error(f"Erro ao ler certificado digital: {e}")
            return {
                "valido": False,
                "erro": f"Erro inesperado: {str(e)}"
            }

    @classmethod
    def validar_certificado(cls, pfx_path: Path, password: str) -> tuple[bool, str]:
        """
        Valida rapidamente o arquivo e a senha do certificado.
        Retorna (True, 'Titular (Válido até DD/MM/AAAA)') ou (False, 'Mensagem de erro').
        """
        instancia = cls(str(pfx_path), password)
        info = instancia.inspecionar()
        if info.get("valido"):
            titular = info.get("titular", "Titular identificado")
            validade = info.get("validade", "")
            dias = info.get("dias_restantes", 0)
            return True, f"{titular} (Válido até {validade} - {dias} dias)"
        else:
            return False, info.get("erro", "Certificado inválido")
