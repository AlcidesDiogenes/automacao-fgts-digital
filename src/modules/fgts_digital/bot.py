"""
Robô de Automação do Portal FGTS Digital.
Executa autenticação com Gov.br via A1, alternância de perfil por procuração,
emissão de guias GFD (com PIX) e download de relatórios de débitos.
"""

import os
import shutil
import hashlib
import tempfile
import glob
from pathlib import Path
from datetime import datetime
import time
import threading
from typing import Dict, Any, List, Optional, Callable
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
from src.modules.fgts_digital.validacao_pdf import validar_pdf_documento
from src.utils.logger import logger
from config import settings


class FGTSDigitalBot:
    """Robô que navega pelo portal FGTS Digital executando a rotina de emissão em lote."""

    def __init__(self, page: Page, output_base_dir: Path):
        self.page = page
        self.output_base_dir = Path(output_base_dir)
        # Motivo da última reprovação de PDF (exibido nos detalhes do resultado)
        self.ultima_rejeicao: str = ""

    def _validar_ou_rejeitar(self, caminho: Path, validacao: Optional[Dict[str, Any]]) -> bool:
        """
        Confere o conteúdo do PDF salvo. Se reprovado, move para '_rejeitados' dentro da pasta
        da empresa (nunca fica com o nome final) e registra o motivo.
        """
        if not validacao:
            return True
        ok, motivo = validar_pdf_documento(
            caminho,
            validacao["cnpj"],
            validacao["competencia"],
            valor_esperado=validacao.get("valor"),
        )
        if ok:
            return True
        destino = caminho.parent / "_rejeitados" / caminho.name
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(caminho), str(destino))
        self.ultima_rejeicao = f"{caminho.name}: {motivo}"
        logger.error(f"PDF REPROVADO na validação ({motivo}). Arquivo movido para: {destino}")
        return False

    # Observação: locator.is_visible(timeout=...) do Playwright IGNORA o timeout (não espera).
    # Os helpers abaixo fazem a espera de verdade, verificando todos os seletores a cada 250 ms
    # até o prazo. timeout_ms=0 significa "verificar só agora" (usado quando a página já foi
    # aguardada antes e a ausência do elemento é o caso normal, para não atrasar cada empresa).

    def _primeiro_visivel(self, seletores: List[str], timeout_ms: int) -> Optional[Any]:
        """Retorna o primeiro locator visível entre os seletores, aguardando até timeout_ms."""
        limite = time.time() + timeout_ms / 1000
        while True:
            for s in seletores:
                try:
                    el = self.page.locator(s).first
                    if el.is_visible():
                        return el
                except Exception:
                    continue
            if time.time() >= limite:
                return None
            time.sleep(0.25)

    def _clicar_primeiro_disponivel(self, seletores: List[str], timeout_ms: int = 5000) -> bool:
        """Clica no primeiro seletor que ficar visível em até timeout_ms."""
        el = self._primeiro_visivel(seletores, timeout_ms)
        if el is None:
            return False
        try:
            el.click()
            return True
        except Exception:
            return False

    def _elemento_visivel(self, seletores: List[str], timeout_ms: int = 3000) -> bool:
        """Verifica se algum dos seletores fica visível em até timeout_ms."""
        return self._primeiro_visivel(seletores, timeout_ms) is not None

    @staticmethod
    def _aguardar_visivel(locator: Any, timeout_ms: int) -> bool:
        """Aguarda um locator específico ficar visível (sem lançar exceção)."""
        try:
            locator.wait_for(state="visible", timeout=timeout_ms)
            return True
        except Exception:
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
                    if btn.is_visible():
                        btn.click()
                        clicou_login = True
                        logger.info(f"Clicou em 'Entrar com gov.br' via: {s_login}")
                        break
                except Exception:
                    continue

            if not clicou_login:
                try:
                    btn_text = self.page.get_by_text("gov.br", exact=False).first
                    if btn_text.is_visible():
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
                    if btn_c.is_visible():
                        btn_c.click()
                        clicou_cert = True
                        logger.info(f"Clicou em certificado via: {s_cert}")
                        break
                except Exception:
                    continue

            if not clicou_cert:
                try:
                    btn_cert_txt = self.page.get_by_text("certificado digital", exact=False).first
                    if btn_cert_txt.is_visible():
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
                pasta_log = settings.LOGS_DIR
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
            self._clicar_primeiro_disponivel(sel.BTN_ACEITAR_COOKIES, timeout_ms=0)

            # 3. Verifica se o modal já está visível; se não, clica em 'Trocar Perfil'
            modal_aberto = self._elemento_visivel(sel.MODAL_PERFIL_CONTAINER, timeout_ms=0)
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
                    if campo.is_visible():
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
            if not self._clicar_primeiro_disponivel(sel.PERFIL_BTN_CONFIRMAR_TROCA, timeout_ms=3000):
                msg = "Botão de confirmação da troca de perfil não localizado"
                logger.warning(f"{cnpj_fmt}: {msg}")
                return {"sucesso": False, "status": "Perfil não confirmado", "motivo": msg}
            time.sleep(2.5)

            # 7. Verifica se houve erro de procuração ou bloqueio retornado no modal
            if self._elemento_visivel(sel.ALERTA_PROCURACAO_INVALIDA, timeout_ms=0):
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

            # 8. Só segue se a barra de perfil mostrar o CNPJ escolhido (evita emitir no perfil anterior)
            if not self._confirmar_perfil_ativo(cnpj_limpo):
                msg = "A barra de perfil não exibe o CNPJ selecionado após a troca"
                logger.warning(f"{cnpj_fmt}: {msg}. Empresa ignorada por segurança.")
                return {"sucesso": False, "status": "Perfil não confirmado", "motivo": msg}

            logger.info(f"Perfil alterado com sucesso para {cnpj_fmt}.")
            return {"sucesso": True}

        except Exception as e:
            logger.error(f"Erro ao trocar perfil para {cnpj_fmt}: {e}")
            return {"sucesso": False, "motivo": str(e)}

    def _textos_indicador_perfil(self) -> List[str]:
        """
        Textos dos elementos que exibem o perfil ativo. Usa os seletores dedicados (ex.: span.dados-perfil);
        só recorre à vizinhança do botão 'Trocar Perfil' se nenhum deles existir na tela.
        """
        textos = []
        for s in sel.PERFIL_INDICADOR_ATIVO:
            try:
                for el in self.page.locator(s).all():
                    if el.is_visible():
                        textos.append(el.inner_text())
            except Exception:
                continue
        if textos:
            return textos
        for s in sel.PERFIL_BTN_TROCAR:
            try:
                btn = self.page.locator(s).first
                if btn.count() > 0 and btn.is_visible():
                    for nivel in (1, 2, 3):
                        textos.append(btn.locator(f"xpath=ancestor::*[{nivel}]").first.inner_text())
                    break
            except Exception:
                continue
        return textos

    def _confirmar_perfil_ativo(self, cnpj_limpo: str, timeout_s: float = 8.0) -> bool:
        """
        Aguarda o modal de perfil fechar e a barra de perfil exibir o CNPJ (ou a raiz) escolhido.
        O FGTS Digital identifica o empregador pela raiz do CNPJ, por isso a raiz é suficiente.
        """
        import re
        raiz = cnpj_limpo[:8]
        padrao = re.compile(rf"(?<![\d.]){raiz[:2]}\.?{raiz[2:5]}\.?{raiz[5:]}")
        limite = time.time() + timeout_s
        while time.time() < limite:
            modal_aberto = self._elemento_visivel(sel.MODAL_PERFIL_CONTAINER, timeout_ms=0)
            if not modal_aberto and any(padrao.search(t or "") for t in self._textos_indicador_perfil()):
                return True
            time.sleep(0.5)
        return False

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
            # Aguarda o formulário de filtros OU o aviso de 'sem débitos'. Sem débito em aberto
            # (COB0003), o portal não exibe o filtro de competência (confirmado em 27/10/2026).
            self.page.wait_for_selector(
                "ng-select, button:has-text('Pesquisar'), " + ", ".join(sel.ALERTA_SEM_DEBITOS),
                timeout=10000
            )
            if self._elemento_visivel(sel.ALERTA_SEM_DEBITOS, timeout_ms=0) and not self.page.locator("ng-select").first.is_visible():
                logger.info("Portal informa que não há débitos em aberto (COB0003); filtro de competência não exibido.")
                return True

            ng_select = self.page.locator("ng-select").first
            if not ng_select.is_visible():
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
                if self._aguardar_visivel(opcao, 2000):
                    opcao.click()
                    logger.info(f"Opção '{competencia}' clicada no dropdown.")
                else:
                    self.page.keyboard.press("Enter")
                    logger.info(f"Pressionado Enter para selecionar '{competencia}'.")

                time.sleep(0.5)

            # Clica no botão Pesquisar
            logger.info("Clicando no botão 'Pesquisar'...")
            btn_pesquisar = self.page.locator("button.secondary:has-text('Pesquisar'), button:has-text('Pesquisar')").first
            if btn_pesquisar.is_visible():
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
        container_mensal: Optional[Any] = None,
        validacao: Optional[Dict[str, Any]] = None
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
                if loc_header_mensal.is_visible():
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
            if not self._validar_ou_rejeitar(caminho_destino, validacao):
                return False
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
                if btn.is_visible():
                    logger.info(f"Confirmando modal com botão: '{b_sel}'")
                    btn.click()
                    time.sleep(1.0)
                    return True
        except Exception:
            pass
        return False

    @staticmethod
    def _hash_arquivo(caminho: Path) -> str:
        with open(caminho, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def _recuperar_pdf_temp_recente(self, desde: float, ignorar_hashes: set) -> Optional[Path]:
        """
        Recupera o PDF gerado no diretório temporário do Playwright/Chrome DEPOIS do clique em 'Emitir'.
        Usado quando o evento CDP do download não é disparado. Ignora arquivos já salvos para a empresa
        (ex.: relatórios analíticos) e o resultado ainda passa pela validação de conteúdo.
        """
        temp_dir = tempfile.gettempdir()
        padrao = os.path.join(temp_dir, "playwright-artifacts-*", "*")
        arquivos = glob.glob(padrao)
        candidatos = []
        for arq in arquivos:
            try:
                mtime = os.path.getmtime(arq)
                if mtime < desde:
                    continue
                with open(arq, "rb") as f:
                    magic = f.read(5)
                if magic.startswith(b"%PDF") and self._hash_arquivo(Path(arq)) not in ignorar_hashes:
                    candidatos.append((mtime, Path(arq)))
            except Exception:
                continue
        if candidatos:
            candidatos.sort(key=lambda x: x[0], reverse=True)
            return candidatos[0][1]
        return None

    def _aceitar_guia_salva(self, caminho_guia: Path, hashes_existentes: set, validacao: Optional[Dict[str, Any]]) -> bool:
        """Rejeita a guia se for cópia de um PDF já salvo para a empresa ou se o conteúdo não conferir."""
        if self._hash_arquivo(caminho_guia) in hashes_existentes:
            destino = caminho_guia.parent / "_rejeitados" / caminho_guia.name
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(caminho_guia), str(destino))
            self.ultima_rejeicao = f"{caminho_guia.name}: arquivo idêntico a um relatório já salvo"
            logger.error(f"PDF REPROVADO: a 'guia' baixada é cópia de um relatório já salvo. Movido para: {destino}")
            return False
        if not self._validar_ou_rejeitar(caminho_guia, validacao):
            return False
        logger.info(f"Guia GFD salva e validada com sucesso: {caminho_guia.name}")
        return True

    def _emitir_guia_gfd(
        self,
        caminho_guia: Path,
        container_mensal: Optional[Any] = None,
        validacao: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Clica no botão 'Emitir guia' DENTRO do card Mensal selecionado e intercepta o download da GFD.
        Trata o modal de confirmação 'Gerar guia - Confirma nova emissão?' e botões pós-emissão.
        Sem card Mensal identificado, não emite. Todo PDF salvo passa pela validação de conteúdo.
        """
        logger.info("Solicitando emissão da guia GFD Mensal...")
        caminho_guia.parent.mkdir(parents=True, exist_ok=True)

        if container_mensal is None:
            logger.warning("Card da Guia Mensal não identificado: emissão bloqueada por segurança.")
            return False

        # PDFs já salvos para a empresa (ex.: relatórios) não podem ser aceitos como guia
        hashes_existentes = {self._hash_arquivo(p) for p in caminho_guia.parent.glob("*.pdf")}
        inicio_emissao = time.time()

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
            if btn_confirmar.is_visible():
                logger.info("Modal 'Gerar guia' já está aberto! Clicando em 'Confirmar'...")
                btn_confirmar.click()
            else:
                # 2. Localiza o botão 'Emitir guia' somente dentro do card Mensal selecionado
                #    (botões fora do card podem pertencer a guias Rescisórias ou residuais)
                btn_emitir = None
                try:
                    for s_btn in ["button:has-text('Emitir guia')", "button:has-text('Emitir Guia')", "button:has-text('Emitir')"]:
                        loc = container_mensal.locator(s_btn)
                        if loc.count() > 0 and loc.first.is_visible():
                            btn_emitir = loc.first
                            logger.info("Botão 'Emitir guia' localizado diretamente no card Mensal.")
                            break
                except Exception:
                    pass

                if not btn_emitir:
                    logger.warning("Botão 'Emitir guia' não localizado dentro do card Mensal.")
                    return False

                logger.info("Clicando no botão 'Emitir guia' da Guia Mensal...")
                btn_emitir.click()
                time.sleep(1.0)

                # Verifica se abriu o modal de confirmação 'Confirma nova emissão?'
                if self._aguardar_visivel(btn_confirmar, 3000):
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
                    if btn_pos.is_visible():
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
                return self._aceitar_guia_salva(caminho_guia, hashes_existentes, validacao)

            # 6. Fallback: PDF criado na pasta temporária do Playwright DEPOIS do clique em 'Emitir'
            logger.info("Verificando se o arquivo da guia foi salvo em diretório temporário...")
            pdf_temp = self._recuperar_pdf_temp_recente(desde=inicio_emissao, ignorar_hashes=hashes_existentes)
            if pdf_temp and pdf_temp.exists():
                shutil.copy(str(pdf_temp), str(caminho_guia))
                logger.info(f"Guia GFD recuperada via pasta temporária ({pdf_temp.stat().st_size} bytes). Validando conteúdo...")
                return self._aceitar_guia_salva(caminho_guia, hashes_existentes, validacao)

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
        apenas_conferir: bool = False,
        exigir_valor_esperado: bool = True
    ) -> Dict[str, Any]:
        """
        Navega para a Gestão de Guias -> Emissão de Guia Rápida,
        seleciona a competência no dropdown, clica em pesquisar,
        valida o valor apurado contra o valor da folha (se fornecido),
        baixa os relatórios analíticos em PDF (FGTS e Consignado)
        e emite a Guia Rápida (GFD) com nomenclatura personalizável.
        Na dúvida não emite: sem valor esperado (se exigido), sem card Mensal
        identificado ou com PDF reprovado na validação de conteúdo.
        """
        cnpj_limpo = limpar_cnpj(cnpj)
        cnpj_fmt = formatar_cnpj(cnpj_limpo)
        self.ultima_rejeicao = ""
        validacao_rel = {"cnpj": cnpj_limpo, "competencia": competencia}
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
            if self._elemento_visivel(sel.ALERTA_SEM_DEBITOS, timeout_ms=0):
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

            if self._elemento_visivel(sel.ALERTA_ESOCIAL_PENDENTE, timeout_ms=0):
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

            # 5b. Travas de segurança antes de qualquer emissão
            if fgts_esperado <= 0 and exigir_valor_esperado:
                msg = (
                    f"Sem valor esperado (folha/relatório) para conferir o FGTS Digital (R$ {valor_tela:.2f}). "
                    f"Guia não emitida. Informe o valor na planilha ou desative a exigência em Parâmetros."
                )
                logger.warning(f"{cnpj_fmt}: {msg}")
                resultado["status"] = "Sem Valor de Referência (Não Emitida)"
                resultado["detalhes"] = msg
                self.page.goto("https://fgtsdigital.sistema.gov.br/portal/servicos", wait_until="domcontentloaded")
                time.sleep(1.0)
                return resultado

            if container_mensal is None:
                msg = "Card da Guia Mensal não identificado na tela. Guia não emitida por segurança."
                logger.warning(f"{cnpj_fmt}: {msg}")
                resultado["status"] = "Card Mensal Não Identificado (Não Emitida)"
                resultado["detalhes"] = msg
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
                    if self._baixar_relatorio_pdf("FGTS", caminho_rel_fgts_div, indice_fallback=0, container_mensal=container_mensal, validacao=validacao_rel):
                        arquivos_audit.append(caminho_rel_fgts_div.name)

                    try:
                        tem_consignado = False
                        if container_mensal:
                            tem_consignado = "consignado" in container_mensal.inner_text().lower()
                        if not tem_consignado:
                            tem_consignado = "consignado" in self.page.inner_text("body").lower()

                        if tem_consignado:
                            caminho_rel_cons_div = pasta_empresa / f"Divergencia_{nome_rel_cons}"
                            if self._baixar_relatorio_pdf("Consignado", caminho_rel_cons_div, indice_fallback=1, container_mensal=container_mensal, validacao=validacao_rel):
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
            if self._baixar_relatorio_pdf("FGTS", caminho_rel_fgts, indice_fallback=0, container_mensal=container_mensal, validacao=validacao_rel):
                arquivos_baixados.append(caminho_rel_fgts.name)

            try:
                tem_consignado = False
                if container_mensal:
                    tem_consignado = "consignado" in container_mensal.inner_text().lower()
                if not tem_consignado:
                    tem_consignado = "consignado" in self.page.inner_text("body").lower()

                if tem_consignado:
                    caminho_rel_cons = pasta_empresa / nome_rel_cons
                    if self._baixar_relatorio_pdf("Consignado", caminho_rel_cons, indice_fallback=1, container_mensal=container_mensal, validacao=validacao_rel):
                        arquivos_baixados.append(caminho_rel_cons.name)
            except Exception as e:
                logger.warning(f"{cnpj_fmt}: Falha ao verificar/baixar relatório consignado: {e}")

            if arquivos_baixados:
                resultado["arquivo_relatorio"] = ", ".join(arquivos_baixados)

            # 6b. Relatório reprovado na validação indica perfil/empresa errados: não emite a guia
            if self.ultima_rejeicao:
                resultado["status"] = "Falha na Validação do PDF (Relatório) - Guia Não Emitida"
                resultado["detalhes"] = (
                    f"Relatório baixado não confere com a empresa/competência ({self.ultima_rejeicao}). "
                    f"Guia não emitida por segurança; arquivo em '_rejeitados'."
                )
                logger.error(f"{cnpj_fmt}: {resultado['detalhes']}")
                self.page.goto("https://fgtsdigital.sistema.gov.br/portal/servicos", wait_until="domcontentloaded")
                time.sleep(1.0)
                return resultado

            # 7. Emissão da Guia (GFD)
            caminho_guia = pasta_empresa / nome_guia
            validacao_guia = {**validacao_rel, "valor": valor_tela}
            sucesso_guia = self._emitir_guia_gfd(caminho_guia, container_mensal=container_mensal, validacao=validacao_guia)
            if sucesso_guia:
                resultado["status"] = "Sucesso - Guia Emitida"
                resultado["arquivo_guia"] = caminho_guia.name
                resultado["detalhes"] = f"Guia GFD gerada, salva e validada (Valor: R$ {valor_tela:.2f})."
            elif self.ultima_rejeicao:
                resultado["status"] = "Falha na Validação do PDF (Guia)"
                resultado["detalhes"] = (
                    f"A guia foi solicitada no portal, mas o PDF baixado não confere ({self.ultima_rejeicao}). "
                    f"Arquivo movido para '_rejeitados'. Conferir manualmente no FGTS Digital."
                )
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
        callback_progresso: Optional[Callable[[int, int, Dict[str, Any]], None]] = None,
        bloquear_se_divergente: bool = True,
        apenas_conferir: bool = False,
        exigir_valor_esperado: bool = True,
        templates_nomes: Optional[Dict[str, str]] = None,
        callback_inicio: Optional[Callable[[int, int, Dict[str, Any]], None]] = None,
        evento_parar: Optional[threading.Event] = None
    ) -> List[Dict[str, Any]]:
        """
        Itera sobre a lista de empresas, alternando perfis e emitindo as guias (ou apenas conferindo valores).
        Laço único usado pela interface e pela linha de comando:
          - callback_inicio(idx, total, empresa): antes de processar cada empresa;
          - callback_progresso(idx, total, resultado): depois de cada empresa;
          - evento_parar: se sinalizado, encerra antes da próxima empresa.
        """
        resultados = []
        total = len(empresas)

        modo_txt = "CONFERÊNCIA DE VALORES" if apenas_conferir else "EMISSÃO EM LOTE"
        logger.info(f"Iniciando [{modo_txt}] de {total} empresas para a competência {competencia}...")

        for idx, emp in enumerate(empresas, start=1):
            if evento_parar is not None and evento_parar.is_set():
                logger.warning("Execução interrompida pelo usuário.")
                break

            cnpj = emp["cnpj"]
            razao = emp["razao_social"]
            comp_empresa = emp.get("competencia") or competencia
            fgts_esperado = float(emp.get("fgts_esperado", 0.0) or 0.0)

            if callback_inicio:
                try:
                    callback_inicio(idx, total, emp)
                except Exception:
                    pass

            logger.info(f"[{idx}/{total}] Processando {emp['cnpj_formatado']} - {razao} (FGTS Esperado: R$ {fgts_esperado:.2f})...")

            # Troca de perfil
            troca = self.trocar_perfil(cnpj)
            if not troca["sucesso"]:
                res = {
                    "cnpj": cnpj,
                    "cnpj_formatado": emp["cnpj_formatado"],
                    "razao_social": razao,
                    "competencia": comp_empresa,
                    "status": troca.get("status", "Erro de Procuração"),
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
                    templates_nomes=templates_nomes,
                    apenas_conferir=apenas_conferir,
                    exigir_valor_esperado=exigir_valor_esperado
                )

            resultados.append(res)

            if callback_progresso:
                try:
                    callback_progresso(idx, total, res)
                except Exception:
                    pass

            # Pequeno intervalo amigável entre requisições
            time.sleep(1.0)

        logger.info(f"Lote concluído: {len(resultados)} de {total} empresas processadas.")
        return resultados
