"""
Teste da execução pela interface (sem portal real): navegador e robô são substituídos
por versões falsas. Verifica que a thread do robô não trava a tela, que os contadores
e a mensagem final saem certos e que o botão 'Parar' interrompe o lote.
"""

import re
import threading
import time

import pytest

ctk = pytest.importorskip("customtkinter")

import src.ui.app as app_mod  # noqa: E402
from src.core.excel_manager import ExcelManager  # noqa: E402
from src.utils.logger import remove_log_listener  # noqa: E402


class NavegadorFalso:
    def __init__(self, **kwargs):
        pass

    def iniciar(self):
        return object()

    def fechar(self):
        pass


def fabrica_robo(status_por_cnpj, atraso=0.0):
    class RoboFalso:
        def __init__(self, page, output_base_dir):
            self.thread_ids = set()

        def login(self):
            return True

        def trocar_perfil(self, cnpj):
            return {"sucesso": True}

        def emitir_guia_e_relatorios(self, cnpj, razao, comp, **kwargs):
            time.sleep(atraso)
            return {
                "cnpj": cnpj, "cnpj_formatado": cnpj, "razao_social": razao, "competencia": comp,
                "status": status_por_cnpj.get(cnpj, "Sucesso - Guia Emitida"),
                "valor_guia": 1.0, "fgts_esperado": 1.0, "diferenca": 0.0,
                "arquivo_guia": "", "arquivo_relatorio": "", "data_hora": "", "detalhes": "",
            }

    # processar_lote real, para testar o laço único
    RoboFalso.processar_lote = app_mod.FGTSDigitalBot.processar_lote
    return RoboFalso


@pytest.fixture(scope="module")
def _janela(tmp_path_factory):
    """
    Uma única janela por módulo: no Windows, criar várias instâncias de Tk no mesmo
    processo falha de forma intermitente ao reler o init.tcl.
    """
    mp = pytest.MonkeyPatch()
    mensagens = []
    mp.setattr(app_mod.messagebox, "showinfo", lambda t, m: mensagens.append(("info", t, m)))
    mp.setattr(app_mod.messagebox, "showerror", lambda t, m: mensagens.append(("erro", t, m)))
    mp.setattr(app_mod, "BrowserManager", NavegadorFalso)
    mp.setattr(app_mod.FGTSDigitalApp, "_salvar_parametros_silencioso", lambda self: None)

    pasta = tmp_path_factory.mktemp("ui")
    planilha = pasta / "empresas.xlsx"
    ExcelManager.criar_planilha_modelo(planilha)

    try:
        janela = app_mod.FGTSDigitalApp()
    except Exception as e:  # sem display disponível
        mp.undo()
        pytest.skip(f"Tk indisponível: {e}")
    janela.competencia_ao_abrir = janela.comp_manual_var.get()  # registrado antes de qualquer teste
    janela.excel_path_var.set(str(planilha))
    janela.planilha_padrao = str(planilha)
    janela.pasta_testes = pasta
    janela.output_dir_var.set(str(pasta / "saida"))
    janela.mensagens = mensagens
    yield janela
    remove_log_listener(janela._adicionar_log_interface)
    janela.destroy()
    mp.undo()


@pytest.fixture
def app(_janela):
    _janela.mensagens.clear()
    _janela.progress_bar.set(0)
    _janela.lbl_progresso.configure(text="")
    _janela.excel_path_var.set(_janela.planilha_padrao)
    _janela.comp_manual_var.set("09/2026")  # a competência é sempre digitada (ADR-0007)
    yield _janela


def _rodar_ate_terminar(janela, limite_s=30, ao_tick=None):
    """
    Processa os eventos da janela (update) até a execução terminar ou estourar o limite.

    Não usa mainloop()+quit(): na 1ª chamada em uma janela, o CTk.mainloop() do CustomTkinter
    executa um update() interno (cor da barra de título no Windows) antes de entrar no laço; um
    quit() disparado ali dentro era descartado, porque o mainloop do Tkinter zera o pedido de saída
    ao iniciar -> travamento intermitente da suíte (28/10/2026). Como a thread do robô só usa a
    fila da interface (não chama o Tkinter), o update() na thread principal é suficiente.
    """
    fim = time.time() + limite_s
    while janela.is_running and time.time() < fim:
        if ao_tick:
            ao_tick()
        janela.update()
        time.sleep(0.02)
    janela.update()
    assert not janela.is_running, "a execução não terminou"


def test_execucao_completa_atualiza_tela_e_contadores(app, monkeypatch):
    from pathlib import Path
    empresas = ExcelManager.ler_empresas(Path(app.excel_path_var.get()))
    status = {empresas[0]["cnpj"]: "Divergência de Valores (Não Emitida)"}
    monkeypatch.setattr(app_mod, "FGTSDigitalBot", fabrica_robo(status))

    app._iniciar_execucao()
    _rodar_ate_terminar(app)

    assert app.progress_bar.get() == pytest.approx(1.0)
    texto = app.lbl_progresso.cget("text")
    assert texto.startswith("Finalizado!") and "Divergências: 1" in texto
    tipo, titulo, msg = app.mensagens[-1]
    assert tipo == "info" and "Relatorio_FGTS_Digital_" in msg
    assert "DIVERGENCIAS_FGTS" not in msg
    assert app.btn_iniciar.cget("state") == "normal"


def test_botao_parar_interrompe_lote(app, monkeypatch):
    monkeypatch.setattr(app_mod, "FGTSDigitalBot", fabrica_robo({}, atraso=0.5))

    estado = {"parou": False}

    def clicar_parar_quando_iniciar():
        if not estado["parou"] and "[1/" in app.lbl_progresso.cget("text"):
            app._iniciar_execucao()  # segundo clique = Parar
            estado["parou"] = True

    app._iniciar_execucao()
    _rodar_ate_terminar(app, ao_tick=clicar_parar_quando_iniciar)
    assert estado["parou"]

    tipo, titulo, msg = app.mensagens[-1]
    assert "interrompida" in msg


def test_widgets_so_sao_alterados_na_thread_principal(app, monkeypatch):
    principal = threading.main_thread()
    chamadas_fora = []
    original = app.lbl_progresso.configure

    def configure_vigiado(*a, **k):
        if threading.current_thread() is not principal:
            chamadas_fora.append(threading.current_thread().name)
        return original(*a, **k)

    monkeypatch.setattr(app.lbl_progresso, "configure", configure_vigiado)
    monkeypatch.setattr(app_mod, "FGTSDigitalBot", fabrica_robo({}))
    app._iniciar_execucao()
    _rodar_ate_terminar(app)
    assert chamadas_fora == []


# ---------------------------------------------------------------------------
# Regressão do travamento (28/10/2026): a thread do robô escrevia no log, o
# handler da tela chamava self.after() (que, vindo de outra thread, ESPERA a
# thread principal) segurando a trava do logging; a thread principal, ao
# mesmo tempo, tentava escrever no log e esperava a mesma trava -> deadlock.
# Regra: nenhuma chamada ao Tkinter pode partir de outra thread.
# ---------------------------------------------------------------------------

def _vigiar_after(app, monkeypatch):
    principal = threading.main_thread()
    chamadas_fora = []
    original = app.after

    def after_vigiado(*a, **k):
        if threading.current_thread() is not principal:
            chamadas_fora.append(threading.current_thread().name)
            return None  # não encaminha ao Tk: chamá-lo fora da thread principal é o defeito
        return original(*a, **k)

    monkeypatch.setattr(app, "after", after_vigiado)
    return chamadas_fora


def _em_outra_thread(funcao):
    t = threading.Thread(target=funcao, name="robo-teste", daemon=True)
    t.start()
    t.join(timeout=10)
    assert not t.is_alive(), "a thread de trabalho ficou presa"


def test_log_vindo_de_outra_thread_nao_chama_o_tkinter(app, monkeypatch):
    chamadas_fora = _vigiar_after(app, monkeypatch)
    _em_outra_thread(lambda: app_mod.logger.info("linha de log vinda da thread do robô"))
    assert chamadas_fora == []


def test_na_ui_vindo_de_outra_thread_nao_chama_o_tkinter(app, monkeypatch):
    chamadas_fora = _vigiar_after(app, monkeypatch)
    _em_outra_thread(lambda: app._na_ui(app.lbl_progresso.configure, text="vindo da thread"))
    assert chamadas_fora == []


def test_logs_simultaneos_das_duas_threads_nao_travam_e_chegam_a_tela(app):
    total = 300
    marcador = f"estresse-{time.time()}"
    estado = {"principal": 0, "fim": False}

    def robo():
        for i in range(total):
            app_mod.logger.info(f"{marcador} robo {i}")

    def principal_escreve():
        if estado["principal"] < total:
            app_mod.logger.info(f"{marcador} principal {estado['principal']}")
            estado["principal"] += 1
            app.after(1, principal_escreve)

    t = threading.Thread(target=robo, daemon=True)
    app.after(1, principal_escreve)
    t.start()

    fim = time.time() + 20
    while time.time() < fim:
        app.update()
        texto = app.txt_logs.get("1.0", "end")
        completo = texto.count(f"{marcador} robo") == total and texto.count(f"{marcador} principal") == total
        if completo and not t.is_alive():
            estado["fim"] = True
            break
        time.sleep(0.02)
    assert estado["fim"], "nem todas as linhas de log chegaram à tela em 20 s"


# ---------------------------------------------------------------------------
# Competência sempre digitada (ADR-0007)
# ---------------------------------------------------------------------------

def test_campo_de_competencia_abre_vazio_e_sem_opcoes_anterior_atual(_janela):
    assert _janela.competencia_ao_abrir == ""
    assert not hasattr(_janela, "comp_tipo_var")
    textos = []
    pilha = [_janela]
    while pilha:
        w = pilha.pop()
        pilha.extend(w.winfo_children())
        try:
            textos.append(str(w.cget("text")))
        except Exception:
            pass
    assert not any(t.startswith(("Anterior", "Atual")) for t in textos)


@pytest.mark.parametrize("digitado", ["", "anterior", "13/2026", "2026/09"])
def test_nao_inicia_sem_competencia_valida(app, monkeypatch, digitado):
    monkeypatch.setattr(app_mod, "FGTSDigitalBot", fabrica_robo({}))
    app.comp_manual_var.set(digitado)
    app._iniciar_execucao()
    assert app.is_running is False
    tipo, titulo, msg = app.mensagens[-1]
    assert tipo == "erro" and "xx/xxxx" in msg


def test_nao_inicia_com_planilha_de_outra_competencia(app, monkeypatch):
    import pandas as pd
    planilha = app.pasta_testes / "divergente.xlsx"
    pd.DataFrame(
        [["11444777000161", "ALFA COMERCIO FICTICIO LTDA", "09/2026"],
         ["33222111000130", "GAMA INDUSTRIA MODELO S/A", "08/2026"]],
        columns=["CNPJ", "Razao_Social", "Competencia"],
    ).to_excel(planilha, index=False)
    monkeypatch.setattr(app_mod, "FGTSDigitalBot", fabrica_robo({}))
    app.excel_path_var.set(str(planilha))
    app.comp_manual_var.set("09/2026")
    app._iniciar_execucao()
    assert app.is_running is False
    tipo, titulo, msg = app.mensagens[-1]
    assert tipo == "erro" and "33.222.111/0001-30" in msg and "08/2026" in msg


def test_competencia_digitada_e_normalizada_e_usada_no_lote(app, monkeypatch):
    usadas = []
    Robo = fabrica_robo({})
    original = Robo.emitir_guia_e_relatorios

    def emitir_registrando(self, cnpj, razao, comp, **kwargs):
        usadas.append(comp)
        return original(self, cnpj, razao, comp, **kwargs)

    Robo.emitir_guia_e_relatorios = emitir_registrando
    monkeypatch.setattr(app_mod, "FGTSDigitalBot", Robo)
    app.comp_manual_var.set("9-2026")
    app._iniciar_execucao()
    _rodar_ate_terminar(app)
    assert usadas and set(usadas) == {"09/2026"}
    assert app.mensagens[-1][0] == "info"


def test_campo_vazio_exibe_xx_xxxx(app):
    # O placeholder do CTkEntry só aparece sem textvariable: confere o texto realmente exibido
    app.comp_manual_var.set("")
    app.focus_set()
    app.update()
    assert app.entry_comp_manual.get() == ""             # valor lido pelo programa
    assert app.entry_comp_manual._entry.get() == "xx/xxxx"  # texto exibido no campo


def _soltar_tecla(widget, keysym):
    """
    Executa os binds de <KeyRelease> do widget como o Tk faria ao soltar a tecla.

    Não usa event_generate: o Tk entrega teclas só ao widget com foco, e o Windows pode negar
    o foco à janela de teste quando outra janela está em uso (o teste falhava às vezes).
    Aqui o script do bind roda com a mesma substituição de %-campos que o Tk faz
    ("??" para os campos que não se aplicam).
    """
    valores = {"#": "0", "T": "3", "W": str(widget), "K": keysym}  # 3 = KeyRelease
    script = widget.bind("<KeyRelease>")
    assert script, "o campo não tem bind de <KeyRelease>"
    widget.tk.eval(re.sub(r"%(.)", lambda m: valores.get(m.group(1), "??"), script))


def test_campo_e_variavel_sincronizados(app):
    app.comp_manual_var.set("09/2026")
    app.update()
    assert app.entry_comp_manual.get() == "09/2026"
    campo = app.entry_comp_manual._entry  # o campo de texto real é o widget interno do CTkEntry
    app.entry_comp_manual.delete(0, "end")
    app.entry_comp_manual.insert(0, "10/2026")
    _soltar_tecla(campo, "6")  # sem foco: não depende da janela estar em primeiro plano
    app.update()
    assert app.comp_manual_var.get() == "10/2026"
