"""
Interface Gráfica Moderna Enterprise (CustomTkinter).
Painel de controle profissional para execução das automações do FGTS Digital em lote.
Arquitetura com Sidebar de navegação lateral, Cards de KPI executivos, Design Tokens
padronizados e tabelas de alta resolução.
"""

import os
import sys
import json
import queue
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from src.core.excel_manager import ExcelManager
from src.core.browser import BrowserManager
from src.modules.fgts_digital.bot import FGTSDigitalBot
from src.modules.fgts_digital.parser import calcular_competencia, limpar_cnpj, formatar_cnpj, validar_cnpj
from src.modules.folha_relatorio.parser_pdf import RelatorioFolhaParser
from src.utils.logger import logger, add_log_listener, remove_log_listener
from src.ui.theme import CORES, RAIO, FONTE_FAMILIA, FONTE_MONO
from config import settings

# Configuração de tema do CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class FGTSDigitalApp(ctk.CTk):
    """Janela principal profissional da aplicação de automação do FGTS Digital."""

    def __init__(self):
        super().__init__()

        self.title("Automação FGTS Digital Pro v2.0")
        self.geometry("1180x780")
        self.minsize(980, 580)

        # Variáveis de estado
        self.excel_path_var = tk.StringVar(value=str(settings.DEFAULT_EXCEL_PATH))
        self.output_dir_var = tk.StringVar(value=str(settings.DEFAULT_OUTPUT_DIR))
        self.headless_var = tk.BooleanVar(value=settings.HEADLESS)
        
        # Nomenclatura dos Documentos Baixados
        self.nome_guia_var = tk.StringVar(value="FGTS - Competencia")
        self.nome_rel_fgts_var = tk.StringVar(value="RE FGTS - Competencia")
        self.nome_rel_cons_var = tk.StringVar(value="Consignado FGTS - Competencia")

        # Parâmetros de Leitura de Relatório (PDF)
        self.param_fgts_mensal_var = tk.BooleanVar(value=True)
        self.param_emp_cred_trab_var = tk.BooleanVar(value=True)
        self.param_fgts_compl_var = tk.BooleanVar(value=True)
        self.param_emp_cred_tr_resc_var = tk.BooleanVar(value=False)
        self.param_simples_dom_var = tk.BooleanVar(value=False)

        # Emissão: exigir valor esperado da folha antes de emitir
        self.exigir_valor_esperado_var = tk.BooleanVar(value=True)

        # Carrega parâmetros persistidos em config/parametros.json
        self._carregar_parametros()

        # Competência
        self.comp_tipo_var = tk.StringVar(value="anterior")
        self.comp_manual_var = tk.StringVar()

        # Importação de Relatório de Folha (PDF)
        pdf_padrao = settings.DATA_DIR / "relatorio_encargos_exemplo.pdf"
        self.pdf_relatorio_path_var = tk.StringVar(value=str(pdf_padrao.resolve()) if pdf_padrao.exists() else "")
        self.empresas_folha_pdf: List[Dict[str, Any]] = []
        self.chk_todas_folha_var = tk.BooleanVar(value=True)
        self.travar_divergencia_var = tk.BooleanVar(value=True)
        self.apenas_conferir_var = tk.BooleanVar(value=False)

        self.is_running = False
        self.evento_parar = threading.Event()
        self.browser_manager = None
        self.empresas_carregadas: List[Dict[str, Any]] = []

        # Estado da navegação
        self.aba_ativa = "painel"
        self.botoes_nav: Dict[str, ctk.CTkButton] = {}
        self.frames_paineis: Dict[str, Any] = {}

        # Construção da Interface
        self._construir_layout_principal()

        # Fila única de tudo que outras threads querem mostrar na tela (logs e atualizações).
        # Só a thread principal toca no Tkinter: ela esvazia a fila a cada 50 ms.
        self._fila_ui: "queue.Queue" = queue.Queue()
        self._id_drenagem = self.after(50, self._drenar_fila_ui)

        # Conecta logs à interface
        add_log_listener(self._adicionar_log_interface)

        # Garante criação da planilha modelo e carrega dados
        if not Path(self.excel_path_var.get()).exists():
            try:
                ExcelManager.criar_planilha_modelo(Path(self.excel_path_var.get()))
            except Exception:
                pass

        self._carregar_e_exibir_empresas()
        self._atualizar_cards_kpi()

        # Se houver PDF de exemplo padrão, processa na inicialização
        if self.pdf_relatorio_path_var.get() and Path(self.pdf_relatorio_path_var.get()).exists():
            self.after(400, self._processar_pdf_folha)

    def _construir_layout_principal(self):
        """Monta o grid mestre: Sidebar lateral esquerda e Container de Conteúdo à direita."""
        self.grid_columnconfigure(0, weight=0)  # Sidebar fixa
        self.grid_columnconfigure(1, weight=1)  # Conteúdo responsivo
        self.grid_rowconfigure(0, weight=1)

        # ---------------------------------------------------------------------
        # 1. SIDEBAR LATERAL (Navegação & Branding)
        # ---------------------------------------------------------------------
        self.sidebar = ctk.CTkFrame(
            self,
            width=250,
            corner_radius=0,
            fg_color=(CORES["bg_sidebar_light"], CORES["bg_sidebar_dark"])
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(7, weight=1)  # Empurra o rodapé para o final

        # Branding
        brand_box = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_box.pack(fill="x", padx=18, pady=(20, 15))

        lbl_logo_icon = ctk.CTkLabel(
            brand_box,
            text="⚡ FGTS DIGITAL",
            font=ctk.CTkFont(family=FONTE_FAMILIA, size=18, weight="bold"),
            text_color="#38BDF8"
        )
        lbl_logo_icon.pack(anchor="w")

        lbl_logo_sub = ctk.CTkLabel(
            brand_box,
            text="Automação de Encargos Pro",
            font=ctk.CTkFont(family=FONTE_FAMILIA, size=11),
            text_color="#94A3B8"
        )
        lbl_logo_sub.pack(anchor="w", pady=(2, 0))

        # Divisor
        div_nav = ctk.CTkFrame(self.sidebar, height=1, fg_color="#334155")
        div_nav.pack(fill="x", padx=18, pady=(0, 15))

        # Itens de Navegação
        itens_menu = [
            ("painel", "⚙  Painel de Controle"),
            ("folha", "📑  Importar Relatório (PDF)"),
            ("empresas", "📋  Fila de Empresas"),
            ("parametros", "🛠  Parâmetros"),
            ("logs", "📜  Logs & Auditoria")
        ]

        self.nav_container = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.nav_container.pack(fill="x", padx=12, pady=0)

        for chave, rotulo in itens_menu:
            btn = ctk.CTkButton(
                self.nav_container,
                text=rotulo,
                anchor="w",
                font=ctk.CTkFont(family=FONTE_FAMILIA, size=13, weight="bold"),
                height=42,
                corner_radius=RAIO["md"],
                fg_color="transparent",
                text_color="#E2E8F0",
                hover_color=CORES["primary_hover"],
                command=lambda k=chave: self._navegar_para(k)
            )
            btn.pack(fill="x", pady=3)
            self.botoes_nav[chave] = btn

        # Rodapé da Sidebar
        footer_sidebar = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer_sidebar.pack(side="bottom", fill="x", padx=15, pady=20)

        lbl_tema = ctk.CTkLabel(
            footer_sidebar,
            text="Aparência do Sistema:",
            font=ctk.CTkFont(size=11),
            text_color="#94A3B8"
        )
        lbl_tema.pack(anchor="w", pady=(0, 4))

        self.opt_tema = ctk.CTkOptionMenu(
            footer_sidebar,
            values=["Dark", "Light", "System"],
            command=self._alterar_tema_aparencia,
            height=28,
            corner_radius=RAIO["sm"],
            fg_color="#334155",
            button_color="#475569"
        )
        self.opt_tema.set("Dark")
        self.opt_tema.pack(fill="x", pady=(0, 10))

        lbl_versao = ctk.CTkLabel(
            footer_sidebar,
            text="Versão 2.0.0 • mTLS & CDP",
            font=ctk.CTkFont(size=10),
            text_color="#64748B"
        )
        lbl_versao.pack(anchor="w")

        # ---------------------------------------------------------------------
        # 2. CONTAINER DE CONTEÚDO PRINCIPAL (Header, KPIs, Painéis)
        # ---------------------------------------------------------------------
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=15)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(2, weight=1)

        # 2.1 Header Superior Dinâmico
        self.header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.lbl_titulo_secao = ctk.CTkLabel(
            self.header_frame,
            text="⚙ Painel de Controle e Execução",
            font=ctk.CTkFont(family=FONTE_FAMILIA, size=22, weight="bold")
        )
        self.lbl_titulo_secao.grid(row=0, column=0, sticky="w")

        self.lbl_subtitulo_secao = ctk.CTkLabel(
            self.header_frame,
            text="Gerenciamento em lote de guias GFD (PIX) e relatórios via Procuração Eletrônica Gov.br",
            font=ctk.CTkFont(family=FONTE_FAMILIA, size=12),
            text_color="#94A3B8"
        )
        self.lbl_subtitulo_secao.grid(row=1, column=0, sticky="w")

        # 2.2 Faixa Executiva de CARDS DE KPI (3 Métricas Principais)
        self.kpi_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.kpi_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        for col in range(3):
            self.kpi_frame.grid_columnconfigure(col, weight=1, uniform="kpi")
        self.kpi_frame.grid_rowconfigure(0, weight=1)

        self.card_kpi_empresas = self._criar_card_kpi(
            parent=self.kpi_frame,
            coluna=0,
            icone="🏢",
            titulo="Empresas no Lote",
            valor="0 carregadas",
            destaque="Aguardando carga"
        )
        self.card_kpi_cert = self._criar_card_kpi(
            parent=self.kpi_frame,
            coluna=1,
            icone="🔒",
            titulo="Certificado Digital",
            valor="Certificado do Windows",
            destaque="Repositório nativo do Windows",
            cor_destaque="#22C55E"
        )
        self.card_kpi_trava = self._criar_card_kpi(
            parent=self.kpi_frame,
            coluna=2,
            icone="🛡",
            titulo="Auditoria de Valores",
            valor="Trava Ativa",
            destaque="Anti-Divergência",
            cor_destaque="#16A34A"
        )

        # 2.3 Containers dos Painéis de Conteúdo (Trocados pela Sidebar)
        self.panel_host = ctk.CTkFrame(self.main_container, corner_radius=RAIO["md"], fg_color="transparent")
        self.panel_host.grid(row=2, column=0, sticky="nsew")
        self.panel_host.grid_columnconfigure(0, weight=1)
        self.panel_host.grid_rowconfigure(0, weight=1)

        self.frame_painel = ctk.CTkScrollableFrame(
            self.panel_host,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color=("#CBD5E1", "#334155"),
            scrollbar_button_hover_color=("#94A3B8", "#475569")
        )
        self.frame_folha = ctk.CTkFrame(self.panel_host, fg_color="transparent")
        self.frame_empresas = ctk.CTkFrame(self.panel_host, fg_color="transparent")
        self.frame_parametros = ctk.CTkScrollableFrame(
            self.panel_host,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color=("#CBD5E1", "#334155"),
            scrollbar_button_hover_color=("#94A3B8", "#475569")
        )
        self.frame_logs = ctk.CTkFrame(self.panel_host, fg_color="transparent")

        self.frames_paineis = {
            "painel": self.frame_painel,
            "folha": self.frame_folha,
            "empresas": self.frame_empresas,
            "parametros": self.frame_parametros,
            "logs": self.frame_logs
        }

        self._construir_view_painel()
        self._construir_view_folha()
        self._construir_view_empresas()
        self._construir_view_parametros()
        self._construir_view_logs()

        # Ativa o painel inicial
        self._navegar_para("painel")

    # -------------------------------------------------------------------------
    # COMPONENTES REUTILIZÁVEIS: CARDS DE KPI
    # -------------------------------------------------------------------------

    def _criar_card_kpi(self, parent, coluna: int, icone: str, titulo: str, valor: str, destaque: str, cor_destaque: str = "#94A3B8") -> Dict[str, Any]:
        """Cria um cartão de métrica executivo com elevação suave e borda moderna."""
        card = ctk.CTkFrame(
            parent,
            corner_radius=RAIO["md"],
            fg_color=(CORES["card_light"], CORES["card_dark"]),
            border_width=1,
            border_color=(CORES["card_border_light"], CORES["card_border_dark"])
        )
        card.grid(row=0, column=coluna, padx=5, pady=0, sticky="nsew")

        top_line = ctk.CTkFrame(card, fg_color="transparent")
        top_line.pack(fill="x", padx=12, pady=(10, 2))

        lbl_ico = ctk.CTkLabel(top_line, text=icone, font=ctk.CTkFont(size=14))
        lbl_ico.pack(side="left", padx=(0, 6))

        lbl_tit = ctk.CTkLabel(
            top_line,
            text=titulo.upper(),
            font=ctk.CTkFont(family=FONTE_FAMILIA, size=10, weight="bold"),
            text_color="#94A3B8"
        )
        lbl_tit.pack(side="left")

        lbl_badge = ctk.CTkLabel(
            top_line,
            text="",
            font=ctk.CTkFont(family=FONTE_FAMILIA, size=10, weight="bold"),
            text_color="#F59E0B"
        )
        lbl_badge.pack(side="right")

        lbl_val = ctk.CTkLabel(
            card,
            text=valor,
            font=ctk.CTkFont(family=FONTE_FAMILIA, size=17, weight="bold"),
            anchor="w"
        )
        lbl_val.pack(fill="x", padx=14, pady=(2, 2))

        lbl_sub = ctk.CTkLabel(
            card,
            text=destaque,
            font=ctk.CTkFont(family=FONTE_FAMILIA, size=11),
            text_color=cor_destaque,
            anchor="w"
        )
        lbl_sub.pack(fill="x", padx=14, pady=(0, 10))

        return {"frame": card, "val": lbl_val, "sub": lbl_sub, "badge": lbl_badge}

    def _atualizar_cards_kpi(self):
        """Atualiza os valores dos 3 cartões executivos no topo da aplicação."""
        # Card 1: Empresas na Fila
        qtd = len(self.empresas_carregadas)
        validos = sum(1 for e in self.empresas_carregadas if e.get("valido", True))
        invalidos = qtd - validos

        if qtd == 0:
            self.card_kpi_empresas["val"].configure(text="0 Empresas")
            self.card_kpi_empresas["sub"].configure(text="Nenhuma na fila", text_color="#94A3B8")
        elif invalidos > 0:
            self.card_kpi_empresas["val"].configure(text=f"{qtd} Empresas")
            self.card_kpi_empresas["sub"].configure(text=f"{validos} válidas ({invalidos} inválidas)", text_color="#F59E0B")
        else:
            self.card_kpi_empresas["val"].configure(text=f"{qtd} Empresas")
            self.card_kpi_empresas["sub"].configure(text="Prontas na fila", text_color="#10B981")

        # Card 3: Trava de Divergência e Aviso de Modo Só Conferir
        if self.apenas_conferir_var.get():
            self.card_kpi_trava["badge"].configure(text="⚠ SÓ CONFERIR", text_color="#F59E0B")
            self.card_kpi_trava["val"].configure(text="Trava Ativa")
            self.card_kpi_trava["sub"].configure(
                text="Aviso: Apenas conferência (não emite guia)",
                text_color="#F59E0B"
            )
        elif self.travar_divergencia_var.get():
            self.card_kpi_trava["badge"].configure(text="")
            self.card_kpi_trava["val"].configure(text="Trava Ativa")
            self.card_kpi_trava["sub"].configure(
                text="Bloqueia guias divergentes",
                text_color="#16A34A"
            )
        else:
            self.card_kpi_trava["badge"].configure(text="")
            self.card_kpi_trava["val"].configure(text="Trava Desligada")
            self.card_kpi_trava["sub"].configure(
                text="Emissão sem conferência",
                text_color="#DC2626"
            )

    def _alternar_modo_conferencia(self):
        """Alterna os textos de status e ação entre emissão e conferência de valores."""
        if self.apenas_conferir_var.get():
            self.btn_iniciar.configure(
                text="🔍 Iniciar Conferência de Valores",
                fg_color=CORES["success"],
                hover_color=CORES["success_hover"]
            )
            self.lbl_progresso.configure(
                text="Modo Conferência ativo: O robô apenas consultará e comparará os valores do relatório com o FGTS Digital (sem emitir guia)."
            )
        else:
            self.btn_iniciar.configure(
                text="▶ Iniciar Automação",
                fg_color=CORES["success"],
                hover_color=CORES["success_hover"]
            )
            self.lbl_progresso.configure(
                text="Pronto para processar. Clique em Iniciar Automação."
            )
        self._atualizar_cards_kpi()

    # -------------------------------------------------------------------------
    # NAVEGAÇÃO DA SIDEBAR
    # -------------------------------------------------------------------------

    def _navegar_para(self, chave: str):
        """Alterna a exibição entre os painéis com realce de botão ativo."""
        self.aba_ativa = chave

        # Esconde todos os painéis e exibe o selecionado
        for k, frame in self.frames_paineis.items():
            if k == chave:
                frame.grid(row=0, column=0, sticky="nsew")
            else:
                frame.grid_forget()

        # Atualiza estilo dos botões da sidebar
        for k, btn in self.botoes_nav.items():
            if k == chave:
                btn.configure(
                    fg_color=CORES["primary"],
                    text_color="#FFFFFF"
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color="#E2E8F0"
                )

        # Atualiza título do Header Superior
        titulos = {
            "painel": ("⚙ Painel de Controle e Execução", "Competência, pasta de destino e acionamento do robô em lote"),
            "folha": ("📑 Importar Relatório (PDF)", "Extração automática, conferência do consignado e envio das empresas para o robô"),
            "empresas": ("📋 Fila de Empresas Carregadas", "Visualização dos CNPJs validados que serão processados na rodada atual"),
            "parametros": ("🛠 Parâmetros do Sistema", "Configurações de certificado digital, regras de leitura do PDF e nomenclatura de arquivos"),
            "logs": ("📜 Logs de Execução & Auditoria", "Monitoramento em tempo real do navegador, trocas de procuração e emissões")
        }
        tit, sub = titulos.get(chave, ("", ""))
        self.lbl_titulo_secao.configure(text=tit)
        self.lbl_subtitulo_secao.configure(text=sub)
        self._atualizar_cards_kpi()

    def _alterar_tema_aparencia(self, novo_tema: str):
        """Altera dinamicamente entre Dark, Light e System."""
        ctk.set_appearance_mode(novo_tema)

    # -------------------------------------------------------------------------
    # PAINEL 1: CONTROLE & EXECUÇÃO
    # -------------------------------------------------------------------------

    def _construir_view_painel(self):
        """Constrói o Painel de Controle com parâmetros da rodada e acionamento do robô."""
        self.frame_painel.grid_columnconfigure(0, weight=1)

        # Card 1: Parâmetros da Rodada e Competência
        card_params = ctk.CTkFrame(
            self.frame_painel,
            corner_radius=RAIO["md"],
            fg_color=(CORES["card_light"], CORES["card_dark"]),
            border_width=1,
            border_color=(CORES["card_border_light"], CORES["card_border_dark"])
        )
        card_params.grid(row=0, column=0, sticky="ew", pady=(0, 10), padx=(0, 6))
        card_params.grid_columnconfigure(1, weight=1)

        lbl_tit_params = ctk.CTkLabel(
            card_params,
            text="⚙ Parâmetros da Rodada",
            font=ctk.CTkFont(family=FONTE_FAMILIA, size=14, weight="bold")
        )
        lbl_tit_params.grid(row=0, column=0, columnspan=4, padx=15, pady=(12, 8), sticky="w")

        # Competência
        lbl_comp = ctk.CTkLabel(card_params, text="Competência FGTS:", font=ctk.CTkFont(size=12))
        lbl_comp.grid(row=1, column=0, padx=15, pady=6, sticky="w")

        comp_box = ctk.CTkFrame(card_params, fg_color="transparent")
        comp_box.grid(row=1, column=1, columnspan=3, padx=5, pady=6, sticky="w")

        comp_ant = calcular_competencia("anterior")
        comp_atual = calcular_competencia("atual")

        rb_ant = ctk.CTkRadioButton(comp_box, text=f"Anterior (Padrão: {comp_ant})", variable=self.comp_tipo_var, value="anterior", command=self._ao_alterar_competencia)
        rb_ant.pack(side="left", padx=(0, 10))

        rb_atual = ctk.CTkRadioButton(comp_box, text=f"Atual ({comp_atual})", variable=self.comp_tipo_var, value="atual", command=self._ao_alterar_competencia)
        rb_atual.pack(side="left", padx=10)

        rb_manual = ctk.CTkRadioButton(comp_box, text="Manual:", variable=self.comp_tipo_var, value="manual", command=self._ao_alterar_competencia)
        rb_manual.pack(side="left", padx=(10, 4))

        self.entry_comp_manual = ctk.CTkEntry(comp_box, textvariable=self.comp_manual_var, width=80, placeholder_text="09/2026")
        self.entry_comp_manual.pack(side="left")

        # Pasta onde salvar os arquivos emitidos
        lbl_out = ctk.CTkLabel(card_params, text="Salvar Arquivos em:", font=ctk.CTkFont(size=12))
        lbl_out.grid(row=2, column=0, padx=15, pady=6, sticky="w")

        entry_out = ctk.CTkEntry(card_params, textvariable=self.output_dir_var)
        entry_out.grid(row=2, column=1, padx=5, pady=6, sticky="ew")

        btn_buscar_out = ctk.CTkButton(card_params, text="Alterar...", width=80, command=self._selecionar_output)
        btn_buscar_out.grid(row=2, column=2, padx=(5, 15), pady=6)

        # Opções Switches
        switches_box = ctk.CTkFrame(card_params, fg_color="transparent")
        switches_box.grid(row=3, column=0, columnspan=3, padx=15, pady=(8, 12), sticky="w")

        self.sw_trava = ctk.CTkSwitch(
            switches_box,
            text="Bloquear emissão em caso de divergência de valores com a folha (Recomendado)",
            variable=self.travar_divergencia_var,
            font=ctk.CTkFont(weight="bold"),
            command=self._atualizar_cards_kpi
        )
        self.sw_trava.pack(anchor="w", pady=3)

        self.sw_exigir_valor = ctk.CTkSwitch(
            switches_box,
            text="Exigir valor esperado da folha para emitir a guia (Recomendado)",
            variable=self.exigir_valor_esperado_var,
            font=ctk.CTkFont(weight="bold"),
            command=self._salvar_parametros_silencioso
        )
        self.sw_exigir_valor.pack(anchor="w", pady=3)

        self.sw_headless = ctk.CTkSwitch(
            switches_box,
            text="Executar em segundo plano (Ocultar janelas secundárias)",
            variable=self.headless_var
        )
        self.sw_headless.pack(anchor="w", pady=3)

        self.sw_apenas_conferir = ctk.CTkSwitch(
            switches_box,
            text="Apenas conferir se os valores do relatório e FGTS Digital são iguais (Sem emitir guia)",
            variable=self.apenas_conferir_var,
            font=ctk.CTkFont(weight="bold"),
            command=self._alternar_modo_conferencia
        )
        self.sw_apenas_conferir.pack(anchor="w", pady=3)

        # Card 2: Ação Central de Disparo e Progresso
        card_action = ctk.CTkFrame(
            self.frame_painel,
            corner_radius=RAIO["md"],
            fg_color=(CORES["card_light"], CORES["card_dark"]),
            border_width=1,
            border_color=(CORES["card_border_light"], CORES["card_border_dark"])
        )
        card_action.grid(row=1, column=0, sticky="ew", pady=(0, 20), padx=(0, 6))
        card_action.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(card_action, height=12, corner_radius=6)
        self.progress_bar.grid(row=0, column=0, columnspan=2, padx=20, pady=(15, 6), sticky="ew")
        self.progress_bar.set(0)

        self.lbl_progresso = ctk.CTkLabel(
            card_action,
            text="Pronto para processar. Clique em Iniciar Automação.",
            font=ctk.CTkFont(size=12),
            text_color="#94A3B8"
        )
        self.lbl_progresso.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="w")

        btn_box = ctk.CTkFrame(card_action, fg_color="transparent")
        btn_box.grid(row=1, column=1, padx=20, pady=(0, 15), sticky="e")

        self.btn_abrir_pasta = ctk.CTkButton(
            btn_box,
            text="📁 Abrir Pasta",
            width=110,
            fg_color="#334155",
            hover_color="#475569",
            command=self._abrir_pasta_saida
        )
        self.btn_abrir_pasta.pack(side="left", padx=5)

        self.btn_iniciar = ctk.CTkButton(
            btn_box,
            text="▶ Iniciar Automação",
            height=38,
            font=ctk.CTkFont(family=FONTE_FAMILIA, size=14, weight="bold"),
            fg_color=CORES["success"],
            hover_color=CORES["success_hover"],
            command=self._iniciar_execucao
        )
        self.btn_iniciar.pack(side="left", padx=5)

    # -------------------------------------------------------------------------
    # PAINEL 2: IMPORTADOR & EDITOR DE FOLHA (PDF)
    # -------------------------------------------------------------------------

    def _construir_view_folha(self):
        """Constrói a interface moderna para leitura de folha com tabela editável."""
        self.frame_folha.grid_columnconfigure(0, weight=1)
        self.frame_folha.grid_rowconfigure(1, weight=1)

        # 1. Barra de Seleção e Ação no Topo
        top_card = ctk.CTkFrame(
            self.frame_folha,
            corner_radius=RAIO["md"],
            fg_color=(CORES["card_light"], CORES["card_dark"]),
            border_width=1,
            border_color=(CORES["card_border_light"], CORES["card_border_dark"])
        )
        top_card.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        top_card.grid_columnconfigure(1, weight=1)

        lbl_pdf_tit = ctk.CTkLabel(top_card, text="Relatório PDF:", font=ctk.CTkFont(weight="bold"))
        lbl_pdf_tit.grid(row=0, column=0, padx=15, pady=10, sticky="w")

        entry_pdf = ctk.CTkEntry(top_card, textvariable=self.pdf_relatorio_path_var, placeholder_text="Selecione o arquivo PDF de pagamento de encargos...")
        entry_pdf.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        btn_buscar_pdf = ctk.CTkButton(top_card, text="Buscar PDF...", width=90, command=self._selecionar_pdf_folha)
        btn_buscar_pdf.grid(row=0, column=2, padx=5, pady=10)

        btn_ler_pdf = ctk.CTkButton(
            top_card,
            text="⚡ Ler e Processar",
            width=120,
            fg_color=CORES["warning"],
            hover_color=CORES["warning_hover"],
            font=ctk.CTkFont(weight="bold"),
            command=self._processar_pdf_folha
        )
        btn_ler_pdf.grid(row=0, column=3, padx=15, pady=10)

        self.lbl_resumo_folha = ctk.CTkLabel(
            top_card,
            text="Nenhum relatório PDF processado.",
            font=ctk.CTkFont(size=12),
            text_color="#94A3B8"
        )
        self.lbl_resumo_folha.grid(row=1, column=0, columnspan=4, padx=15, pady=(0, 8), sticky="w")

        # 2. Container Rolável da Tabela
        self.frame_tabela_folha = ctk.CTkScrollableFrame(
            self.frame_folha,
            corner_radius=RAIO["md"],
            fg_color=(CORES["card_light"], CORES["card_dark"]),
            border_width=1,
            border_color=(CORES["card_border_light"], CORES["card_border_dark"])
        )
        self.frame_tabela_folha.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

        # 3. Barra Inferior de Ações
        bottom_bar = ctk.CTkFrame(
            self.frame_folha,
            corner_radius=RAIO["md"],
            fg_color=(CORES["card_light"], CORES["card_dark"]),
            border_width=1,
            border_color=(CORES["card_border_light"], CORES["card_border_dark"])
        )
        bottom_bar.grid(row=2, column=0, sticky="ew")

        botoes_box = ctk.CTkFrame(bottom_bar, fg_color="transparent")
        botoes_box.pack(fill="x", padx=12, pady=8)

        btn_enviar = ctk.CTkButton(
            botoes_box,
            text="⚡ Enviar Selecionadas para o Robô",
            fg_color=CORES["success"],
            hover_color=CORES["success_hover"],
            font=ctk.CTkFont(weight="bold"),
            command=self._enviar_folha_para_robo
        )
        btn_enviar.pack(side="left", padx=5)

        btn_excel = ctk.CTkButton(
            botoes_box,
            text="📥 Salvar em Excel (.xlsx)",
            fg_color=CORES["primary"],
            hover_color=CORES["primary_hover"],
            command=self._salvar_folha_excel
        )
        btn_excel.pack(side="left", padx=5)

        btn_pdf = ctk.CTkButton(
            botoes_box,
            text="📄 Exportar Resumo em PDF",
            fg_color="#475569",
            hover_color="#334155",
            command=self._exportar_folha_pdf
        )
        btn_pdf.pack(side="left", padx=5)

        btn_limpar_dados = ctk.CTkButton(
            botoes_box,
            text="🗑 Limpar Dados",
            fg_color="#DC2626",
            hover_color="#B91C1C",
            command=self._limpar_dados_folha_pdf
        )
        btn_limpar_dados.pack(side="left", padx=5)

    def _renderizar_tabela_folha(self):
        """Renderiza as linhas da tabela de folha com visual executivo e inputs editáveis."""
        for w in self.frame_tabela_folha.winfo_children():
            w.destroy()

        self.widgets_folha_linhas = []
        if not self.empresas_folha_pdf:
            lbl_vazio = ctk.CTkLabel(
                self.frame_tabela_folha,
                text="Nenhum dado para exibir. Carregue um arquivo PDF de encargos da folha.",
                font=ctk.CTkFont(size=13),
                text_color="#94A3B8"
            )
            lbl_vazio.pack(pady=40)
            return

        # Cabeçalho da Tabela
        header_linha = ctk.CTkFrame(self.frame_tabela_folha, fg_color=("#E2E8F0", "#0F172A"), corner_radius=6)
        header_linha.pack(fill="x", padx=4, pady=(2, 6))
        header_linha.grid_columnconfigure(2, weight=1)

        chk_todas = ctk.CTkCheckBox(
            header_linha,
            text="",
            width=22,
            variable=self.chk_todas_folha_var,
            command=self._alternar_selecao_todas_folha
        )
        chk_todas.grid(row=0, column=0, padx=6, pady=5)

        lbl_h_doc = ctk.CTkLabel(header_linha, text="CNPJ / CPF", width=150, font=ctk.CTkFont(weight="bold"), anchor="w")
        lbl_h_doc.grid(row=0, column=1, padx=4, pady=5)

        lbl_h_razao = ctk.CTkLabel(header_linha, text="Razão Social / Nome", font=ctk.CTkFont(weight="bold"), anchor="w")
        lbl_h_razao.grid(row=0, column=2, padx=4, pady=5, sticky="ew")

        lbl_h_comp = ctk.CTkLabel(header_linha, text="Comp.", width=70, font=ctk.CTkFont(weight="bold"), anchor="center")
        lbl_h_comp.grid(row=0, column=3, padx=4, pady=5)

        lbl_h_mensal = ctk.CTkLabel(header_linha, text="Mensal (R$)", width=100, font=ctk.CTkFont(weight="bold"), anchor="e")
        lbl_h_mensal.grid(row=0, column=4, padx=4, pady=5)

        lbl_h_consig = ctk.CTkLabel(header_linha, text="Consignado (R$)", width=105, font=ctk.CTkFont(weight="bold"), anchor="e")
        lbl_h_consig.grid(row=0, column=5, padx=4, pady=5)

        lbl_h_total = ctk.CTkLabel(header_linha, text="Guia FGTS (R$)", width=115, font=ctk.CTkFont(weight="bold"), anchor="e")
        lbl_h_total.grid(row=0, column=6, padx=4, pady=5)

        lbl_h_resc = ctk.CTkLabel(header_linha, text="Rescisório (R$)", width=100, font=ctk.CTkFont(weight="bold"), anchor="e")
        lbl_h_resc.grid(row=0, column=7, padx=6, pady=5)

        # Linhas de Dados
        for idx, emp in enumerate(self.empresas_folha_pdf):
            bg_cor = ("#F8FAFC", "#1E293B") if idx % 2 == 0 else ("#FFFFFF", "#0F172A")
            linha = ctk.CTkFrame(self.frame_tabela_folha, fg_color=bg_cor, corner_radius=4)
            linha.pack(fill="x", padx=4, pady=2)
            linha.grid_columnconfigure(2, weight=1)

            # Checkbox
            chk_var = tk.BooleanVar(value=emp.get("selecionado", True))
            chk = ctk.CTkCheckBox(linha, text="", width=22, variable=chk_var)
            chk.grid(row=0, column=0, padx=6, pady=4)

            # Documento
            entry_doc = ctk.CTkEntry(linha, width=150, font=ctk.CTkFont(family=FONTE_MONO, size=11))
            entry_doc.insert(0, emp["documento"])
            entry_doc.grid(row=0, column=1, padx=4, pady=4)

            # Razão Social
            entry_razao = ctk.CTkEntry(linha)
            entry_razao.insert(0, emp["razao_social"])
            entry_razao.grid(row=0, column=2, padx=4, pady=4, sticky="ew")

            # Competência
            entry_comp = ctk.CTkEntry(linha, width=70, justify="center")
            entry_comp.insert(0, emp["competencia"])
            entry_comp.grid(row=0, column=3, padx=4, pady=4)

            # FGTS Mensal
            entry_mensal = ctk.CTkEntry(linha, width=100, justify="right")
            entry_mensal.insert(0, f"{emp['fgts_mensal']:.2f}")
            entry_mensal.grid(row=0, column=4, padx=4, pady=4)

            # Consignado
            entry_consig = ctk.CTkEntry(linha, width=105, justify="right")
            entry_consig.insert(0, f"{emp.get('consignado', 0.0):.2f}")
            entry_consig.grid(row=0, column=5, padx=4, pady=4)

            # Guia FGTS (Mensal + Consignado)
            lbl_tot = ctk.CTkLabel(
                linha,
                text=f"R$ {emp['total_fgts']:,.2f}",
                width=115,
                font=ctk.CTkFont(weight="bold"),
                anchor="e",
                text_color="#38BDF8"
            )
            lbl_tot.grid(row=0, column=6, padx=4, pady=4)

            # Rescisório
            entry_resc = ctk.CTkEntry(linha, width=100, justify="right")
            entry_resc.insert(0, f"{emp['fgts_rescisorio']:.2f}")
            entry_resc.grid(row=0, column=7, padx=6, pady=4)

            self.widgets_folha_linhas.append({
                "chk_var": chk_var,
                "entry_doc": entry_doc,
                "entry_razao": entry_razao,
                "entry_comp": entry_comp,
                "entry_mensal": entry_mensal,
                "entry_consignado": entry_consig,
                "entry_rescisorio": entry_resc,
                "lbl_total": lbl_tot,
                "emp_original": emp
            })

    # -------------------------------------------------------------------------
    # PAINEL 3: FILA DE EMPRESAS IMPORTADAS
    # -------------------------------------------------------------------------

    def _construir_view_empresas(self):
        """Constrói a visualização dos CNPJs carregados na planilha de trabalho."""
        self.frame_empresas.grid_columnconfigure(0, weight=1)
        self.frame_empresas.grid_rowconfigure(1, weight=1)

        top_bar = ctk.CTkFrame(
            self.frame_empresas,
            corner_radius=RAIO["md"],
            fg_color=(CORES["card_light"], CORES["card_dark"]),
            border_width=1,
            border_color=(CORES["card_border_light"], CORES["card_border_dark"])
        )
        top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        top_bar.grid_columnconfigure(0, weight=1)

        self.lbl_resumo_empresas = ctk.CTkLabel(
            top_bar,
            text="Nenhuma empresa carregada.",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.lbl_resumo_empresas.grid(row=0, column=0, padx=15, pady=10, sticky="w")

        btn_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        btn_box.grid(row=0, column=1, padx=15, pady=10, sticky="e")

        btn_recarregar = ctk.CTkButton(
            btn_box,
            text="🔄 Recarregar",
            width=110,
            command=self._carregar_e_exibir_empresas
        )
        btn_recarregar.pack(side="left", padx=5)

        btn_abrir_excel = ctk.CTkButton(
            btn_box,
            text="Abrir Planilha",
            width=110,
            fg_color="#334155",
            hover_color="#475569",
            command=self._abrir_planilha_no_excel
        )
        btn_abrir_excel.pack(side="left", padx=5)

        btn_limpar_fila = ctk.CTkButton(
            btn_box,
            text="🗑 Limpar Fila",
            width=100,
            fg_color="#DC2626",
            hover_color="#B91C1C",
            command=self._limpar_fila_empresas
        )
        btn_limpar_fila.pack(side="left", padx=5)

        self.frame_tabela = ctk.CTkScrollableFrame(
            self.frame_empresas,
            corner_radius=RAIO["md"],
            fg_color=(CORES["card_light"], CORES["card_dark"]),
            border_width=1,
            border_color=(CORES["card_border_light"], CORES["card_border_dark"])
        )
        self.frame_tabela.grid(row=1, column=0, sticky="nsew")
        self.frame_tabela.grid_columnconfigure(1, weight=1)

    # -------------------------------------------------------------------------
    # PAINEL 4: TERMINAL DE LOGS & AUDITORIA
    # -------------------------------------------------------------------------

    def _construir_view_logs(self):
        """Constrói console no estilo Terminal Corporativo com autoscroll."""
        self.frame_logs.grid_columnconfigure(0, weight=1)
        self.frame_logs.grid_rowconfigure(1, weight=1)

        header_logs = ctk.CTkFrame(
            self.frame_logs,
            corner_radius=RAIO["md"],
            fg_color=(CORES["card_light"], CORES["card_dark"]),
            border_width=1,
            border_color=(CORES["card_border_light"], CORES["card_border_dark"])
        )
        header_logs.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header_logs.grid_columnconfigure(0, weight=1)

        lbl_log_tit = ctk.CTkLabel(
            header_logs,
            text="💻 Console de Eventos do Sistema",
            font=ctk.CTkFont(family=FONTE_FAMILIA, size=13, weight="bold")
        )
        lbl_log_tit.grid(row=0, column=0, padx=15, pady=8, sticky="w")

        btn_limpar = ctk.CTkButton(
            header_logs,
            text="Limpar Console",
            width=110,
            fg_color="#334155",
            hover_color="#475569",
            command=self._limpar_logs
        )
        btn_limpar.grid(row=0, column=1, padx=15, pady=8, sticky="e")

        self.txt_logs = ctk.CTkTextbox(
            self.frame_logs,
            font=ctk.CTkFont(family=FONTE_MONO, size=11),
            fg_color=CORES["terminal_bg"],
            text_color=CORES["terminal_text"],
            corner_radius=RAIO["md"],
            wrap="word"
        )
        self.txt_logs.grid(row=1, column=0, sticky="nsew")

    # -------------------------------------------------------------------------
    # PAINEL 5: PARÂMETROS DO SISTEMA
    # -------------------------------------------------------------------------

    def _construir_view_parametros(self):
        """Constrói o painel de Parâmetros do Sistema (certificado, leitura de PDF e nomenclatura)."""
        self.frame_parametros.grid_columnconfigure(0, weight=1)

        # Card 1: Certificado Digital
        card_cert = ctk.CTkFrame(
            self.frame_parametros,
            corner_radius=RAIO["md"],
            fg_color=(CORES["card_light"], CORES["card_dark"]),
            border_width=1,
            border_color=(CORES["card_border_light"], CORES["card_border_dark"])
        )
        card_cert.grid(row=0, column=0, sticky="ew", pady=(0, 15), padx=(0, 6))
        card_cert.grid_columnconfigure(1, weight=1)

        lbl_tit_cert = ctk.CTkLabel(
            card_cert,
            text="🔒 Certificado Digital",
            font=ctk.CTkFont(family=FONTE_FAMILIA, size=14, weight="bold")
        )
        lbl_tit_cert.grid(row=0, column=0, columnspan=3, padx=15, pady=(12, 6), sticky="w")

        # Somente certificado instalado no Windows: o modo arquivo .PFX foi removido
        # porque quebra o captcha do Gov.br (ver docs/decisoes/ADR-0004).
        self.frame_cert_win_aviso = ctk.CTkFrame(card_cert, fg_color=("#ECFDF5", "#064E3B"), corner_radius=6)
        self.frame_cert_win_aviso.grid(row=1, column=0, columnspan=3, padx=15, pady=(0, 12), sticky="ew")

        lbl_win_desc = ctk.CTkLabel(
            self.frame_cert_win_aviso,
            text="✔ O robô utilizará diretamente o certificado digital A1/A3 já instalado no Windows. Nenhuma senha ou arquivo é necessário.",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#065F46", "#34D399")
        )
        lbl_win_desc.pack(padx=12, pady=8, anchor="w")

        # Card 2: Regras de Leitura do Relatório de Encargos (PDF)
        card_regras = ctk.CTkFrame(
            self.frame_parametros,
            corner_radius=RAIO["md"],
            fg_color=(CORES["card_light"], CORES["card_dark"]),
            border_width=1,
            border_color=(CORES["card_border_light"], CORES["card_border_dark"])
        )
        card_regras.grid(row=1, column=0, sticky="ew", pady=(0, 15), padx=(0, 6))
        card_regras.grid_columnconfigure(0, weight=1)

        lbl_tit_regras = ctk.CTkLabel(
            card_regras,
            text="📑 Regras de Leitura do Relatório de Encargos (PDF)",
            font=ctk.CTkFont(family=FONTE_FAMILIA, size=14, weight="bold")
        )
        lbl_tit_regras.pack(anchor="w", padx=15, pady=(12, 4))

        lbl_desc_regras = ctk.CTkLabel(
            card_regras,
            text="Selecione quais encargos listados no relatório em PDF compõem o total esperado do FGTS Digital:",
            font=ctk.CTkFont(size=12),
            text_color="#94A3B8"
        )
        lbl_desc_regras.pack(anchor="w", padx=15, pady=(0, 10))

        # Checkbox 1: FGTS Mensal
        chk_fgts = ctk.CTkCheckBox(
            card_regras,
            text="FGTS (Mensal Regular) — Valor base do FGTS mensal da competência (Cód. 115/150)",
            variable=self.param_fgts_mensal_var,
            font=ctk.CTkFont(weight="bold")
        )
        chk_fgts.pack(anchor="w", padx=20, pady=5)

        # Checkbox 2: Emp. Créd. Trab.
        chk_cred_trab = ctk.CTkCheckBox(
            card_regras,
            text="Emp. Créd. Trab. (Empréstimo Consignado dos Trabalhadores Ativos) — Recolhido na Guia Mensal",
            variable=self.param_emp_cred_trab_var,
            font=ctk.CTkFont(weight="bold")
        )
        chk_cred_trab.pack(anchor="w", padx=20, pady=5)

        # Checkbox 3: FGTS Compl.
        chk_compl = ctk.CTkCheckBox(
            card_regras,
            text="FGTS Compl. / Complementar — Folhas complementares ou diferenças salariais",
            variable=self.param_fgts_compl_var,
            font=ctk.CTkFont(weight="bold")
        )
        chk_compl.pack(anchor="w", padx=20, pady=5)

        # Divisor suave
        div1 = ctk.CTkFrame(card_regras, height=1, fg_color="#334155")
        div1.pack(fill="x", padx=20, pady=8)

        lbl_opc = ctk.CTkLabel(
            card_regras,
            text="Encargos Adicionais / Casos Específicos (Desmarcados por padrão):",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#CBD5E1"
        )
        lbl_opc.pack(anchor="w", padx=20, pady=(0, 4))

        # Checkbox 4: Emp. Créd. Tr. Resc.
        chk_cred_resc = ctk.CTkCheckBox(
            card_regras,
            text="Emp. Créd. Tr. Resc. (Consignado de Rescisão) — Marcar apenas se for recolhido junto",
            variable=self.param_emp_cred_tr_resc_var
        )
        chk_cred_resc.pack(anchor="w", padx=20, pady=5)

        # Checkbox 5: Simples Doméstico
        chk_domestico = ctk.CTkCheckBox(
            card_regras,
            text="Simples Doméstico — Guias específicas de empregador doméstico",
            variable=self.param_simples_dom_var
        )
        chk_domestico.pack(anchor="w", padx=20, pady=(5, 14))

        # Card 3: Nomenclatura dos Documentos Emitidos
        card_nomes = ctk.CTkFrame(
            self.frame_parametros,
            corner_radius=RAIO["md"],
            fg_color=(CORES["card_light"], CORES["card_dark"]),
            border_width=1,
            border_color=(CORES["card_border_light"], CORES["card_border_dark"])
        )
        card_nomes.grid(row=2, column=0, sticky="ew", pady=(0, 15), padx=(0, 6))
        card_nomes.grid_columnconfigure(1, weight=1)

        lbl_tit_nomes = ctk.CTkLabel(
            card_nomes,
            text="🏷 Nomenclatura dos Documentos Emitidos",
            font=ctk.CTkFont(family=FONTE_FAMILIA, size=14, weight="bold")
        )
        lbl_tit_nomes.grid(row=0, column=0, columnspan=3, padx=15, pady=(12, 4), sticky="w")

        lbl_desc_nomes = ctk.CTkLabel(
            card_nomes,
            text="Personalize como os arquivos PDF serão nomeados ao serem baixados do FGTS Digital:",
            font=ctk.CTkFont(size=12),
            text_color="#94A3B8"
        )
        lbl_desc_nomes.grid(row=1, column=0, columnspan=3, padx=15, pady=(0, 10), sticky="w")

        lbl_n_guia = ctk.CTkLabel(card_nomes, text="Guia FGTS (GFD):", font=ctk.CTkFont(size=12))
        lbl_n_guia.grid(row=2, column=0, padx=15, pady=4, sticky="w")
        entry_n_guia = ctk.CTkEntry(card_nomes, textvariable=self.nome_guia_var, placeholder_text="FGTS - Competencia")
        entry_n_guia.grid(row=2, column=1, padx=5, pady=4, sticky="ew")

        lbl_n_rfgts = ctk.CTkLabel(card_nomes, text="Relatório FGTS:", font=ctk.CTkFont(size=12))
        lbl_n_rfgts.grid(row=3, column=0, padx=15, pady=4, sticky="w")
        entry_n_rfgts = ctk.CTkEntry(card_nomes, textvariable=self.nome_rel_fgts_var, placeholder_text="RE FGTS - Competencia")
        entry_n_rfgts.grid(row=3, column=1, padx=5, pady=4, sticky="ew")

        lbl_n_rcons = ctk.CTkLabel(card_nomes, text="Relatório Consignado:", font=ctk.CTkFont(size=12))
        lbl_n_rcons.grid(row=4, column=0, padx=15, pady=4, sticky="w")
        entry_n_rcons = ctk.CTkEntry(card_nomes, textvariable=self.nome_rel_cons_var, placeholder_text="Consignado FGTS - Competencia")
        entry_n_rcons.grid(row=4, column=1, padx=5, pady=4, sticky="ew")

        # Presets de nomes
        preset_box = ctk.CTkFrame(card_nomes, fg_color="transparent")
        preset_box.grid(row=2, column=2, rowspan=3, padx=15, pady=4, sticky="ns")

        btn_pre_padrao = ctk.CTkButton(
            preset_box,
            text="Padrão",
            width=110,
            height=26,
            fg_color="#334155",
            hover_color="#475569",
            command=lambda: self._aplicar_preset_nomes("padrao")
        )
        btn_pre_padrao.pack(pady=2)

        btn_pre_emp = ctk.CTkButton(
            preset_box,
            text="+ Empresa",
            width=110,
            height=26,
            fg_color="#334155",
            hover_color="#475569",
            command=lambda: self._aplicar_preset_nomes("empresa")
        )
        btn_pre_emp.pack(pady=2)

        btn_pre_cnpj = ctk.CTkButton(
            preset_box,
            text="+ CNPJ",
            width=110,
            height=26,
            fg_color="#334155",
            hover_color="#475569",
            command=lambda: self._aplicar_preset_nomes("cnpj")
        )
        btn_pre_cnpj.pack(pady=2)

        lbl_dica = ctk.CTkLabel(
            card_nomes,
            text="💡 Dica: Variáveis aceitas: Competencia (ex: 09-2026), CNPJ, Empresa",
            font=ctk.CTkFont(size=11),
            text_color="#94A3B8"
        )
        lbl_dica.grid(row=5, column=0, columnspan=3, padx=15, pady=(4, 12), sticky="w")

        # Card 4: Barra de Ação (Salvar / Restaurar)
        card_acoes = ctk.CTkFrame(
            self.frame_parametros,
            corner_radius=RAIO["md"],
            fg_color=(CORES["card_light"], CORES["card_dark"]),
            border_width=1,
            border_color=(CORES["card_border_light"], CORES["card_border_dark"])
        )
        card_acoes.grid(row=3, column=0, sticky="ew", pady=(0, 20), padx=(0, 6))
        card_acoes.grid_columnconfigure(0, weight=1)

        box_botoes_salvar = ctk.CTkFrame(card_acoes, fg_color="transparent")
        box_botoes_salvar.pack(fill="x", padx=15, pady=12)

        self.lbl_status_parametros = ctk.CTkLabel(
            box_botoes_salvar,
            text="Os parâmetros são persistidos automaticamente em config/parametros.json.",
            font=ctk.CTkFont(size=12),
            text_color="#94A3B8"
        )
        self.lbl_status_parametros.pack(side="left")

        btn_restaurar = ctk.CTkButton(
            box_botoes_salvar,
            text="🔄 Restaurar Padrões",
            width=140,
            fg_color="#334155",
            hover_color="#475569",
            command=self._restaurar_parametros_padrao
        )
        btn_restaurar.pack(side="right", padx=(5, 0))

        btn_salvar = ctk.CTkButton(
            box_botoes_salvar,
            text="💾 Salvar Parâmetros",
            width=160,
            height=36,
            font=ctk.CTkFont(weight="bold"),
            fg_color=CORES["success"],
            hover_color=CORES["success_hover"],
            command=self._salvar_parametros
        )
        btn_salvar.pack(side="right", padx=(0, 5))

    def _carregar_parametros(self):
        """Carrega os parâmetros de config/parametros.json para as variáveis de estado."""
        cfg_path = settings.PARAMETROS_PATH
        if not cfg_path.exists():
            return
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                dados = json.load(f)

            regras = dados.get("regras_leitura_pdf", {})
            if "fgts_mensal" in regras:
                self.param_fgts_mensal_var.set(bool(regras["fgts_mensal"]))
            if "emp_cred_trab" in regras:
                self.param_emp_cred_trab_var.set(bool(regras["emp_cred_trab"]))
            if "fgts_compl" in regras:
                self.param_fgts_compl_var.set(bool(regras["fgts_compl"]))
            if "emp_cred_tr_resc" in regras:
                self.param_emp_cred_tr_resc_var.set(bool(regras["emp_cred_tr_resc"]))
            if "simples_dom" in regras:
                self.param_simples_dom_var.set(bool(regras["simples_dom"]))

            nomes = dados.get("nomenclatura", {})
            if "guia" in nomes:
                self.nome_guia_var.set(str(nomes["guia"]))
            if "relatorio_fgts" in nomes:
                self.nome_rel_fgts_var.set(str(nomes["relatorio_fgts"]))
            if "relatorio_consignado" in nomes:
                self.nome_rel_cons_var.set(str(nomes["relatorio_consignado"]))

            pastas = dados.get("pastas", {})
            if "output_dir" in pastas:
                self.output_dir_var.set(str(pastas["output_dir"]))

            emissao = dados.get("emissao", {})
            if "exigir_valor_esperado" in emissao:
                self.exigir_valor_esperado_var.set(bool(emissao["exigir_valor_esperado"]))
        except Exception as e:
            logger.warning(f"Não foi possível carregar config/parametros.json: {e}")

    def _montar_dados_parametros(self) -> Dict[str, Any]:
        return {
            "regras_leitura_pdf": {
                "fgts_mensal": self.param_fgts_mensal_var.get(),
                "emp_cred_trab": self.param_emp_cred_trab_var.get(),
                "fgts_compl": self.param_fgts_compl_var.get(),
                "emp_cred_tr_resc": self.param_emp_cred_tr_resc_var.get(),
                "simples_dom": self.param_simples_dom_var.get()
            },
            "nomenclatura": {
                "guia": self.nome_guia_var.get().strip(),
                "relatorio_fgts": self.nome_rel_fgts_var.get().strip(),
                "relatorio_consignado": self.nome_rel_cons_var.get().strip()
            },
            "pastas": {
                "output_dir": self.output_dir_var.get().strip()
            },
            "emissao": {
                "exigir_valor_esperado": self.exigir_valor_esperado_var.get()
            }
        }

    def _salvar_parametros_silencioso(self):
        """Persiste os parâmetros sem diálogos (usado pelos switches do painel)."""
        try:
            with open(settings.PARAMETROS_PATH, "w", encoding="utf-8") as f:
                json.dump(self._montar_dados_parametros(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Não foi possível salvar config/parametros.json: {e}")

    def _salvar_parametros(self):
        """Persiste os parâmetros em config/parametros.json e reaplica regras."""
        cfg_path = settings.PARAMETROS_PATH
        dados = self._montar_dados_parametros()
        try:
            cfg_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
            logger.info("Parâmetros do sistema salvos com sucesso em config/parametros.json.")

            if hasattr(self, "lbl_status_parametros"):
                self.lbl_status_parametros.configure(
                    text="✔ Parâmetros salvos com sucesso em config/parametros.json!",
                    text_color="#22C55E"
                )

            # Se já houver PDF carregado, reprocessa imediatamente para atualizar os cálculos
            if self.pdf_relatorio_path_var.get() and Path(self.pdf_relatorio_path_var.get()).exists():
                self._processar_pdf_folha()

            messagebox.showinfo("Parâmetros Salvos", "Parâmetros configurados e salvos com sucesso!")
        except Exception as e:
            logger.error(f"Erro ao salvar parametros.json: {e}")
            if hasattr(self, "lbl_status_parametros"):
                self.lbl_status_parametros.configure(
                    text=f"✖ Erro ao salvar: {e}",
                    text_color="#EF4444"
                )
            messagebox.showerror("Erro", f"Não foi possível salvar os parâmetros:\n{e}")

    def _restaurar_parametros_padrao(self):
        """Restaura as configurações de fábrica/padrão recomendadas."""
        self.param_fgts_mensal_var.set(True)
        self.param_emp_cred_trab_var.set(True)
        self.param_fgts_compl_var.set(True)
        self.param_emp_cred_tr_resc_var.set(False)
        self.param_simples_dom_var.set(False)
        self.nome_guia_var.set("FGTS - Competencia")
        self.nome_rel_fgts_var.set("RE FGTS - Competencia")
        self.nome_rel_cons_var.set("Consignado FGTS - Competencia")
        self.output_dir_var.set(str(settings.DEFAULT_OUTPUT_DIR))
        self.exigir_valor_esperado_var.set(True)
        self._salvar_parametros()

    # -------------------------------------------------------------------------
    # MÉTODOS DE AÇÃO & LÓGICA DE DADOS
    # -------------------------------------------------------------------------

    def _aplicar_preset_nomes(self, preset: str):
        """Aplica padrões de nomenclatura pré-definidos."""
        if preset == "padrao":
            self.nome_guia_var.set("FGTS - Competencia")
            self.nome_rel_fgts_var.set("RE FGTS - Competencia")
            self.nome_rel_cons_var.set("Consignado FGTS - Competencia")
        elif preset == "empresa":
            self.nome_guia_var.set("FGTS - Competencia - Empresa")
            self.nome_rel_fgts_var.set("RE FGTS - Competencia - Empresa")
            self.nome_rel_cons_var.set("Consignado FGTS - Competencia - Empresa")
        elif preset == "cnpj":
            self.nome_guia_var.set("FGTS_Competencia_CNPJ")
            self.nome_rel_fgts_var.set("RE_FGTS_Competencia_CNPJ")
            self.nome_rel_cons_var.set("Consignado_FGTS_Competencia_CNPJ")

    def _selecionar_excel(self):
        arquivo = filedialog.askopenfilename(
            title="Selecione a Planilha de Empresas",
            filetypes=[("Planilhas Excel (*.xlsx, *.xls)", "*.xlsx *.xls"), ("Arquivos CSV (*.csv)", "*.csv")]
        )
        if arquivo:
            self.excel_path_var.set(arquivo)
            self._carregar_e_exibir_empresas()

    def _gerar_modelo_excel(self):
        caminho = filedialog.asksaveasfilename(
            title="Salvar Planilha Modelo",
            defaultextension=".xlsx",
            initialfile="empresas_modelo_fgts.xlsx",
            filetypes=[("Planilha Excel (*.xlsx)", "*.xlsx")]
        )
        if caminho:
            ExcelManager.criar_planilha_modelo(Path(caminho))
            self.excel_path_var.set(caminho)
            self._carregar_e_exibir_empresas()
            messagebox.showinfo("Sucesso", f"Planilha modelo criada em:\n{caminho}")

    def _selecionar_output(self):
        pasta = filedialog.askdirectory(title="Selecione a Pasta de Saída")
        if pasta:
            self.output_dir_var.set(pasta)

    def _abrir_pasta_saida(self):
        pasta = settings.resolver_caminho(self.output_dir_var.get())
        pasta.mkdir(parents=True, exist_ok=True)
        os.startfile(str(pasta.resolve()))

    def _selecionar_pdf_folha(self):
        arquivo = filedialog.askopenfilename(
            title="Selecione o Relatório de Encargos em PDF",
            filetypes=[("Arquivos PDF (*.pdf)", "*.pdf"), ("Todos os arquivos", "*.*")]
        )
        if arquivo:
            self.pdf_relatorio_path_var.set(arquivo)
            self._processar_pdf_folha()

    def _processar_pdf_folha(self):
        caminho_str = self.pdf_relatorio_path_var.get().strip()
        if not caminho_str:
            return
        caminho = Path(caminho_str)
        if not caminho.exists():
            return

        try:
            logger.info(f"Lendo relatório PDF: {caminho.name}...")
            regras = {
                "fgts_mensal": self.param_fgts_mensal_var.get(),
                "emp_cred_trab": self.param_emp_cred_trab_var.get(),
                "fgts_compl": self.param_fgts_compl_var.get(),
                "emp_cred_tr_resc": self.param_emp_cred_tr_resc_var.get(),
                "simples_dom": self.param_simples_dom_var.get(),
            }
            empresas = RelatorioFolhaParser.parse_pdf(caminho, regras_encargos=regras)
            self.empresas_folha_pdf = empresas
            self._renderizar_tabela_folha()

            total_emp = len(empresas)
            tot_mensal = sum(e["fgts_mensal"] for e in empresas)
            tot_consignado = sum(e.get("consignado", 0.0) for e in empresas)
            tot_fgts = sum(e["total_fgts"] for e in empresas)
            tot_rescisorio = sum(e["fgts_rescisorio"] for e in empresas)

            resumo = (
                f"✔ {total_emp} entidades identificadas   |   "
                f"FGTS Mensal: R$ {tot_mensal:,.2f}   |   "
                f"Consignado: R$ {tot_consignado:,.2f}   |   "
                f"Guia FGTS Unificada: R$ {tot_fgts:,.2f}   |   "
                f"Rescisório: R$ {tot_rescisorio:,.2f}"
            )
            self.lbl_resumo_folha.configure(text=resumo, text_color="#22C55E")
            self._atualizar_cards_kpi()

        except Exception as e:
            logger.error(f"Erro ao processar relatório PDF: {e}")
            self.lbl_resumo_folha.configure(text=f"Erro ao processar arquivo: {e}", text_color="#EF4444")

    def _alternar_selecao_todas_folha(self):
        estado = self.chk_todas_folha_var.get()
        for w in self.widgets_folha_linhas:
            w["chk_var"].set(estado)

    def _limpar_dados_folha_pdf(self):
        """Limpa todos os dados extraídos do PDF e reinicia a visualização."""
        self.empresas_folha_pdf = []
        self.pdf_relatorio_path_var.set("")
        self._renderizar_tabela_folha()
        self.lbl_resumo_folha.configure(
            text="Dados limpos. Selecione um novo arquivo PDF para processar.",
            text_color="#94A3B8"
        )
        self._atualizar_cards_kpi()

    def _coletar_empresas_editadas_folha(self) -> List[Dict[str, Any]]:
        import re
        resultado = []
        for w in self.widgets_folha_linhas:
            doc_str = w["entry_doc"].get().strip()
            razao_str = w["entry_razao"].get().strip()
            comp_str = w["entry_comp"].get().strip()

            def parse_entry_num(entry_widget):
                val_txt = entry_widget.get().replace("R$", "").strip()
                if not val_txt:
                    return 0.0
                if "," in val_txt and "." in val_txt:
                    val_txt = val_txt.replace(".", "").replace(",", ".")
                elif "," in val_txt:
                    val_txt = val_txt.replace(",", ".")
                try:
                    return float(val_txt)
                except Exception:
                    return 0.0

            mensal_val = parse_entry_num(w["entry_mensal"])
            consig_val = parse_entry_num(w["entry_consignado"])
            resc_val = parse_entry_num(w["entry_rescisorio"])

            tot_fgts = round(mensal_val + consig_val, 2)
            outros = w["emp_original"].get("outros_encargos", 0.0)
            tot_geral = round(tot_fgts + resc_val + outros, 2)
            doc_limpo = re.sub(r"\D", "", doc_str)

            resultado.append({
                "selecionado": w["chk_var"].get(),
                "tipo_doc": "CPF" if len(doc_limpo) == 11 else "CNPJ",
                "documento": doc_str,
                "documento_limpo": doc_limpo,
                "razao_social": razao_str,
                "competencia": comp_str,
                "fgts_mensal": mensal_val,
                "consignado": consig_val,
                "fgts_rescisorio": resc_val,
                "outros_encargos": outros,
                "total_fgts": tot_fgts,
                "total_geral": tot_geral,
                "funcionarios_rescisorios": w["emp_original"].get("funcionarios_rescisorios", [])
            })
        return resultado

    def _enviar_folha_para_robo(self):
        empresas = self._coletar_empresas_editadas_folha()
        selecionadas = [e for e in empresas if e["selecionado"] and e["tipo_doc"] == "CNPJ"]

        if not selecionadas:
            messagebox.showwarning("Atenção", "Nenhuma empresa (CNPJ) selecionada para enviar ao robô.")
            return

        import pandas as pd
        excel_path = Path(self.excel_path_var.get().strip())
        
        dados = []
        for e in selecionadas:
            dados.append({
                "CNPJ": e["documento_limpo"],
                "Razao_Social": e["razao_social"],
                "Competencia": e["competencia"],
                "Status": "Pendente",
                "FGTS_Esperado": e["total_fgts"]
            })

        df = pd.DataFrame(dados)
        df.to_excel(excel_path, index=False)
        logger.info(f"{len(selecionadas)} empresas importadas da folha salvas na planilha do robô.")

        self._carregar_e_exibir_empresas()
        self._navegar_para("painel")

        msg = (
            f"✔ {len(selecionadas)} empresas carregadas com sucesso no robô!\n\n"
            f"Elas já estão prontas no Painel de Controle.\n"
            f"Basta clicar em '▶ Iniciar Automação' para processar o lote."
        )
        messagebox.showinfo("Empresas Enviadas ao Robô", msg)

    def _salvar_folha_excel(self):
        empresas = self._coletar_empresas_editadas_folha()
        if not empresas:
            messagebox.showwarning("Atenção", "Nenhum dado para exportar.")
            return
        arquivo = filedialog.asksaveasfilename(
            title="Salvar Planilha de Encargos",
            defaultextension=".xlsx",
            initialfile=f"Encargos_Folha_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            filetypes=[("Planilha Excel (*.xlsx)", "*.xlsx")]
        )
        if arquivo:
            RelatorioFolhaParser.exportar_para_excel(empresas, Path(arquivo))
            messagebox.showinfo("Sucesso", f"Planilha salva com sucesso em:\n{arquivo}")

    def _exportar_folha_pdf(self):
        empresas = self._coletar_empresas_editadas_folha()
        if not empresas:
            messagebox.showwarning("Atenção", "Nenhum dado para exportar.")
            return
        arquivo = filedialog.asksaveasfilename(
            title="Salvar Resumo em PDF",
            defaultextension=".pdf",
            initialfile=f"Resumo_Encargos_Folha_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            filetypes=[("Documento PDF (*.pdf)", "*.pdf")]
        )
        if arquivo:
            RelatorioFolhaParser.exportar_para_pdf(empresas, Path(arquivo))
            messagebox.showinfo("Sucesso", f"Relatório PDF gerado com sucesso em:\n{arquivo}")

    def _carregar_e_exibir_empresas(self):
        for w in self.frame_tabela.winfo_children():
            w.destroy()

        excel_path = Path(self.excel_path_var.get().strip())
        if not excel_path.exists():
            self.empresas_carregadas = []
            self.lbl_resumo_empresas.configure(text="Planilha não encontrada.")
            self._atualizar_cards_kpi()
            return

        try:
            competencia = self._obter_competencia_selecionada()
            empresas = ExcelManager.ler_empresas(excel_path, competencia_padrao=competencia)
            self.empresas_carregadas = empresas
            total = len(empresas)
            validos = sum(1 for e in empresas if e["valido"])

            self.lbl_resumo_empresas.configure(
                text=f"Total: {total} empresas   |   Válidas: {validos}   |   Inválidas: {total - validos}"
            )
            # Cabeçalho da Tabela da Fila
            header_linha = ctk.CTkFrame(self.frame_tabela, fg_color=("#E2E8F0", "#0F172A"), corner_radius=6)
            header_linha.pack(fill="x", padx=4, pady=(2, 6))
            header_linha.grid_columnconfigure(1, weight=1)

            lbl_h_cnpj = ctk.CTkLabel(header_linha, text="CNPJ", width=160, font=ctk.CTkFont(weight="bold"), anchor="w")
            lbl_h_cnpj.grid(row=0, column=0, padx=8, pady=5)

            lbl_h_razao = ctk.CTkLabel(header_linha, text="Razão Social", font=ctk.CTkFont(weight="bold"), anchor="w")
            lbl_h_razao.grid(row=0, column=1, padx=8, pady=5, sticky="ew")

            lbl_h_comp = ctk.CTkLabel(header_linha, text="Competência", width=90, font=ctk.CTkFont(weight="bold"), anchor="center")
            lbl_h_comp.grid(row=0, column=2, padx=8, pady=5)

            lbl_h_fgts = ctk.CTkLabel(header_linha, text="FGTS Folha (R$)", width=120, font=ctk.CTkFont(weight="bold"), anchor="e")
            lbl_h_fgts.grid(row=0, column=3, padx=8, pady=5)

            lbl_h_status = ctk.CTkLabel(header_linha, text="Validação", width=100, font=ctk.CTkFont(weight="bold"), anchor="center")
            lbl_h_status.grid(row=0, column=4, padx=8, pady=5)

            # Renderiza linhas da fila
            for idx, emp in enumerate(empresas):
                bg_cor = ("#F8FAFC", "#1E293B") if idx % 2 == 0 else ("#FFFFFF", "#0F172A")
                linha = ctk.CTkFrame(self.frame_tabela, fg_color=bg_cor, corner_radius=4)
                linha.pack(fill="x", padx=4, pady=2)
                linha.grid_columnconfigure(1, weight=1)

                lbl_c1 = ctk.CTkLabel(linha, text=emp["cnpj_formatado"], width=160, font=ctk.CTkFont(family=FONTE_MONO), anchor="w")
                lbl_c1.grid(row=0, column=0, padx=8, pady=4)

                lbl_c2 = ctk.CTkLabel(linha, text=emp["razao_social"], anchor="w")
                lbl_c2.grid(row=0, column=1, padx=8, pady=4, sticky="ew")

                comp_txt = emp.get("competencia") or competencia
                lbl_c3 = ctk.CTkLabel(linha, text=comp_txt, width=90, anchor="center")
                lbl_c3.grid(row=0, column=2, padx=8, pady=4)

                fgts_esp = float(emp.get("fgts_esperado", 0.0) or 0.0)
                lbl_c4 = ctk.CTkLabel(linha, text=f"R$ {fgts_esp:,.2f}", width=110, font=ctk.CTkFont(weight="bold"), anchor="e")
                lbl_c4.grid(row=0, column=3, padx=8, pady=4)

                badge_cor = "#22C55E" if emp["valido"] else "#EF4444"
                badge_txt = "✔ Válido" if emp["valido"] else "✖ Inválido"
                badge = ctk.CTkLabel(
                    linha,
                    text=badge_txt,
                    width=100,
                    text_color=badge_cor,
                    font=ctk.CTkFont(weight="bold"),
                    anchor="center"
                )
                badge.grid(row=0, column=4, padx=8, pady=4)

        except Exception as e:
            logger.error(f"Erro ao carregar planilha de empresas: {e}")
            self.lbl_resumo_empresas.configure(text=f"Erro ao ler arquivo: {e}", text_color="#EF4444")
        finally:
            self._atualizar_cards_kpi()

    def _limpar_fila_empresas(self):
        """Limpa a fila de empresas carregadas e esvazia a planilha de trabalho."""
        excel_path = Path(self.excel_path_var.get().strip())
        import pandas as pd
        df_vazio = pd.DataFrame(columns=["CNPJ", "Razao_Social", "Competencia", "Status", "FGTS_Esperado"])
        df_vazio.to_excel(excel_path, index=False)
        self.empresas_carregadas = []
        self._carregar_e_exibir_empresas()
        logger.info("Fila de empresas limpa pelo usuário.")
        messagebox.showinfo("Fila Limpa", "A fila de empresas foi esvaziada com sucesso.")

    def _ao_alterar_competencia(self):
        """Recarrega a fila e os cards com a nova competência selecionada."""
        self._carregar_e_exibir_empresas()

    def _abrir_planilha_no_excel(self):
        caminho = Path(self.excel_path_var.get().strip())
        if caminho.exists():
            os.startfile(str(caminho.resolve()))
        else:
            messagebox.showerror("Erro", "O arquivo não existe.")

    def _adicionar_log_interface(self, mensagem: str, nivel: str):
        """
        Listener do logging: só enfileira (não toca no Tkinter). É chamado com a trava do
        handler de log segura e de qualquer thread; chamar self.after() daqui fazia a thread
        do robô esperar a thread principal enquanto esta esperava a trava do log (deadlock).
        """
        self._fila_ui.put(lambda: self._inserir_linha_log(mensagem))

    def _inserir_linha_log(self, mensagem: str):
        self.txt_logs.insert("end", f"{mensagem}\n")
        self.txt_logs.see("end")

    def _drenar_fila_ui(self):
        """Executa, na thread principal, o que as outras threads enfileiraram (até 500 itens por ciclo)."""
        try:
            for _ in range(500):
                funcao = self._fila_ui.get_nowait()
                try:
                    funcao()
                except Exception as e:
                    print(f"[UI] Falha ao aplicar atualização de tela: {e}", file=sys.stderr)
        except queue.Empty:
            pass
        try:
            self._id_drenagem = self.after(50, self._drenar_fila_ui)
        except tk.TclError:
            pass  # janela já destruída

    def destroy(self):
        remove_log_listener(self._adicionar_log_interface)
        try:
            self.after_cancel(self._id_drenagem)
        except Exception:
            pass
        super().destroy()

    def _limpar_logs(self):
        self.txt_logs.delete("1.0", "end")

    def _obter_competencia_selecionada(self) -> str:
        tipo = self.comp_tipo_var.get()
        if tipo == "manual":
            manual = self.comp_manual_var.get().strip()
            return calcular_competencia(manual)
        return calcular_competencia(tipo)

    # -------------------------------------------------------------------------
    # EXECUÇÃO DO ROBÔ (WORKER THREAD)
    # O Tkinter não é thread-safe: a thread do robô nunca toca em widgets nem em
    # variáveis Tk. A configuração é lida na thread principal (_coletar_config_execucao)
    # e toda atualização de tela passa por _na_ui, que só enfileira em self._fila_ui
    # (nunca chama self.after() de outra thread — ver _drenar_fila_ui).
    # -------------------------------------------------------------------------

    def _na_ui(self, funcao, *args, **kwargs):
        """Agenda uma função para rodar na thread principal (via fila; seguro em qualquer thread)."""
        self._fila_ui.put(lambda: funcao(*args, **kwargs))

    def _coletar_config_execucao(self) -> Dict[str, Any]:
        """Lê todas as opções da tela (thread principal) para a thread do robô."""
        return {
            "competencia": self._obter_competencia_selecionada(),
            "excel_path": Path(self.excel_path_var.get().strip()),
            "output_dir": settings.resolver_caminho(self.output_dir_var.get()),
            "headless": self.headless_var.get(),
            "templates_nomes": {
                "guia": self.nome_guia_var.get().strip() or "FGTS - Competencia",
                "relatorio_fgts": self.nome_rel_fgts_var.get().strip() or "RE FGTS - Competencia",
                "relatorio_consignado": self.nome_rel_cons_var.get().strip() or "Consignado FGTS - Competencia"
            },
            "apenas_conferir": self.apenas_conferir_var.get(),
            "bloquear_se_divergente": self.travar_divergencia_var.get(),
            "exigir_valor_esperado": self.exigir_valor_esperado_var.get(),
        }

    def _iniciar_execucao(self):
        if self.is_running:
            self.evento_parar.set()
            self.btn_iniciar.configure(text="Cancelando...", state="disabled")
            return

        excel_path = Path(self.excel_path_var.get().strip())
        if not excel_path.exists():
            messagebox.showerror("Atenção", "A planilha de empresas informada não existe.")
            return

        config = self._coletar_config_execucao()
        self.is_running = True
        self.evento_parar.clear()
        self.btn_iniciar.configure(text="⏹ Parar Execução", fg_color=CORES["danger"], hover_color=CORES["danger_hover"])
        self.progress_bar.set(0)

        thread = threading.Thread(target=self._executar_em_background, args=(config,), daemon=True)
        thread.start()

    @staticmethod
    def _classificar_resultado(status: str) -> str:
        """Agrupa o status de uma empresa nos contadores da tela."""
        st_low = status.lower()
        if "iguais" in st_low or "conferido" in st_low:
            return "iguais"
        if "diverg" in st_low:
            return "divergencias"
        if "sucesso" in st_low:
            return "sucessos"
        if any(k in st_low for k in ["pendente", "sem debito", "sem débito", "sem movimento", "valor consultado"]):
            return "pendentes"
        return "erros"

    def _executar_em_background(self, config: Dict[str, Any]):
        competencia = config["competencia"]
        apenas_conferir = config["apenas_conferir"]
        output_dir = config["output_dir"]
        modo_rotulo = "Conferência de Valores" if apenas_conferir else "Emissão em Lote"

        logger.info(f"--- Iniciando Rodada FGTS Digital Pro: {modo_rotulo} (Competência: {competencia}) ---")
        self._na_ui(self.lbl_progresso.configure, text=f"Carregando lote para competência {competencia}...")

        contadores = {"sucessos": 0, "pendentes": 0, "erros": 0, "iguais": 0, "divergencias": 0}

        def ao_iniciar_empresa(idx: int, total: int, emp: Dict[str, Any]):
            if apenas_conferir:
                texto = f"[{idx}/{total}] Conferindo {emp['cnpj_formatado']} | Iguais: {contadores['iguais']} | Divergências: {contadores['divergencias']}"
            else:
                texto = f"[{idx}/{total}] Processando {emp['cnpj_formatado']} | Emitidas: {contadores['sucessos']} | Alertas: {contadores['erros']}"
            self._na_ui(self.progress_bar.set, (idx - 1) / total)
            self._na_ui(self.lbl_progresso.configure, text=texto)

        def ao_concluir_empresa(idx: int, total: int, res: Dict[str, Any]):
            contadores[self._classificar_resultado(res.get("status", ""))] += 1
            self._na_ui(self.progress_bar.set, idx / total)

        try:
            empresas = ExcelManager.ler_empresas(config["excel_path"], competencia_padrao=competencia)
            total = len(empresas)
            if total == 0:
                logger.warning("Nenhuma empresa válida encontrada na planilha.")
                return

            self.browser_manager = BrowserManager(
                headless=config["headless"],
                downloads_path=output_dir
            )

            page = self.browser_manager.iniciar()
            bot = FGTSDigitalBot(page=page, output_base_dir=output_dir)

            self._na_ui(self.lbl_progresso.configure, text="Autenticando no Gov.br com Certificado Digital...")
            if not bot.login():
                logger.error("Falha na autenticação inicial com o FGTS Digital.")
                self._na_ui(messagebox.showerror, "Erro de Autenticação", "Não foi possível autenticar no portal com o certificado.")
                return

            resultados = bot.processar_lote(
                empresas,
                competencia,
                callback_progresso=ao_concluir_empresa,
                bloquear_se_divergente=config["bloquear_se_divergente"],
                apenas_conferir=apenas_conferir,
                exigir_valor_esperado=config["exigir_valor_esperado"],
                templates_nomes=config["templates_nomes"],
                callback_inicio=ao_iniciar_empresa,
                evento_parar=self.evento_parar
            )

            if resultados:
                rel_path = ExcelManager.gerar_relatorio_execucao(resultados, output_dir, competencia)
                logger.info(f"Relatório de execução salvo em: {rel_path.name}")

            c = contadores
            interrompido = len(resultados) < total
            aviso_interrupcao = f"\n\n⏹ Execução interrompida: {len(resultados)} de {total} empresas processadas." if interrompido else ""
            aviso_div = ""
            if c["divergencias"] > 0:
                aviso_div = (
                    f"\n\n⚠ ATENÇÃO: Foram identificadas {c['divergencias']} divergências de valores! "
                    f"Consulte o relatório 'Relatorio_FGTS_Digital_*.xlsx' gerado na pasta de saída."
                )

            if apenas_conferir:
                texto_final = f"Conferência Concluída! Total: {total} | Iguais: {c['iguais']} | Divergências: {c['divergencias']} | Pendentes/Sem Débito: {c['pendentes']}"
                titulo = "Conferência Concluída"
                msg_final = (
                    f"Conferência de valores finalizada!\n\n"
                    f"Total de Empresas: {total}\n"
                    f"Valores Iguais (OK): {c['iguais']}\n"
                    f"Divergências Detectadas: {c['divergencias']}\n"
                    f"Sem Movimento / Pendentes / Consultados: {c['pendentes']}\n"
                    f"Erros (procuração, perfil, técnicos): {c['erros']}\n\n"
                    f"Nenhuma guia foi emitida.\n"
                    f"O relatório completo de conferência foi salvo na pasta de saída."
                )
            else:
                texto_final = f"Finalizado! Total: {total} | Emitidas: {c['sucessos']} | Pendentes: {c['pendentes']} | Alertas: {c['erros']} | Divergências: {c['divergencias']}"
                titulo = "Processamento Concluído"
                msg_final = (
                    f"Lote finalizado!\n\n"
                    f"Total de Empresas: {total}\n"
                    f"Guias Emitidas: {c['sucessos']}\n"
                    f"Pendentes/Sem Movimento: {c['pendentes']}\n"
                    f"Divergências (não emitidas): {c['divergencias']}\n"
                    f"Alertas (procuração, perfil, validação de PDF, técnicos): {c['erros']}\n\n"
                    f"Os relatórios e comprovantes estão salvos na pasta de saída."
                )
            self._na_ui(self.lbl_progresso.configure, text=texto_final)
            self._na_ui(messagebox.showinfo, titulo, msg_final + aviso_div + aviso_interrupcao)

        except Exception as e:
            logger.error(f"Erro inesperado durante a automação: {e}")
            self._na_ui(messagebox.showerror, "Erro", f"Ocorreu um erro durante o processamento:\n{e}")
        finally:
            if self.browser_manager:
                self.browser_manager.fechar()
            self._na_ui(self._finalizar_execucao_ui)

    def _finalizar_execucao_ui(self):
        """Restaura o botão e o estado da tela ao fim da execução (thread principal)."""
        self.is_running = False
        self.evento_parar.clear()
        if self.apenas_conferir_var.get():
            self.btn_iniciar.configure(
                text="🔍 Iniciar Conferência de Valores",
                fg_color=CORES["success"],
                hover_color=CORES["success_hover"],
                state="normal"
            )
        else:
            self.btn_iniciar.configure(
                text="▶ Iniciar Automação",
                fg_color=CORES["success"],
                hover_color=CORES["success_hover"],
                state="normal"
            )


def iniciar_aplicacao():
    app = FGTSDigitalApp()
    app.mainloop()


if __name__ == "__main__":
    iniciar_aplicacao()
