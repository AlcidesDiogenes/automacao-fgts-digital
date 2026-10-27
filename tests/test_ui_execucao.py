"""
Teste da execução pela interface (sem portal real): navegador e robô são substituídos
por versões falsas. Verifica que a thread do robô não trava a tela, que os contadores
e a mensagem final saem certos e que o botão 'Parar' interrompe o lote.
"""

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
    janela.excel_path_var.set(str(planilha))
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
    yield _janela


def _rodar_ate_terminar(janela, limite_s=30, ao_tick=None):
    """
    Roda o mainloop real (o Tkinter só aceita after() de outras threads com o mainloop ativo)
    até a execução terminar ou estourar o limite.
    """
    fim = time.time() + limite_s

    def checar():
        if ao_tick:
            ao_tick()
        if not janela.is_running or time.time() > fim:
            janela.quit()
        else:
            janela.after(50, checar)

    janela.after(50, checar)
    janela.mainloop()
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
