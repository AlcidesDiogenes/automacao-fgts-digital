"""
Gera as imagens do README a partir da INTERFACE REAL do programa, usando somente dados
FICTÍCIOS (LGPD): planilha e relatório do Domínio sintéticos em data/output/exemplo_ficticio/.
O relatório real em data/ nunca é carregado. O robô e o navegador são simulados (nenhum acesso
ao portal).

Gera em docs/assets/:
  - tela_painel.png        Painel de Controle com a fila carregada
  - tela_importar_pdf.png  Importação do relatório do Domínio (tabela de encargos)
  - tela_fila.png          Fila de empresas
  - tela_parametros.png    Parâmetros (certificado do Windows, regras de leitura, nomenclatura)
  - tela_logs.png          Logs após um lote simulado
  - fluxo_app.gif          Importar PDF -> enviar ao robô -> executar lote (simulado)

Uso (na raiz do projeto, com a tela do computador livre — a janela fica em primeiro plano
durante a captura):
    venv/Scripts/python.exe scripts/capturar_telas.py

Refazer sempre que a interface mudar (regra de documentação do projeto).
"""

import ctypes
import sys
import time
from ctypes import wintypes
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

import os  # noqa: E402

os.chdir(RAIZ)

import pandas as pd  # noqa: E402
from PIL import Image, ImageGrab  # noqa: E402

from config import settings  # noqa: E402
from tests.conftest import gerar_pdf_dominio  # noqa: E402

ASSETS = RAIZ / "docs" / "assets"
PASTA_FICTICIA = Path("data/output/exemplo_ficticio")  # relativo: o caminho exibido na tela fica curto

# --------------------------------------------------------------------------------------------
# Dados fictícios (CNPJs e CPF de exemplo, nomes inventados, valores arbitrários)
# --------------------------------------------------------------------------------------------
EMPRESAS = [
    ("11.444.777/0001-61", "ALFA COMERCIO FICTICIO LTDA", [("FGTS", "8.420,00"), ("Emp. Créd. Trab.", "1.130,40")]),
    ("22.333.444/0001-81", "BETA SERVICOS EXEMPLO LTDA", [("FGTS", "3.215,75")]),
    ("33.222.111/0001-30", "GAMA INDUSTRIA MODELO S/A", [("FGTS", "12.980,10"), ("FGTS Compl.", "410,00"), ("Emp. Créd. Trab.", "2.045,90")]),
    ("44.555.666/0001-02", "DELTA TRANSPORTES TESTE LTDA", [("FGTS", "1.760,32"), ("Emp. Créd. Trab.", "220,15")]),
    ("55.666.777/0001-90", "EPSILON ALIMENTOS DEMO LTDA", [("FGTS", "5.034,88")]),
]
DOMESTICO = ("123.456.789-09", "EMPREGADOR DOMESTICO FICTICIO", [("Simples doméstico", "312,40")])

# Status que o robô simulado devolve, por CNPJ (mostra os tipos de resultado da v2.1)
STATUS_SIMULADO = {
    "11444777000161": "Sucesso - Guia Emitida",
    "22333444000181": "Sucesso - Guia Emitida",
    "33222111000130": "Divergência de Valores (Não Emitida)",
    "44555666000102": "Sem Débitos / Movimento",
    "55666777000190": "Sucesso - Guia Emitida",
}


def _paginas():
    paginas = []
    for doc, razao, encargos in EMPRESAS + [DOMESTICO]:
        linhas = []
        for nome, valor in encargos:
            linhas += [f"{nome} 1 {valor} 09/2026 20/10/2026 {valor}", f"Total: {valor} {valor}"]
        paginas.append({
            "doc": doc,
            "tipo_doc": "CPF" if len(doc) == 14 else "CNPJ",
            "razao": razao,
            "linhas": linhas,
        })
    return paginas


def preparar_dados():
    PASTA_FICTICIA.mkdir(parents=True, exist_ok=True)
    gerar_pdf_dominio(PASTA_FICTICIA / "relatorio_encargos_exemplo.pdf", _paginas())
    pd.DataFrame(columns=["CNPJ", "Razao_Social", "Competencia", "Status", "FGTS_Esperado"]).to_excel(
        PASTA_FICTICIA / "empresas_ficticias.xlsx", index=False
    )


# --------------------------------------------------------------------------------------------
# Robô e navegador simulados
# --------------------------------------------------------------------------------------------
class NavegadorSimulado:
    def __init__(self, **kwargs):
        pass

    def iniciar(self):
        return object()

    def fechar(self):
        pass


def fabrica_robo(ui_mod):
    class RoboSimulado:
        def __init__(self, page, output_base_dir):
            pass

        def login(self):
            time.sleep(0.6)
            return True

        def trocar_perfil(self, cnpj):
            time.sleep(0.4)
            return {"sucesso": True}

        def emitir_guia_e_relatorios(self, cnpj, razao, comp, fgts_esperado=0.0, **kwargs):
            time.sleep(0.9)
            status = STATUS_SIMULADO.get(cnpj, "Sucesso - Guia Emitida")
            return {
                "cnpj": cnpj, "cnpj_formatado": cnpj, "razao_social": razao, "competencia": comp,
                "status": status, "valor_guia": fgts_esperado, "fgts_esperado": fgts_esperado,
                "diferenca": 0.0, "arquivo_guia": "", "arquivo_relatorio": "", "data_hora": "",
                "detalhes": "",
            }

    RoboSimulado.processar_lote = ui_mod.FGTSDigitalBot.processar_lote
    return RoboSimulado


# --------------------------------------------------------------------------------------------
# Captura
# --------------------------------------------------------------------------------------------
def retangulo_janela(app):
    """Retângulo da janela (com barra de título) em pixels físicos da tela."""
    hwnd = ctypes.windll.user32.GetParent(app.winfo_id())
    rect = wintypes.RECT()
    DWMWA_EXTENDED_FRAME_BOUNDS = 9
    ctypes.windll.dwmapi.DwmGetWindowAttribute(
        hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect)
    )
    return rect.left, rect.top, rect.right, rect.bottom


def esperar(app, segundos):
    fim = time.time() + segundos
    while time.time() < fim:
        app.update()
        time.sleep(0.02)


def capturar(app, nome=None):
    app.lift()
    esperar(app, 0.4)
    img = ImageGrab.grab(bbox=retangulo_janela(app), all_screens=True)
    if nome:
        img.save(ASSETS / nome, optimize=True)
        print(f"   salvo: docs/assets/{nome} ({img.width}x{img.height})")
    return img


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

    preparar_dados()

    # Aponta o programa para os dados fictícios ANTES de criar a janela
    settings.DATA_DIR = PASTA_FICTICIA
    settings.DEFAULT_EXCEL_PATH = PASTA_FICTICIA / "empresas_ficticias.xlsx"

    import src.ui.app as ui_mod

    ui_mod.messagebox.showinfo = lambda *a, **k: None
    ui_mod.messagebox.showwarning = lambda *a, **k: None
    ui_mod.messagebox.showerror = lambda *a, **k: None
    ui_mod.BrowserManager = NavegadorSimulado
    ui_mod.FGTSDigitalBot = fabrica_robo(ui_mod)
    ui_mod.FGTSDigitalApp._salvar_parametros_silencioso = lambda self: None

    app = ui_mod.FGTSDigitalApp()
    app.geometry("1280x820+20+20")
    app.attributes("-topmost", True)
    esperar(app, 3.0)  # leitura automática do PDF fictício
    app._limpar_logs()
    # Exibe o caminho relativo (o absoluto mostraria o nome de usuário do Windows)
    app.pdf_relatorio_path_var.set(str(PASTA_FICTICIA / "relatorio_encargos_exemplo.pdf"))
    app.output_dir_var.set(str(PASTA_FICTICIA / "saida"))  # o lote simulado grava o relatório aqui

    quadros = []

    def quadro(repeticoes=1):
        img = capturar(app)
        quadros.extend([img] * repeticoes)

    print("-> Capturando telas...")
    app._navegar_para("folha")
    esperar(app, 1.0)
    capturar(app, "tela_importar_pdf.png")
    quadro(6)

    app._enviar_folha_para_robo()  # grava a planilha fictícia e volta ao Painel
    esperar(app, 1.0)
    capturar(app, "tela_painel.png")
    quadro(5)

    app._navegar_para("empresas")
    esperar(app, 0.8)
    capturar(app, "tela_fila.png")
    quadro(4)

    app._navegar_para("parametros")
    esperar(app, 0.8)
    capturar(app, "tela_parametros.png")

    print("-> Executando lote simulado para o GIF...")
    app._navegar_para("painel")
    esperar(app, 0.5)
    app._iniciar_execucao()
    fim = time.time() + 60
    while app.is_running and time.time() < fim:
        esperar(app, 0.7)
        quadro()
    esperar(app, 1.0)
    quadro(6)

    app._navegar_para("logs")
    esperar(app, 0.8)
    capturar(app, "tela_logs.png")
    quadro(6)

    print("-> Compilando fluxo_app.gif...")
    largura = 1000
    reduzidos = [q.resize((largura, int(q.height * largura / q.width)), Image.LANCZOS) for q in quadros]
    paleta = [r.convert("P", palette=Image.ADAPTIVE, colors=128) for r in reduzidos]
    paleta[0].save(
        ASSETS / "fluxo_app.gif", save_all=True, append_images=paleta[1:],
        duration=500, loop=0, optimize=True,
    )
    print(f"   salvo: docs/assets/fluxo_app.gif ({len(paleta)} quadros)")

    app.attributes("-topmost", False)
    app.destroy()


if __name__ == "__main__":
    main()
