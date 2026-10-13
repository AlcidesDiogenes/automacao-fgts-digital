"""
Módulo de tratamento e formatação de dados para o FGTS Digital.
Inclui sanitização de CNPJ, cálculos de competência e formatação de valores.
"""

import re
from datetime import datetime
from typing import Tuple, Optional


def limpar_cnpj(cnpj: str) -> str:
    """Remove pontuação e caracteres não numéricos do CNPJ."""
    if not cnpj:
        return ""
    numeros = re.sub(r"\D", "", str(cnpj)).strip()
    # Se já tiver entre 11 e 14 dígitos, completa com zeros à esquerda
    if 11 <= len(numeros) <= 14:
        return numeros.zfill(14)
    return numeros


def formatar_cnpj(cnpj: str) -> str:
    """Formata CNPJ limpo para o padrão XX.XXX.XXX/XXXX-XX."""
    num = limpar_cnpj(cnpj)
    if len(num) != 14:
        return num
    return f"{num[:2]}.{num[2:5]}.{num[5:8]}/{num[8:12]}-{num[12:]}"


def validar_cnpj(cnpj: str) -> bool:
    """Validação básica de formato de CNPJ (14 dígitos numéricos não repetidos)."""
    if not cnpj or len(str(cnpj).strip()) < 11:
        return False
    num = limpar_cnpj(cnpj)
    if len(num) != 14:
        return False
    # Verifica se não são todos dígitos repetidos
    if len(set(num)) == 1:
        return False
    return True


def calcular_competencia(tipo: str = "anterior", data_referencia: Optional[datetime] = None) -> str:
    """
    Calcula a competência no formato MM/AAAA.
    - 'anterior': Mês anterior ao de referência (padrão de fechamento da folha)
    - 'atual': Mês corrente
    - Customizado: Se for passado no formato MM/AAAA ou MM-AAAA, padroniza.
    """
    ref = data_referencia or datetime.now()

    tipo_limpo = tipo.strip().lower()

    if tipo_limpo == "atual":
        return ref.strftime("%m/%Y")

    if tipo_limpo == "anterior":
        # Se for janeiro, mês anterior é dezembro do ano passado
        if ref.month == 1:
            mes = 12
            ano = ref.year - 1
        else:
            mes = ref.month - 1
            ano = ref.year
        return f"{mes:02d}/{ano}"

    # Se for uma string com formato personalizado (ex: 08/2026 ou 08-2026)
    match = re.match(r"^(\d{1,2})[/-](\d{4})$", tipo_limpo)
    if match:
        mes_val = int(match.group(1))
        ano_val = int(match.group(2))
        if 1 <= mes_val <= 12 and 2000 <= ano_val <= 2100:
            return f"{mes_val:02d}/{ano_val}"

    # Fallback para o mês anterior caso formato seja inválido
    return calcular_competencia("anterior", ref)


def sanitizar_nome_arquivo(nome: str) -> str:
    """Remove caracteres inválidos para nomes de arquivos no Windows."""
    return re.sub(r'[\\/*?:"<>|]', "", nome).strip()


def converter_valor_br(valor_str: str) -> float:
    """Converte string monetária brasileira ('R$ 1.250,45' ou '1.250,45') para float."""
    if not valor_str:
        return 0.0
    limpo = re.sub(r"[^\d,\.]", "", str(valor_str))
    # Remove pontos de milhar e substitui vírgula por ponto
    limpo = limpo.replace(".", "").replace(",", ".")
    try:
        return float(limpo)
    except ValueError:
        return 0.0


def formatar_nome_documento(template: str, contexto: dict) -> str:
    """
    Formata o nome de um documento com base em um padrão customizável.
    Suporta tags (com ou sem chaves, maiúsculas ou minúsculas):
      - Competencia / {competencia} -> ex: 09-2026
      - CNPJ / {cnpj}               -> ex: 22070849000174
      - Empresa / {empresa} / Razao -> ex: SMART LABORATORIO DE SOLUCOES OPTICAS
    Garante terminação em .pdf e sanitiza contra caracteres proibidos pelo Windows.
    """
    comp = str(contexto.get("competencia", "")).replace("/", "-").strip()
    cnpj = limpar_cnpj(str(contexto.get("cnpj", "")))
    razao = sanitizar_nome_arquivo(str(contexto.get("razao_social", "")))[:35].strip()

    resultado = template

    # Substituição flexível de variáveis
    resultado = re.sub(r"\{?compet[êe]ncia\}?", comp, resultado, flags=re.IGNORECASE)
    resultado = re.sub(r"\{?comp\}?", comp, resultado, flags=re.IGNORECASE)
    resultado = re.sub(r"\{?cnpj\}?", cnpj, resultado, flags=re.IGNORECASE)
    resultado = re.sub(r"\{?empresa\}?", razao, resultado, flags=re.IGNORECASE)
    resultado = re.sub(r"\{?raz[aã]o\}?", razao, resultado, flags=re.IGNORECASE)

    # Limpeza de múltiplos espaços
    resultado = re.sub(r"\s+", " ", resultado).strip(" -_")

    # Garante extensão .pdf
    if not resultado.lower().endswith(".pdf"):
        resultado += ".pdf"

    return sanitizar_nome_arquivo(resultado)

