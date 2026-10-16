"""
Robô de Automação do Portal FGTS Digital.
Executa autenticação com Gov.br via A1, alternância de perfil por procuração,
emissão de guias GFD (com PIX) e download de relatórios de débitos.
"""

import os
import shutil
import tempfile
import glob
from pathlib import Path
from datetime import datetime
import time
from typing import Dict, Any, List, Optional
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from src.modules.fgts_digital import selectors as sel
from src.modules.fgts_digital.parser import (
    limpar_cnpj,
    formatar_cnpj,
    sanitizar_nome_arquivo,
    converter_valor_br,
    formatar_nome_documento,
    extrair_valor_fgts_de_texto
)
from src.utils.logger import logger


class FGTSDigitalBot:
    """Robô que navega pelo portal FGTS Digital executando a rotina de emissão em lote."""

    def __init__(self, page: Page, output_base_dir: Path):
        self.page = page
        self.output_base_dir = Path(output_base_dir)

    def _clicar_primeiro_disponivel(self, seletores: List[str], timeout_ms: int = 5000) -> bool:
        """Tenta clicar no primeiro seletor que estiver visível na página."""
        for s in seletores:
            try:
                el = self.page.locator(s).first
                if el.is_visible(timeout=timeout_ms):
                    el.click()
                    return True
            except Exception:
                continue
        return False

    def _elemento_visivel(self, seletores: List[str], timeout_ms: int = 3000) -> bool:
        """Verifica se algum dos seletores fornecidos está visível na tela."""
        for s in seletores:
            try:
                if self.page.locator(s).first.is_visible(timeout=timeout_ms):
                    return True
            except Exception:
                continue
        return False

    def login(self) -> bool:
        """
        Navega para o portal do FGTS Digital e realiza login via Gov.br com Certificado Digital.
        Se já estiver conectado (ex: via CDP na janela ativa), reaproveita a sessão instantaneamente.
        """
        logger.info("Verificando sessão ativa no FGTS Digital...")
        try:
            # 1. Se já estiver no portal do FGTS Digital (ex: conexão CDP ou sessão persistente)
            if "fgtsdigital.sistema.gov.br" in self.page.url:
                self._clicar_primeiro_disponivel(sel.BTN_ACEITAR_COOKIES, timeout_ms=1000)
                if (
                    self._elemento_visivel(sel.MODAL_PERFIL_CONTAINER, timeout_ms=1000)
                    or self._elemento_visivel(sel.PERFIL_BTN_TROCAR, timeout_ms=1500)
                    or self._elemento_visivel(sel.CARD_GESTAO_GUIAS, timeout_ms=1500)
                ):
                    logger.info("Sessão autenticada ativa detectada no FGTS Digital!")
                    return True

            # 2. Navega até o portal caso não esteja
            self.page.goto(sel.URL_FGTS_PORTAL, wait_until="domcontentloaded")
            time.sleep(2.0)
            self._clicar_primeiro_disponivel(sel.BTN_ACEITAR_COOKIES, timeout_ms=1000)

            # Verifica se já está verdadeiramente logado
            if (
                self._elemento_visivel(sel.MODAL_PERFIL_CONTAINER, timeout_ms=2000)
                or self._elemento_visivel(sel.PERFIL_BTN_TROCAR, timeout_ms=2000)
                or self._elemento_visivel(sel.CARD_GESTAO_GUIAS, timeout_ms=2000)
            ):
                logger.info("Sessão ativa detectada no FGTS Digital.")
                return True

            # Localiza e clica no botão Entrar com gov.br
            logger.info("Localizando botão 'Entrar com gov.br'...")
            clicou_login = False
            for s_login in sel.LOGIN_BTN_GOV_BR:
                try:
                    btn = self.page.locator(s_login).first
                    if btn.is_visible(timeout=3000):
                        btn.click()
                        clicou_login = True
                        logger.info(f"Clicou em 'Entrar com gov.br' via: {s_login}")
                        break
                except Exception:
                    continue

            if not clicou_login:
                try:
                    btn_text = self.page.get_by_text("gov.br", exact=False).first
                    if btn_text.is_visible(timeout=4000):
                        btn_text.click()
                        clicou_login = True
                        logger.info("Clicou em 'Entrar com gov.br' via busca textual.")
                except Exception:
                    pass

            if not clicou_login:
                logger.error("Botão 'Entrar com gov.br' não foi localizado na página.")
                return False

            # Aguarda o redirecionamento e carregamento da tela de login do SSO Gov.br
            logger.info("Aguardando carregamento da tela de login do Gov.br...")
            try:
                self.page.wait_for_url("**/sso.acesso.gov.br/login**", timeout=25000)
            except Exception:
                logger.info("Verificando se já está na tela de login do Gov.br...")

            time.sleep(1.5)

            # Na página do SSO Gov.br, seleciona login com Certificado Digital
            logger.info("Localizando botão 'Seu certificado digital' no Gov.br...")
            self._elemento_visivel(sel.LOGIN_BTN_CERTIFICADO, timeout_ms=8000)
            clicou_cert = False
            for s_cert in sel.LOGIN_BTN_CERTIFICADO:
                try:
                    btn_c = self.page.locator(s_cert).first
                    if btn_c.is_visible(timeout=3000):
                        btn_c.click()
                        clicou_cert = True
                        logger.info(f"Clicou em certificado via: {s_cert}")
                        break
                except Exception:
                    continue

            if not clicou_cert:
                try:
                    btn_cert_txt = self.page.get_by_text("certificado digital", exact=False).first
                    if btn_cert_txt.is_visible(timeout=5000):
                        btn_cert_txt.click()
                        clicou_cert = True
                        logger.info("Clicou em certificado via busca textual.")
                except Exception as e:
                    logger.error(f"Não foi possível clicar em Certificado Digital no Gov.br: {e}")
                    return False

            # Monitora o retorno ao FGTS Digital ou telas intermediárias (ex: Captcha, Autorizar)
            logger.info("Autenticando mTLS do certificado e monitorando retorno ao FGTS Digital...")
            inicio_espera = time.time()
            tempo_limite = 90
            captcha_detectado = False
            retornou = False

            while time.time() - inicio_espera < tempo_limite:
                current_url = self.page.url

                # 1. Verifica se já retornou ao FGTS Digital
                if "fgtsdigital.sistema.gov.br" in current_url and "acessogov" not in current_url:
                    retornou = True
                    break

                # 2. Detecta desafio de segurança / Captcha do Gov.br
                tem_captcha = self._elemento_visivel(sel.CAPTCHA_DETECTORS, timeout_ms=500)
                if tem_captcha:
                    if not captcha_detectado:
                        captcha_detectado = True
                        tempo_limite = 240  # Concede até 4 minutos para intervenção humana no Captcha
                        logger.warning("[ATENÇÃO] Desafio de segurança (Captcha) detectado no Gov.br!")
                        logger.warning("Por favor, resolva o desafio na janela aberta do navegador...")
                    time.sleep(1.5)
                    continue

                # 3. Verifica se apareceu a tela de consentimento do Gov.br ("Autorizar")
                if not tem_captcha and self._elemento_visivel(sel.BTN_AUTORIZAR_GOV_BR, timeout_ms=800):
                    logger.info("Detectado botão 'Autorizar' no Gov.br. Clicando automaticamente...")
                    self._clicar_primeiro_disponivel(sel.BTN_AUTORIZAR_GOV_BR, timeout_ms=3000)
                    time.sleep(2.0)
                    continue

                time.sleep(1.0)

            if not retornou:
                pasta_log = Path("data/logs")
                pasta_log.mkdir(parents=True, exist_ok=True)
                foto_erro = pasta_log / "erro_login_timeout.png"
                self.page.screenshot(path=str(foto_erro))
                logger.error(f"Tempo esgotado aguardando retorno do Gov.br. URL atual: {self.page.url}")
                return False

            self.page.wait_for_load_state("networkidle")
            time.sleep(2.0)

            if (
                self._elemento_visivel(sel.MODAL_PERFIL_CONTAINER, timeout_ms=8000)
                or self._elemento_visivel(sel.PERFIL_BTN_TROCAR, timeout_ms=8000)
                or self._elemento_visivel(sel.CARD_GESTAO_GUIAS, timeout_ms=5000)
                or "fgtsdigital.sistema.gov.br" in self.page.url
            ):
                logger.info("Login realizado com sucesso no FGTS Digital!")
                return True
            else:
                logger.error(f"Retorno do Gov.br não autenticou no FGTS Digital. URL final: {self.page.url}")
                return False

        except Exception as e:
            logger.error(f"Erro durante autenticação no FGTS Digital: {e}")
            return False

    def trocar_perfil(self, cnpj: str) -> Dict[str, Any]:
        """
        Altera o perfil ativo para o CNPJ do cliente outorgante via Procuração Eletrônica.
        """
        cnpj_limpo = limpar_cnpj(cnpj)
        cnpj_fmt = formatar_cnpj(cnpj_limpo)
        logger.info(f"Alternando perfil para a empresa CNPJ: {cnpj_fmt}...")

        try:
            # 1. Se estiver em subpágina (ex: cobranca), retorna para a tela inicial de serviços
            if "servicos" not in self.page.url or "cobranca" in self.page.url:
                self.page.goto("https://fgtsdigital.sistema.gov.br/portal/servicos", wait_until="domcontentloaded")
                time.sleep(1.0)

            # 2. Fecha eventuais avisos de cookies
            self._clicar_primeiro_disponivel(sel.BTN_ACEITAR_COOKIES, timeout_ms=800)

            # 3. Verifica se o modal já está visível; se não, clica em 'Trocar Perfil'
            modal_aberto = self._elemento_visivel(sel.MODAL_PERFIL_CONTAINER, timeout_ms=1200)
            if not modal_aberto:
                logger.info("Abrindo modal de troca de perfil...")
                if not self._clicar_primeiro_disponivel(sel.PERFIL_BTN_TROCAR, timeout_ms=3000):
                    self._clicar_primeiro_disponivel(sel.PERFIL_MENU_USUARIO, timeout_ms=2000)
                    self._clicar_primeiro_disponivel(sel.PERFIL_BTN_TROCAR, timeout_ms=2000)
                time.sleep(1.0)

            # 4. Seleciona a opção 'Procurador' no dropdown de Perfil (se não estiver selecionada)
            val_perfil = self.page.locator("ng-select .ng-value-label").all_text_contents()
            if not any("Procurador" in str(v) for v in val_perfil):
                logger.info("Selecionando opção 'Procurador' no dropdown...")
                self._clicar_primeiro_disponivel(sel.PERFIL_DROPDOWN_CONTAINER, timeout_ms=2000)
                time.sleep(0.4)
                self._clicar_primeiro_disponivel(sel.PERFIL_OPCAO_PROCURADOR, timeout_ms=2500)
                time.sleep(0.5)

            # 5. Preenche o CNPJ outorgante
            input_preenchido = False
            for s in sel.PERFIL_INPUT_CNPJ_OUTORGANTE:
                try:
                    campo = self.page.locator(s).first
                    if campo.is_visible(timeout=2000):
                        campo.fill("")
                        campo.fill(cnpj_limpo)
                        input_preenchido = True
                        logger.info(f"CNPJ {cnpj_fmt} preenchido.")
                        break
                except Exception:
                    continue

            if not input_preenchido:
                msg = f"Campo de inserção do CNPJ outorgante não localizado para {cnpj_fmt}."
                logger.warning(msg)
                return {"sucesso": False, "motivo": msg}

            time.sleep(0.4)

            # 6. Clica em confirmar troca ('Selecionar' ou 'Definir')
            logger.info("Confirmando seleção de perfil...")
            self._clicar_primeiro_disponivel(sel.PERFIL_BTN_CONFIRMAR_TROCA, timeout_ms=3000)
            time.sleep(2.5)

            # 7. Verifica se houve erro de procuração ou bloqueio retornado no modal
            if self._elemento_visivel(sel.ALERTA_PROCURACAO_INVALIDA, timeout_ms=1500):
                msg = "Sem procuração ativa ou permissão no FGTS Digital"
                logger.warning(f"{cnpj_fmt}: {msg}")
                try:
                    self.page.locator("button:has-text('Cancelar')").first.click()
                except Exception:
                    pass
                return {"sucesso": False, "motivo": msg}

            mensagens_erro = self.page.locator(".modal-body .invalid-feedback, .modal-body br-alert-messages .message").all_text_contents()
            erros_relevantes = [m.strip() for m in mensagens_erro if m.strip() and "obrigatório" not in m.lower()]
            if erros_relevantes:
                msg = " | ".join(erros_relevantes)
                logger.warning(f"{cnpj_fmt}: Erro no portal: {msg}")
                try:
                    self.page.locator("button:has-text('Cancelar')").first.click()
                except Exception:
                    pass
                return {"sucesso": False, "motivo": msg}

            logger.info(f"Perfil alterado com sucesso para {cnpj_fmt}.")
            return {"sucesso": True}

        except Exception as e:
            logger.error(f"Erro ao trocar perfil para {cnpj_fmt}: {e}")
            return {"sucesso": False, "motivo": str(e)}

    def _obter_container_mensal(self, fgts_esperado: float = 0.0) -> Optional[Any]:
        """
        Localiza o card/container específico da guia Mensal na tela de Guia Rápida.
        Se houver múltiplos cards mensais (ex: guia residual e guia principal com consignado),
        avalia cada card e seleciona aquele cujo valor mais se aproxima de `fgts_esperado`
        (ou o de maior valor caso fgts_esperado seja 0).
        Evita interferência de guias Rescisórias não pagas que aparecem no mesmo portal.
        """
        import re
        try:
            loc_headers = self.page.locator("h1, h2, h3, h4, h5, div, span, strong").filter(
                has_text=re.compile(r"Mensal\s*-\s*Vencimento", re.IGNORECASE)
            ).all()

            candidatos = []
            seen_signatures = set()

            for header in loc_headers:
                if not header.is_visible():
                    continue

                for ancestor_xpath in [
                    "xpath=ancestor::*[contains(@class, 'card') or contains(@class, 'br-card') or contains(@class, 'cardListItem') or self::fieldset][1]",
                    "xpath=ancestor::div[contains(@class, 'border') or contains(@style, 'border') or contains(@class, 'box')][1]",
                    "xpath=ancestor::div[button[contains(., 'Emitir')] and (.//*[contains(., 'FGTS')] or .//*[contains(., 'Total')])][1]",
                    "xpath=ancestor::div[2]",
                    "xpath=ancestor::div[3]",
                    "xpath=ancestor::div[4]"
                ]:
                    try:
                        cand = header.locator(ancestor_xpath).first
                        if cand.count() > 0 and cand.is_visible():
                            txt = cand.inner_text()
                            txt_lower = txt.lower()
                            if "mensal" in txt_lower and "rescisória" not in txt_lower and "rescisoria" not in txt_lower:
                                sig = txt[:150]
                                if sig not in seen_signatures:
                                    seen_signatures.add(sig)
                                    val = extrair_valor_fgts_de_texto(txt, fgts_esperado=fgts_esperado)
                                    candidatos.append((cand, val, txt))
                                break
                    except Exception:
                        continue

            # Fallback caso ancestrais não tenham retornado candidatos
            if not candidatos:
                cards = self.page.locator("div.card, .br-card, fieldset, div").filter(
                    has_text=re.compile(r"Mensal\s*-\s*Vencimento", re.IGNORECASE)
                ).all()
                for c in cards:
                    if c.is_visible():
                        txt = c.inner_text()
                        txt_lower = txt.lower()
                        if "mensal" in txt_lower and "rescisória" not in txt_lower and "rescisoria" not in txt_lower:
                            sig = txt[:150]
                            if sig not in seen_signatures:
                                seen_signatures.add(sig)
                                val = extrair_valor_fgts_de_texto(txt, fgts_esperado=fgts_esperado)
                                candidatos.append((c, val, txt))

            if not candidatos:
                return None

            if len(candidatos) == 1:
                cand, val, _ = candidatos[0]
                logger.info(f"Container único da Guia Mensal identificado (Valor apurado: R$ {val:.2f}).")
                return cand

            # Mais de um container mensal identificado
            logger.info(f"Foram identificados {len(candidatos)} cards mensais na tela. Selecionando o mais adequado...")
            for idx, (_, val, _) in enumerate(candidatos, 1):
                logger.info(f"  -> Card {idx}: Valor apurado R$ {val:.2f}")

            if fgts_esperado > 0:
                candidatos.sort(key=lambda item: abs(item[1] - fgts_esperado))
                melhor_cand, melhor_val, _ = candidatos[0]
                logger.info(
                    f"Card selecionado por proximidade com valor esperado: R$ {melhor_val:.2f} (Esperado: R$ {fgts_esperado:.2f} | Dif: R$ {abs(melhor_val - fgts_esperado):.2f})."
                )
                return melhor_cand
            else:
                candidatos.sort(key=lambda item: item[1], reverse=True)
                melhor_cand, melhor_val, _ = candidatos[0]
                logger.info(f"Card selecionado pelo maior valor apurado: R$ {melhor_val:.2f}.")
                return melhor_cand

        except Exception as e:
            logger.debug(f"Aviso ao localizar container mensal: {e}")

        return None

    def _extrair_valor_tela_fgts(self, container_mensal: Optional[Any] = None, fgts_esperado: float = 0.0) -> float:
        """
        Extrai o valor numérico total a recolher da Guia Rápida MENSAL.
        Prioriza o container e bloco exclusivo da guia Mensal para evitar que guias rescisórias
        não pagas pelo cliente (ou outros débitos) somados no 'Total Devedor' causem falsas divergências.
        """
        import re

        # 1. Se temos o container isolado do card Mensal, avalia o texto exclusivo dele
        if container_mensal:
            try:
                txt_mensal = container_mensal.inner_text()
                val = extrair_valor_fgts_de_texto(txt_mensal, fgts_esperado=fgts_esperado)
                if val > 0:
                    logger.info(f"Valor extraído diretamente do card Mensal: R$ {val:.2f}")
                    return val
            except Exception as e:
                logger.warning(f"Erro ao extrair valor do container mensal: {e}")

        # 2. Avalia o texto da página inteira usando o parser especializado em Mensal
        try:
            texto_geral = self.page.inner_text("body")
            val = extrair_valor_fgts_de_texto(texto_geral, fgts_esperado=fgts_esperado)
            if val > 0:
                logger.info(f"Valor Mensal identificado via parser textual: R$ {val:.2f}")
                return val
        except Exception as e:
            logger.debug(f"Erro ao ler texto geral da página: {e}")

        # 3. Busca por seletores específicos mapeados
        for seletor in sel.CAMPOS_VALOR_TOTAL_TELA:
            try:
                elementos = self.page.locator(seletor).all()
                for el in elementos:
                    texto = el.inner_text().strip()
                    val = converter_valor_br(texto)
                    if val > 0:
                        return val
            except Exception:
                continue

        return 0.0

    def _selecionar_competencia_e_pesquisar(self, competencia: str) -> bool:
        """
        Na tela de Emissão de Guia Rápida, seleciona a competência no dropdown <ng-select>
        e clica no botão 'Pesquisar'.
        """
        logger.info(f"Configurando competência '{competencia}' e executando pesquisa...")
        try:
            # Aguarda o carregamento do formulário de filtros
            self.page.wait_for_selector("ng-select, button:has-text('Pesquisar')", timeout=10000)
            
            ng_select = self.page.locator("ng-select").first
            if not ng_select.is_visible(timeout=5000):
                logger.warning("Campo ng-select de competência não visível.")
                return False

            texto_atual = ng_select.inner_text().strip()
            logger.info(f"Competência atualmente exibida no campo: '{texto_atual}'")
            
            # Se a competência desejada não estiver selecionada, altera
            if competencia not in texto_atual:
                logger.info(f"Alterando competência para '{competencia}'...")
                
                # Clica no botão de limpar se estiver visível
                btn_clear = ng_select.locator(".ng-clear-wrapper, span.ng-clear")
                if btn_clear.count() > 0 and btn_clear.first.is_visible():
                    btn_clear.first.click()
                    time.sleep(0.3)

                # Abre o dropdown
                ng_select.click()
                time.sleep(0.4)

                # Preenche o input do ng-select
                input_text = ng_select.locator("input[type='text'], input[role='combobox']")
                if input_text.count() > 0:
                    input_text.first.fill(competencia)
                    time.sleep(0.5)

                # Clica na opção correspondente na lista suspensa
                opcao = self.page.locator(f".ng-dropdown-panel .ng-option:has-text('{competencia}')").first
                if opcao.is_visible(timeout=2000):
                    opcao.click()
                    logger.info(f"Opção '{competencia}' clicada no dropdown.")
                else:
                    self.page.keyboard.press("Enter")
                    logger.info(f"Pressionado Enter para selecionar '{competencia}'.")

                time.sleep(0.5)

            # Clica no botão Pesquisar
            logger.info("Clicando no botão 'Pesquisar'...")
            btn_pesquisar = self.page.locator("button.secondary:has-text('Pesquisar'), button:has-text('Pesquisar')").first
            if btn_pesquisar.is_visible(timeout=3000):
                btn_pesquisar.click()
            else:
                self._clicar_primeiro_disponivel(sel.GUIA_RAPIDA_BTN_PESQUISAR, timeout_ms=3000)

            # Aguarda a resposta da pesquisa (débitos carregados ou alerta sem débitos)
            time.sleep(1.5)
            try:
                self.page.wait_for_selector(
                    "button:has-text('Emitir guia'), div:has-text('Total Devedor'), div:has-text('COB0003'), div:has-text('Não há débitos'), .alerta-sem-debitos",
                    timeout=12000
                )
            except Exception:
                logger.warning("Tempo limite ao aguardar resultado da pesquisa de débitos.")

            return True

        except Exception as e:
            logger.error(f"Erro ao selecionar competência e pesquisar: {e}")
            return False

    def _baixar_relatorio_pdf(
        self,
        secao_nome: str,
        caminho_destino: Path,
        indice_fallback: int = 0,
        container_mensal: Optional[Any] = None
    ) -> bool:
        """
        Localiza e faz o download do relatório analítico em PDF da seção especificada ('FGTS' ou 'Consignado').
        Prioriza os botões dentro do container da Guia Mensal para não baixar relatórios de guias Rescisórias.
        """
        logger.info(f"Buscando botão de download do relatório PDF ({secao_nome})...")
        caminho_destino.parent.mkdir(parents=True, exist_ok=True)

        seletores_pdf = [
            "button:has(.fa-file-pdf)",
            "button:has(i[class*='pdf'])",
            "button:has([class*='pdf'])",
            "button[title*='pdf' i]",
            "button[aria-label*='pdf' i]",
            "a[title*='pdf' i]",
            "i.fa-file-pdf",
            "[class*='fa-file-pdf']"
        ]

        btn_alvo = None

        # 1. Se temos container mensal, procura os botões da seção DENTRO do container mensal
        if container_mensal:
            try:
                cabecalhos = container_mensal.locator("h1, h2, h3, h4, h5, h6, strong, span.title, div.card-header, div, span").filter(has_text=secao_nome).all()
                for cab in cabecalhos:
                    parent = cab.locator("xpath=..")
                    for s in seletores_pdf:
                        botoes = parent.locator(s)
                        if botoes.count() > 0 and botoes.first.is_visible():
                            btn_alvo = botoes.first
                            logger.info(f"Botão PDF para '{secao_nome}' localizado no cabeçalho dentro do container Mensal.")
                            break
                    if btn_alvo:
                        break

                if not btn_alvo:
                    for s in seletores_pdf:
                        botoes = container_mensal.locator(s).all()
                        visiveis = [b for b in botoes if b.is_visible()]
                        idx_rel = 0 if secao_nome.lower() == "fgts" else 1
                        if len(visiveis) > idx_rel:
                            btn_alvo = visiveis[idx_rel]
                            logger.info(f"Botão PDF para '{secao_nome}' selecionado no container Mensal por índice {idx_rel}.")
                            break
            except Exception as e:
                logger.debug(f"Tentativa de buscar botão PDF no container mensal falhou: {e}")

        # 2. Se não encontrou no container mensal, busca após o texto 'Mensal - Vencimento'
        if not btn_alvo:
            try:
                loc_header_mensal = self.page.locator("text=/Mensal\\s*-\\s*Vencimento/i").first
                if loc_header_mensal.is_visible(timeout=1000):
                    cabs_apos = loc_header_mensal.locator(f"xpath=following::*[self::h1 or self::h2 or self::h3 or self::h4 or self::h5 or self::h6 or self::strong or self::div or self::span][contains(text(), '{secao_nome}')]").all()
                    for cab in cabs_apos:
                        parent = cab.locator("xpath=..")
                        for s in seletores_pdf:
                            botoes = parent.locator(s)
                            if botoes.count() > 0 and botoes.first.is_visible():
                                btn_alvo = botoes.first
                                logger.info(f"Botão PDF para '{secao_nome}' localizado após cabeçalho Mensal.")
                                break
                        if btn_alvo:
                            break
            except Exception as e:
                logger.debug(f"Busca de PDF após header mensal falhou: {e}")

        # 3. Procura geral próximo ao cabeçalho da seção
        if not btn_alvo:
            try:
                cabecalhos = self.page.locator("h1, h2, h3, h4, h5, h6, strong, span.title, div.card-header").filter(has_text=secao_nome).all()
                for cab in cabecalhos:
                    parent = cab.locator("xpath=..")
                    for s in seletores_pdf:
                        botoes = parent.locator(s)
                        if botoes.count() > 0 and botoes.first.is_visible():
                            btn_alvo = botoes.first
                            logger.info(f"Botão PDF para '{secao_nome}' localizado no cabeçalho da seção.")
                            break
                    if btn_alvo:
                        break
            except Exception as e:
                logger.debug(f"Tentativa geral de localizar botão {secao_nome} falhou: {e}")

        # 4. Fallback: seleciona por índice global dos botões de PDF visíveis
        if not btn_alvo:
            logger.info(f"Tentando localizar botão PDF para '{secao_nome}' via índice de botões visíveis (índice: {indice_fallback})...")
            for s in seletores_pdf:
                try:
                    todos = self.page.locator(s).all()
                    visiveis = [el for el in todos if el.is_visible()]
                    if len(visiveis) > indice_fallback:
                        btn_alvo = visiveis[indice_fallback]
                        logger.info(f"Botão PDF localizado pelo seletor '{s}' no índice {indice_fallback}.")
                        break
                except Exception:
                    continue

        if not btn_alvo:
            logger.warning(f"Botão de relatório PDF para '{secao_nome}' não foi encontrado.")
            return False

        try:
            with self.page.expect_download(timeout=15000) as download_info:
                btn_alvo.click()
            download = download_info.value
            download.save_as(str(caminho_destino))
            logger.info(f"Relatório PDF ({secao_nome}) baixado com sucesso: {caminho_destino.name}")
            return True
        except Exception as e:
            logger.warning(f"Erro ou tempo limite ao baixar relatório PDF ({secao_nome}): {e}")
            return False

    def _confirmar_modal_se_houver(self) -> bool:
        """Detecta modais de confirmação abertos (como 'Confirma nova emissão?') e clica no botão afirmativo."""
        try:
            botoes_confirmar = [
                "button:has-text('Confirmar')",
                "button.primary:has-text('Confirmar')",
                "button:has-text('Sim')",
                "button.primary:has-text('Sim')",
                "button:has-text('Emitir')",
                "button:has-text('Continuar')",
                "button:has-text('Ok')"
            ]
            for b_sel in botoes_confirmar:
                btn = self.page.locator(b_sel).first
                if btn.is_visible(timeout=800):
                    logger.info(f"Confirmando modal com botão: '{b_sel}'")
                    btn.click()
                    time.sleep(1.0)
                    return True
        except Exception:
            pass
        return False

    def _recuperar_pdf_temp_recente(self, tempo_max_segundos: int = 120) -> Optional[Path]:
        """
        Recupera o PDF mais recente gerado no diretório temporário do Playwright/Chrome.
        Garante que o arquivo da guia seja copiado mesmo se o evento CDP do download não for disparado na página.
        """
        temp_dir = tempfile.gettempdir()
        padrao = os.path.join(temp_dir, "playwright-artifacts-*", "*")
        arquivos = glob.glob(padrao)
        candidatos = []
        agora = time.time()
        for arq in arquivos:
            try:
                mtime = os.path.getmtime(arq)
                size = os.path.getsize(arq)
                if (agora - mtime) <= tempo_max_segundos and size > 20000:
                    with open(arq, "rb") as f:
                        magic = f.read(5)
                    if magic.startswith(b"%PDF"):
                        candidatos.append((mtime, Path(arq)))
            except Exception:
                continue
        if candidatos:
            candidatos.sort(key=lambda x: x[0], reverse=True)
            return candidatos[0][1]
        return None

    def _emitir_guia_gfd(self, caminho_guia: Path, container_mensal: Optional[Any] = None) -> bool:
        """
        Clica no botão 'Emitir guia' da Guia MENSAL e intercepta o download do arquivo PDF da GFD.
        Trata o modal de confirmação 'Gerar guia - Confirma nova emissão?' e botões pós-emissão.
        Conta com listener nativo de downloads e fallback para garantir a persistência na pasta.
        """
        logger.info("Solicitando emissão da guia GFD Mensal...")
        caminho_guia.parent.mkdir(parents=True, exist_ok=True)

        downloads_capturados = []

        def on_download(download):
            logger.info(f"Evento de download capturado pelo Playwright: {download.suggested_filename}")
            downloads_capturados.append(download)

        try:
            self.page.on("download", on_download)
        except Exception:
            pass

        try:
            # 1. Se o modal de confirmação 'Gerar guia' já estiver aberto na tela
            btn_confirmar = self.page.locator("button:has-text('Confirmar'), button.primary:has-text('Confirmar')").first
            if btn_confirmar.is_visible(timeout=1000):
                logger.info("Modal 'Gerar guia' já está aberto! Clicando em 'Confirmar'...")
                btn_confirmar.click()
            else:
                # 2. Localiza o botão 'Emitir guia' priorizando a Guia MENSAL
                btn_emitir = None

                # 2a. Busca no container isolado da Guia Mensal
                if container_mensal:
                    try:
                        for s in ["button:has-text('Emitir guia')", "button:has-text('Emitir Guia')", "button:has-text('Emitir')"]:
                            loc = container_mensal.locator(s)
                            if loc.count() > 0 and loc.first.is_visible():
                                btn_emitir = loc.first
                                logger.info("Botão 'Emitir guia' localizado diretamente no card Mensal.")
                                break
                    except Exception:
                        pass

                # 2b. Busca pelo botão que segue imediatamente o cabeçalho 'Mensal - Vencimento'
                if not btn_emitir:
                    try:
                        loc_header_mensal = self.page.locator("text=/Mensal\\s*-\\s*Vencimento/i").first
                        if loc_header_mensal.is_visible(timeout=1000):
                            btn_apos = loc_header_mensal.locator("xpath=following::button[contains(., 'Emitir')][1]").first
                            if btn_apos.is_visible(timeout=1500):
                                btn_emitir = btn_apos
                                logger.info("Botão 'Emitir guia' localizado imediatamente após o cabeçalho 'Mensal - Vencimento'.")
                    except Exception:
                        pass

                # 2c. Fallback geral para qualquer botão 'Emitir guia' visível
                if not btn_emitir:
                    for s in sel.BTN_EMITIR_GUIA:
                        loc = self.page.locator(s)
                        if loc.count() > 0 and loc.first.is_visible():
                            btn_emitir = loc.first
                            break

                if not btn_emitir:
                    logger.warning("Botão 'Emitir guia' não localizado na tela.")
                    return False

                logger.info("Clicando no botão 'Emitir guia' da Guia Mensal...")
                btn_emitir.click()
                time.sleep(1.0)

                # Verifica se abriu o modal de confirmação 'Confirma nova emissão?'
                if btn_confirmar.is_visible(timeout=3000):
                    logger.info("Modal 'Gerar guia - Confirma nova emissão?' exibido! Clicando em 'Confirmar'...")
                    btn_confirmar.click()

            # 3. Aguarda até 15 segundos para o download ser despachado
            for _ in range(30):
                if downloads_capturados:
                    break
                time.sleep(0.5)

            # 4. Se ainda não capturou, tenta botões pós-emissão (Baixar Guia, etc.)
            if not downloads_capturados:
                seletores_pos = [
                    "button:has-text('Baixar Guia')",
                    "button:has-text('Baixar guia')",
                    "button:has-text('Download')",
                    "button:has-text('Baixar')",
                    "a:has-text('Baixar Guia')",
                    "a:has-text('Baixar')",
                    "button:has-text('Imprimir Guia')"
                ]
                for s_pos in seletores_pos:
                    btn_pos = self.page.locator(s_pos).first
                    if btn_pos.is_visible(timeout=1000):
                        logger.info(f"Clicando no botão de download '{s_pos}'...")
                        btn_pos.click()
                        time.sleep(2.0)
                        break

            # Aguarda mais alguns segundos para finalização
            for _ in range(10):
                if downloads_capturados:
                    break
                time.sleep(0.5)

            # 5. Salva o arquivo baixado via evento do Playwright
            if downloads_capturados:
                download_obj = downloads_capturados[-1]
                download_obj.save_as(str(caminho_guia))
                logger.info(f"Guia GFD salva com sucesso em: {caminho_guia.name}")
                return True

            # 6. Fallback: Recupera o arquivo gerado pelo Chrome na pasta temporária do Playwright
            logger.info("Verificando se o arquivo da guia foi salvo em diretório temporário...")
            pdf_temp = self._recuperar_pdf_temp_recente(tempo_max_segundos=60)
            if pdf_temp and pdf_temp.exists():
                shutil.copy(str(pdf_temp), str(caminho_guia))
                logger.info(f"Guia GFD recuperada e salva com sucesso via fallback: {caminho_guia.name} ({pdf_temp.stat().st_size} bytes)")
                return True

            logger.warning("Nenhum download de guia GFD foi concluído ou localizado.")
            return False

        except Exception as e:
            logger.error(f"Erro ao processar emissão da guia GFD: {e}")
            return False
        finally:
            try:
                self.page.remove_listener("download", on_download)
            except Exception:
                pass

    def emitir_guia_e_relatorios(
        self,
        cnpj: str,
        razao_social: str,
        competencia: str,
        fgts_esperado: float = 0.0,
        bloquear_se_divergente: bool = True,
        templates_nomes: Optional[Dict[str, str]] = None,
        apenas_conferir: bool = False
    ) -> Dict[str, Any]:
        """
        Navega para a Gestão de Guias -> Emissão de Guia Rápida,
        seleciona a competência no dropdown, clica em pesquisar,
        valida o valor apurado contra o valor da folha (se fornecido),
        baixa os relatórios analíticos em PDF (FGTS e Consignado)
        e emite a Guia Rápida (GFD) com nomenclatura personalizável.
        """
        cnpj_limpo = limpar_cnpj(cnpj)
        cnpj_fmt = formatar_cnpj(cnpj_limpo)
        comp_pasta = competencia.replace("/", "-")
        razao_sanitizada = sanitizar_nome_arquivo(razao_social)[:40]

        pasta_empresa = self.output_base_dir / comp_pasta / f"{cnpj_limpo}_{razao_sanitizada}"

        # Padrões de nomenclatura configuráveis
        tpls = {
            "guia": "FGTS - Competencia",
            "relatorio_fgts": "RE FGTS - Competencia",
            "relatorio_consignado": "Consignado FGTS - Competencia",
            **(templates_nomes or {})
        }
        ctx = {
            "cnpj": cnpj_limpo,
            "razao_social": razao_social,
            "competencia": competencia
        }
        nome_guia = formatar_nome_documento(tpls.get("guia", "FGTS - Competencia"), ctx)
        nome_rel_fgts = formatar_nome_documento(tpls.get("relatorio_fgts", "RE FGTS - Competencia"), ctx)
        nome_rel_cons = formatar_nome_documento(tpls.get("relatorio_consignado", "Consignado FGTS - Competencia"), ctx)

        resultado = {
            "cnpj": cnpj_limpo,
            "cnpj_formatado": cnpj_fmt,
            "razao_social": razao_social,
            "competencia": competencia,
            "status": "Iniciado",
            "valor_guia": 0.0,
            "fgts_esperado": fgts_esperado,
            "diferenca": 0.0,
            "arquivo_guia": "",
            "arquivo_relatorio": "",
            "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "detalhes": ""
        }

        try:
            # 1. Acessar menu Gestão de Guias -> Emissão de Guia Rápida
            logger.info(f"{cnpj_fmt}: Acessando Gestão de Guias...")
            if "emissao-guia-rapida" not in self.page.url:
                if not self._clicar_primeiro_disponivel(sel.CARD_GESTAO_GUIAS, timeout_ms=4000):
                    self.page.goto("https://fgtsdigital.sistema.gov.br/cobranca/#/gestao-guias/emissao-guia-rapida", wait_until="domcontentloaded")
                else:
                    time.sleep(1.5)
                    self._clicar_primeiro_disponivel(sel.CARD_GUIA_RAPIDA, timeout_ms=5000)
                time.sleep(2.0)

            # 2. Selecionar competência e clicar em Pesquisar
            sucesso_pesquisa = self._selecionar_competencia_e_pesquisar(competencia)
            if not sucesso_pesquisa:
                logger.warning(f"{cnpj_fmt}: Não foi possível executar a pesquisa para a competência {competencia}.")

            # 3. Verifica mensagens de status/bloqueio (ex: COB0003 - Não há débitos de interesse)
            if self._elemento_visivel(sel.ALERTA_SEM_DEBITOS, timeout_ms=2500):
                resultado["status"] = "Sem Débitos / Movimento"
                resultado["detalhes"] = "Não há débitos de interesse para o empregador (COB0003)."
                logger.info(f"{cnpj_fmt}: {resultado['status']}")
                
                if fgts_esperado > 0:
                    resultado["diferenca"] = -fgts_esperado
                    resultado["detalhes"] = f"Folha previa R$ {fgts_esperado:.2f}, mas o portal acusa 'Sem Débitos' (COB0003)."
                
                self._clicar_primeiro_disponivel(sel.BTN_FECHAR_AVISO, timeout_ms=2000)
                time.sleep(0.5)
                self.page.goto("https://fgtsdigital.sistema.gov.br/portal/servicos", wait_until="domcontentloaded")
                time.sleep(1.0)
                return resultado

            if self._elemento_visivel(sel.ALERTA_ESOCIAL_PENDENTE, timeout_ms=2000):
                resultado["status"] = "Pendente eSocial"
                resultado["detalhes"] = "Folha de pagamento ainda não transmitida ou fechada no eSocial."
                logger.warning(f"{cnpj_fmt}: {resultado['status']}")
                self._clicar_primeiro_disponivel(sel.BTN_FECHAR_AVISO, timeout_ms=2000)
                self.page.goto("https://fgtsdigital.sistema.gov.br/portal/servicos", wait_until="domcontentloaded")
                time.sleep(1.0)
                return resultado

            # 4. Leitura e Validação do Valor Apurado na Tela (priorizando Guia Mensal)
            container_mensal = self._obter_container_mensal(fgts_esperado=fgts_esperado)
            valor_tela = self._extrair_valor_tela_fgts(container_mensal=container_mensal, fgts_esperado=fgts_esperado)
            if valor_tela == 0.0:
                time.sleep(2.0)
                container_mensal = self._obter_container_mensal(fgts_esperado=fgts_esperado)
                valor_tela = self._extrair_valor_tela_fgts(container_mensal=container_mensal, fgts_esperado=fgts_esperado)

            resultado["valor_guia"] = valor_tela

            # 5. Modo Apenas Conferir Valores (Auditoria sem emissão de guia)
            if apenas_conferir:
                if fgts_esperado > 0:
                    diferenca = valor_tela - fgts_esperado
                    resultado["diferenca"] = diferenca
                    if abs(diferenca) <= 0.02:
                        msg_conf = f"Valores Conferem (Iguais)! Relatório: R$ {fgts_esperado:.2f} | FGTS Digital: R$ {valor_tela:.2f}."
                        logger.info(f"{cnpj_fmt}: {msg_conf}")
                        resultado["status"] = "Conferido (Valores Iguais)"
                        resultado["detalhes"] = msg_conf
                    else:
                        msg_conf = (
                            f"DIVERGÊNCIA DE VALORES! "
                            f"Relatório: R$ {fgts_esperado:.2f} | FGTS Digital: R$ {valor_tela:.2f} | "
                            f"Diferença: R$ {diferenca:+.2f}."
                        )
                        logger.warning(f"{cnpj_fmt}: {msg_conf}")
                        resultado["status"] = "Divergência de Valores"
                        resultado["detalhes"] = msg_conf
                else:
                    msg_conf = f"Valor apurado no FGTS Digital: R$ {valor_tela:.2f} (sem valor de relatório para confronto)."
                    logger.info(f"{cnpj_fmt}: {msg_conf}")
                    resultado["status"] = "Valor Consultado"
                    resultado["detalhes"] = msg_conf

                self.page.goto("https://fgtsdigital.sistema.gov.br/portal/servicos", wait_until="domcontentloaded")
                time.sleep(1.0)
                return resultado

            # 6. Auditoria de Divergência contra Folha (Emissão Normal)
            if fgts_esperado > 0:
                diferenca = valor_tela - fgts_esperado
                resultado["diferenca"] = diferenca

                # Tolerância de 2 centavos para possíveis arredondamentos
                if bloquear_se_divergente and abs(diferenca) > 0.02:
                    msg_diverg = (
                        f"DIVERGÊNCIA DE VALORES DETECTADA! "
                        f"Folha/Relatório: R$ {fgts_esperado:.2f} | FGTS Digital: R$ {valor_tela:.2f} | Diferença: R$ {diferenca:+.2f}. "
                        f"Emissão da guia cancelada por segurança."
                    )
                    logger.warning(f"{cnpj_fmt}: {msg_diverg}")
                    resultado["status"] = "Divergência de Valores (Não Emitida)"
                    resultado["detalhes"] = msg_diverg

                    # Baixa os relatórios analíticos em PDF para auditoria contábil
                    arquivos_audit = []
                    caminho_rel_fgts_div = pasta_empresa / f"Divergencia_{nome_rel_fgts}"
                    if self._baixar_relatorio_pdf("FGTS", caminho_rel_fgts_div, indice_fallback=0, container_mensal=container_mensal):
                        arquivos_audit.append(caminho_rel_fgts_div.name)

                    try:
                        tem_consignado = False
                        if container_mensal:
                            tem_consignado = "consignado" in container_mensal.inner_text().lower()
                        if not tem_consignado:
                            tem_consignado = "consignado" in self.page.inner_text("body").lower()

                        if tem_consignado:
                            caminho_rel_cons_div = pasta_empresa / f"Divergencia_{nome_rel_cons}"
                            if self._baixar_relatorio_pdf("Consignado", caminho_rel_cons_div, indice_fallback=1, container_mensal=container_mensal):
                                arquivos_audit.append(caminho_rel_cons_div.name)
                    except Exception:
                        pass

                    if arquivos_audit:
                        resultado["arquivo_relatorio"] = ", ".join(arquivos_audit)

                    self.page.goto("https://fgtsdigital.sistema.gov.br/portal/servicos", wait_until="domcontentloaded")
                    time.sleep(1.0)
                    return resultado

            # 6. Download dos Relatórios Analíticos em PDF (FGTS e Consignado)
            arquivos_baixados = []
            caminho_rel_fgts = pasta_empresa / nome_rel_fgts
            if self._baixar_relatorio_pdf("FGTS", caminho_rel_fgts, indice_fallback=0, container_mensal=container_mensal):
                arquivos_baixados.append(caminho_rel_fgts.name)

            try:
                tem_consignado = False
                if container_mensal:
                    tem_consignado = "consignado" in container_mensal.inner_text().lower()
                if not tem_consignado:
                    tem_consignado = "consignado" in self.page.inner_text("body").lower()

                if tem_consignado:
                    caminho_rel_cons = pasta_empresa / nome_rel_cons
                    if self._baixar_relatorio_pdf("Consignado", caminho_rel_cons, indice_fallback=1, container_mensal=container_mensal):
                        arquivos_baixados.append(caminho_rel_cons.name)
            except Exception as e:
                logger.warning(f"{cnpj_fmt}: Falha ao verificar/baixar relatório consignado: {e}")

            if arquivos_baixados:
                resultado["arquivo_relatorio"] = ", ".join(arquivos_baixados)

            # 7. Emissão da Guia (GFD)
            caminho_guia = pasta_empresa / nome_guia
            sucesso_guia = self._emitir_guia_gfd(caminho_guia, container_mensal=container_mensal)
            if sucesso_guia:
                resultado["status"] = "Sucesso - Guia Emitida"
                resultado["arquivo_guia"] = caminho_guia.name
                resultado["detalhes"] = f"Guia GFD gerada e salva com sucesso (Valor: R$ {valor_tela:.2f})."
            else:
                if arquivos_baixados:
                    resultado["status"] = "Relatórios Baixados (Guia Pendente)"
                    resultado["detalhes"] = "Relatórios em PDF baixados, mas houve timeout ou pendência ao baixar a GFD."
                else:
                    resultado["status"] = "Falha na Emissão"
                    resultado["detalhes"] = "Não foi possível concluir o download da Guia GFD."

            # 8. Retorno à tela de serviços para a próxima empresa
            self.page.goto("https://fgtsdigital.sistema.gov.br/portal/servicos", wait_until="domcontentloaded")
            time.sleep(1.0)
            return resultado

        except Exception as e:
            logger.error(f"{cnpj_fmt}: Erro durante processamento: {e}")
            resultado["status"] = "Erro Técnico"
            resultado["detalhes"] = str(e)
            try:
                self.page.goto("https://fgtsdigital.sistema.gov.br/portal/servicos", wait_until="domcontentloaded")
            except Exception:
                pass
            return resultado

    def processar_lote(
        self,
        empresas: List[Dict[str, Any]],
        competencia: str,
        callback_progresso: Optional[Any] = None,
        bloquear_se_divergente: bool = True,
        apenas_conferir: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Itera sobre a lista de empresas, alternando perfis e emitindo as guias (ou apenas conferindo valores).
        """
        resultados = []
        total = len(empresas)

        modo_txt = "CONFERÊNCIA DE VALORES" if apenas_conferir else "EMISSÃO EM LOTE"
        logger.info(f"Iniciando [{modo_txt}] de {total} empresas para a competência {competencia}...")

        for idx, emp in enumerate(empresas, start=1):
            cnpj = emp["cnpj"]
            razao = emp["razao_social"]
            comp_empresa = emp.get("competencia") or competencia
            fgts_esperado = float(emp.get("fgts_esperado", 0.0) or 0.0)

            logger.info(f"[{idx}/{total}] Processando {emp['cnpj_formatado']} - {razao} (FGTS Esperado: R$ {fgts_esperado:.2f})...")

            # Troca de perfil
            troca = self.trocar_perfil(cnpj)
            if not troca["sucesso"]:
                res = {
                    "cnpj": cnpj,
                    "cnpj_formatado": emp["cnpj_formatado"],
                    "razao_social": razao,
                    "competencia": comp_empresa,
                    "status": "Erro de Procuração",
                    "valor_guia": 0.0,
                    "fgts_esperado": fgts_esperado,
                    "diferenca": 0.0,
                    "arquivo_guia": "",
                    "arquivo_relatorio": "",
                    "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "detalhes": troca.get("motivo", "Procuração não disponível")
                }
            else:
                # Emite a guia e relatórios ou apenas confere valores
                res = self.emitir_guia_e_relatorios(
                    cnpj,
                    razao,
                    comp_empresa,
                    fgts_esperado=fgts_esperado,
                    bloquear_se_divergente=bloquear_se_divergente,
                    apenas_conferir=apenas_conferir
                )

            resultados.append(res)

            if callback_progresso:
                try:
                    callback_progresso(idx, total, res)
                except Exception:
                    pass

            # Pequeno intervalo amigável entre requisições
            time.sleep(1.0)

        logger.info(f"Lote concluído: {total} empresas processadas.")
        return resultados
