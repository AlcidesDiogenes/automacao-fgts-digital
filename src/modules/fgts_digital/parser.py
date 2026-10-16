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


def extrair_valor_fgts_de_texto(texto: str, fgts_esperado: float = 0.0) -> float:
    """
    Extrai o valor monetário da Guia Rápida MENSAL a partir do texto renderizado na tela.
    Suporta múltiplos blocos Mensais (ex: folha geral e folha complementar/avulsa),
    selecionando o bloco que corresponde ao valor esperado (fgts_esperado) ou o de maior valor.
    Prioriza a seção/bloco exclusivo da guia Mensal para evitar falsas divergências
    quando o cliente possui guias rescisórias não pagas (ou outros débitos)
    que são somadas no 'Total Devedor' no topo da página.
    """
    if not texto:
        return 0.0

    # 1. Localiza todos os inícios de blocos 'Mensal - Vencimento' na tela
    posicoes_mensal = [m.start() for m in re.finditer(r"Mensal\s*-\s*Vencimento", texto, re.IGNORECASE)]

    if posicoes_mensal:
        blocos_valores = []
        for i, pos_inicio in enumerate(posicoes_mensal):
            # O bloco vai até o próximo cabeçalho Mensal, ou até o fim
            pos_fim = posicoes_mensal[i + 1] if i + 1 < len(posicoes_mensal) else len(texto)
            bloco = texto[pos_inicio:pos_fim]

            # Corta se encontrar Rescisória ou Total Devedor dentro do trecho
            m_corte = re.search(r"\n\s*(?:Rescisória|Total Devedor)\s*-", bloco[25:], re.IGNORECASE)
            if m_corte:
                bloco = bloco[:m_corte.start() + 25]

            val = 0.0
            # 1a. Procura por 'Total Guia' dentro do bloco (ex: 'Total Guia 31.240,69')
            m_total_guia = re.search(r"Total\s*Guia[^\d]*(\d{1,3}(?:\.\d{3})*,\d{2})", bloco, re.IGNORECASE)
            if m_total_guia:
                val = converter_valor_br(m_total_guia.group(1))

            # 1b. Fallback: procura pela última ocorrência de 'Total' no bloco
            if val == 0.0:
                matches_totais = re.findall(r"Total[^\d]*(\d{1,3}(?:\.\d{3})*,\d{2})", bloco, re.IGNORECASE)
                if matches_totais:
                    val = converter_valor_br(matches_totais[-1])

            if val > 0:
                blocos_valores.append(val)

        if blocos_valores:
            if fgts_esperado > 0:
                # Escolhe o valor que tem menor diferença com o valor esperado
                blocos_valores.sort(key=lambda v: abs(v - fgts_esperado))
                return blocos_valores[0]
            else:
                # Se não houver valor esperado, pega o de maior valor (folha principal)
                return max(blocos_valores)

    # 2. Se não encontrou cabeçalho Mensal explícito, busca 'Total Guia' na página geral
    m_guia = re.search(r"Total\s*Guia[^\d]*(\d{1,3}(?:\.\d{3})*,\d{2})", texto, re.IGNORECASE)
    if m_guia:
        val = converter_valor_br(m_guia.group(1))
        if val > 0:
            return val

    # 3. Fallback: 'Total Devedor' na página geral (apenas se 'Total Guia' não existir)
    m_devedor = re.search(r"Total\s*Devedor[^\d]*(\d{1,3}(?:\.\d{3})*,\d{2})", texto, re.IGNORECASE)
    if m_devedor:
        val = converter_valor_br(m_devedor.group(1))
        if val > 0:
            return val

    # 4. Fallback genérico: busca qualquer padrão monetário associado a 'Total'
    matches = re.findall(r"Total[^\d]*(\d{1,3}(?:\.\d{3})*,\d{2})", texto, re.IGNORECASE)
    if matches:
        return converter_valor_br(matches[-1])

    return 0.0

