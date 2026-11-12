"""
Testes de segurança da emissão (Fase 1 da auditoria de 27/10/2026).
O robô roda contra um portal falso (ver conftest.py): o objetivo é garantir que,
na dúvida, ele NÃO emite e NÃO salva arquivo com nome de outra empresa.
"""

from conftest import gerar_pdf
from src.modules.fgts_digital.bot import FGTSDigitalBot

URL_SERVICOS = "https://fgtsdigital.sistema.gov.br/portal/servicos"
URL_GUIA_RAPIDA = "https://fgtsdigital.sistema.gov.br/cobranca/#/gestao-guias/emissao-guia-rapida"

CNPJ_ALVO = "12345678000190"
CNPJ_ANTERIOR = "98765432000110"


# ---------------------------------------------------------------------------
# Troca de perfil
# ---------------------------------------------------------------------------

def html_servicos(modo: str, cnpj_inicial: str = "98.765.432/0001-10") -> str:
    """
    modo:
      'ok'       -> confirma, fecha o modal e atualiza a barra de perfil
      'ignora'   -> botão Selecionar não faz nada (modal continua aberto)
      'sem_troca'-> fecha o modal mas a barra continua no CNPJ anterior
    """
    # Estrutura copiada do portal real (27/10/2026): span.dados-perfil + span.dados-usuario + botão
    return f"""
<html><body>
<div class="d-flex align-items-center">
  <div style="margin-right: 10px;">
    <span class="dados-perfil" id="perfil-ativo"> Empregador: {cnpj_inicial} | EMPRESA ANTERIOR LTDA </span>
    <span class="dados-usuario"> Usuário (Procurador): 123.456.780-00 | PROCURADOR TESTE </span>
  </div>
  <div><button type="button" class="br-button secondary botao-barra-perfil" onclick="abrir()">Trocar Perfil</button></div>
</div>
<lib-fgtsd-modal-alterar-perfil id="modal" style="display:none">
  <ng-select><span class="ng-value-label">Procurador</span></ng-select>
  <input placeholder="Informe CNPJ ou CPF" id="ni">
  <div class="modal-buttons">
    <button class="primary" onclick="confirmar()">Selecionar</button>
    <button>Cancelar</button>
  </div>
</lib-fgtsd-modal-alterar-perfil>
<script>
const MODO = "{modo}";
function fmt(v) {{
  v = v.replace(/\\D/g, "");
  return v.slice(0,2)+"."+v.slice(2,5)+"."+v.slice(5,8)+"/"+v.slice(8,12)+"-"+v.slice(12);
}}
function abrir() {{ document.getElementById('modal').style.display = 'block'; }}
function confirmar() {{
  if (MODO === 'ignora') return;
  document.getElementById('modal').style.display = 'none';
  if (MODO === 'ok') {{
    document.getElementById('perfil-ativo').textContent =
      ' Empregador: ' + fmt(document.getElementById('ni').value) + ' | EMPRESA ALVO LTDA ';
  }}
}}
</script>
</body></html>"""


def _abrir_servicos(portal, modo):
    portal.paginas["/portal/servicos"] = html_servicos(modo)
    portal.page.goto(URL_SERVICOS)
    return FGTSDigitalBot(page=portal.page, output_base_dir=".")


def test_troca_perfil_confirmada_quando_barra_mostra_cnpj_alvo(portal):
    bot = _abrir_servicos(portal, "ok")
    res = bot.trocar_perfil(CNPJ_ALVO)
    assert res["sucesso"] is True


def test_troca_perfil_falha_quando_botao_confirmar_nao_age(portal):
    bot = _abrir_servicos(portal, "ignora")
    res = bot.trocar_perfil(CNPJ_ALVO)
    assert res["sucesso"] is False
    assert res.get("status") == "Perfil não confirmado"


def test_troca_perfil_falha_quando_barra_continua_em_outra_empresa(portal):
    bot = _abrir_servicos(portal, "sem_troca")
    res = bot.trocar_perfil(CNPJ_ALVO)
    assert res["sucesso"] is False
    assert res.get("status") == "Perfil não confirmado"


# ---------------------------------------------------------------------------
# Emissão: tela de Guia Rápida
# ---------------------------------------------------------------------------

def card(tipo: str, total: str, marcador: str) -> str:
    return f"""
<div class="br-card">
  <h4>{tipo} - Vencimento 20/10/2026</h4>
  <p>FGTS</p>
  <p>Total Guia {total}</p>
  <button class="br-button primary" onclick="emitir('{marcador}')">Emitir guia</button>
</div>"""


def card_com_guia_relacionada(total: str, numeros=("9999999999999999-1",)) -> str:
    """
    Card Mensal com o bloco 'Guias relacionadas aguardando pagamento' (estrutura copiada do
    portal real em 12/11/2026: <a aria-label="Reimprimir guia"> com o número da guia; dados fictícios).
    """
    links = "".join(
        f'<span class="mr-1"><a tabindex="0" aria-label="Reimprimir guia" class="link pointer" '
        f'onclick="reimprimir(\'{n}\')">{n}</a></span>'
        for n in numeros
    )
    return f"""
<div class="border-solid-sm rounder-md p-3 mb-3">
  <div class="row"><div class="col-sm-12">
    <span class="input align-middle"><b>Mensal</b> - Vencimento da Guia: 20/10/2026</span>
    <button class="ml-2 br-button primary" onclick="emitir('mensal')">Emitir guia</button>
  </div></div>
  <div class="row"><div class="col-12"><br-fieldset><fieldset>
    <a class="fieldset-header" aria-label="Recolher"><legend>Guias relacionadas aguardando pagamento</legend></a>
    <div class="content">{links}</div>
  </fieldset></br-fieldset></div></div>
  <p>FGTS</p>
  <p>Total Guia {total}</p>
</div>"""


def html_guia_rapida(cards: str, modal_nova_emissao: bool = False, confirmar_solto: bool = False) -> str:
    """
    modal_nova_emissao: 'Emitir guia' abre o modal 'Gerar guia - Confirma nova emissão?' (o portal real
    só mostra esse modal quando a competência já tem guia; confirmado nos logs de 11 e 12/11/2026).
    confirmar_solto: há um botão 'Confirmar' visível fora de qualquer modal antes da emissão.
    """
    extra = ""
    if confirmar_solto:
        extra += '<button class="primary" onclick="confirmarSolto()">Confirmar</button>'
    return f"""
<html><body>
<ng-select><div class="ng-value">09/2026</div><input type="text"></ng-select>
<button class="secondary" onclick="document.getElementById('res').style.display='block'">Pesquisar</button>
{extra}
<div id="res" style="display:none">{cards}</div>
<div class="modal show" role="dialog" id="modal-gerar" style="display:none">
  <div class="modal-header">Gerar guia</div>
  <div class="modal-body">Confirma nova emissão?</div>
  <div class="modal-footer">
    <button class="secondary" onclick="cancelarModal()">Cancelar</button>
    <button class="primary" onclick="confirmarModal()">Confirmar</button>
  </div>
</div>
<script>
const MODAL = {"true" if modal_nova_emissao else "false"};
function baixar(arq) {{ window.location.href = "https://fgtsdigital.sistema.gov.br/download/" + arq; }}
function emitir(m) {{
  if (MODAL) {{ document.getElementById('modal-gerar').style.display = 'block'; return; }}
  baixar("guia.pdf");
}}
function evento(n) {{ fetch("https://fgtsdigital.sistema.gov.br/__evento/" + n).catch(() => {{}}); }}
function confirmarModal() {{ evento('reemissao_confirmada'); baixar("guia.pdf"); }}
function cancelarModal() {{ evento('cancelado'); document.getElementById('modal-gerar').style.display = 'none'; }}
function confirmarSolto() {{ evento('solto'); }}
function reimprimir(n) {{ baixar("reimpressa.pdf"); }}
</script>
</body></html>"""


def _abrir_guia_rapida(portal, tmp_path, cards, **opcoes):
    portal.paginas["/cobranca/"] = html_guia_rapida(cards, **opcoes)
    portal.paginas["/portal/servicos"] = "<html><body>servicos</body></html>"
    portal.page.goto(URL_GUIA_RAPIDA)
    return FGTSDigitalBot(page=portal.page, output_base_dir=tmp_path)


def _houve_download_de_guia(portal) -> bool:
    return any("/download/guia.pdf" in u for u in portal.requisicoes)


def test_sem_valor_esperado_nao_emite(portal, tmp_path):
    bot = _abrir_guia_rapida(portal, tmp_path, card("Mensal", "1.000,00", "mensal"))
    res = bot.emitir_guia_e_relatorios(CNPJ_ALVO, "Empresa Alfa", "09/2026", fgts_esperado=0.0)
    assert "Sem Valor de Referência" in res["status"]
    assert not _houve_download_de_guia(portal)


def test_nao_clica_emitir_fora_do_card_mensal(portal, tmp_path):
    bot = _abrir_guia_rapida(portal, tmp_path, card("Rescisória", "500,00", "rescisoria"))
    res = bot.emitir_guia_e_relatorios(CNPJ_ALVO, "Empresa Alfa", "09/2026", fgts_esperado=500.0)
    assert "Sucesso" not in res["status"]
    assert not _houve_download_de_guia(portal)


def test_emite_e_valida_guia_correta(portal, tmp_path):
    pdf = gerar_pdf(tmp_path / "src" / "guia.pdf", [
        "Guia do FGTS Digital - GFD",
        "Empregador: 12.345.678/0001-90",
        "Competencia: 09/2026",
        "Valor total: 1.000,00",
    ])
    portal.arquivos["/download/guia.pdf"] = pdf.read_bytes()
    bot = _abrir_guia_rapida(portal, tmp_path / "out", card("Mensal", "1.000,00", "mensal"))
    res = bot.emitir_guia_e_relatorios(CNPJ_ALVO, "Empresa Alfa", "09/2026", fgts_esperado=1000.0)
    assert res["status"] == "Sucesso - Guia Emitida"
    assert res["arquivo_guia"]
    salvos = list((tmp_path / "out").rglob(res["arquivo_guia"]))
    assert len(salvos) == 1 and "_rejeitados" not in str(salvos[0])


def test_guia_de_outra_empresa_e_rejeitada(portal, tmp_path):
    pdf = gerar_pdf(tmp_path / "src" / "guia.pdf", [
        "Guia do FGTS Digital - GFD",
        "Empregador: 98.765.432/0001-10",
        "Competencia: 09/2026",
        "Valor total: 1.000,00",
    ])
    portal.arquivos["/download/guia.pdf"] = pdf.read_bytes()
    bot = _abrir_guia_rapida(portal, tmp_path / "out", card("Mensal", "1.000,00", "mensal"))
    res = bot.emitir_guia_e_relatorios(CNPJ_ALVO, "Empresa Alfa", "09/2026", fgts_esperado=1000.0)
    assert "Sucesso" not in res["status"]
    assert "valida" in res["status"].lower()
    pasta = tmp_path / "out"
    aprovados = [p for p in pasta.rglob("*.pdf") if "_rejeitados" not in p.parts]
    rejeitados = [p for p in pasta.rglob("*.pdf") if "_rejeitados" in p.parts]
    assert aprovados == []
    assert len(rejeitados) == 1


# ---------------------------------------------------------------------------
# Guia já emitida (problema conhecido #13, ADR-0008): nunca reemitir;
# reimprimir a guia existente só se o valor dela for o do relatório.
# ---------------------------------------------------------------------------

def _pdf_guia(tmp_path, nome, cnpj_fmt="12.345.678/0001-90", valor="1.000,00"):
    return gerar_pdf(tmp_path / "src" / nome, [
        "GFD - Guia do FGTS Digital",
        f"Empregador: {cnpj_fmt}",
        "Competencia: 09/2026",
        f"Total da Guia: {valor}",
    ]).read_bytes()


def _evento(portal, nome) -> bool:
    """Ações do portal falso viram requisições: ficam registradas mesmo após o robô sair da tela."""
    return any(f"/__evento/{nome}" in u for u in portal.requisicoes)


def _baixou(portal, arquivo) -> bool:
    return any(f"/download/{arquivo}" in u for u in portal.requisicoes)


def test_guia_existente_com_valor_do_relatorio_e_reimpressa_sem_reemitir(portal, tmp_path):
    portal.arquivos["/download/reimpressa.pdf"] = _pdf_guia(tmp_path, "reimp.pdf")
    portal.arquivos["/download/guia.pdf"] = _pdf_guia(tmp_path, "nova.pdf")
    bot = _abrir_guia_rapida(portal, tmp_path / "out", card_com_guia_relacionada("1.000,00"))
    res = bot.emitir_guia_e_relatorios(CNPJ_ALVO, "Empresa Alfa", "09/2026", fgts_esperado=1000.0)
    assert res["status"] == "Sucesso - Guia Já Emitida (Reimpressa)"
    assert "9999999999999999-1" in res["detalhes"]
    assert not _baixou(portal, "guia.pdf")           # não clicou em 'Emitir guia'
    assert not _baixou(portal, "guia.pdf")
    salvos = list((tmp_path / "out").rglob(res["arquivo_guia"]))
    assert len(salvos) == 1 and "_rejeitados" not in str(salvos[0])


def test_guia_existente_com_valor_diferente_vai_para_rejeitados(portal, tmp_path):
    portal.arquivos["/download/reimpressa.pdf"] = _pdf_guia(tmp_path, "reimp.pdf", valor="900,00")
    bot = _abrir_guia_rapida(portal, tmp_path / "out", card_com_guia_relacionada("1.000,00"))
    res = bot.emitir_guia_e_relatorios(CNPJ_ALVO, "Empresa Alfa", "09/2026", fgts_esperado=1000.0)
    assert res["status"] == "Divergência na Guia Existente (Conferir no Portal)"
    assert not _baixou(portal, "guia.pdf")
    assert _baixou(portal, "reimpressa.pdf")
    pasta = tmp_path / "out"
    assert [p for p in pasta.rglob("*.pdf") if "_rejeitados" not in p.parts and "FGTS - " in p.name] == []
    assert len([p for p in pasta.rglob("*.pdf") if "_rejeitados" in p.parts]) == 1


def test_mais_de_uma_guia_relacionada_nao_reimprime_nem_emite(portal, tmp_path):
    cards = card_com_guia_relacionada("1.000,00", numeros=("9999999999999999-1", "9999999999999998-2"))
    bot = _abrir_guia_rapida(portal, tmp_path / "out", cards)
    res = bot.emitir_guia_e_relatorios(CNPJ_ALVO, "Empresa Alfa", "09/2026", fgts_esperado=1000.0)
    assert res["status"] == "Guia Existente - Mais de Uma Relacionada (Conferir no Portal)"
    assert not _baixou(portal, "guia.pdf")
    assert not _baixou(portal, "reimpressa.pdf")


def test_modal_confirma_nova_emissao_e_cancelado(portal, tmp_path):
    portal.arquivos["/download/guia.pdf"] = _pdf_guia(tmp_path, "nova.pdf")
    bot = _abrir_guia_rapida(portal, tmp_path / "out", card("Mensal", "1.000,00", "mensal"), modal_nova_emissao=True)
    res = bot.emitir_guia_e_relatorios(CNPJ_ALVO, "Empresa Alfa", "09/2026", fgts_esperado=1000.0)
    assert res["status"] == "Guia Existente - Reemissão Bloqueada (Conferir no Portal)"
    assert _evento(portal, "cancelado")
    assert not _evento(portal, "reemissao_confirmada")
    assert not _baixou(portal, "guia.pdf")


def test_confirmar_solto_na_tela_nao_e_clicado_e_emissao_normal_segue(portal, tmp_path):
    portal.arquivos["/download/guia.pdf"] = _pdf_guia(tmp_path, "nova.pdf")
    bot = _abrir_guia_rapida(portal, tmp_path / "out", card("Mensal", "1.000,00", "mensal"), confirmar_solto=True)
    res = bot.emitir_guia_e_relatorios(CNPJ_ALVO, "Empresa Alfa", "09/2026", fgts_esperado=1000.0)
    assert not _evento(portal, "solto")
    assert res["status"] == "Sucesso - Guia Emitida"


def test_guia_existente_sem_valor_de_referencia_nao_reimprime(portal, tmp_path):
    # Exigência de valor esperado desligada pelo operador: sem relatório não há como conferir a guia existente.
    portal.arquivos["/download/reimpressa.pdf"] = _pdf_guia(tmp_path, "reimp.pdf")
    bot = _abrir_guia_rapida(portal, tmp_path / "out", card_com_guia_relacionada("1.000,00"))
    res = bot.emitir_guia_e_relatorios(CNPJ_ALVO, "Empresa Alfa", "09/2026", fgts_esperado=0.0, exigir_valor_esperado=False)
    assert res["status"] == "Guia Existente sem Valor Conferido (Não Reimpressa)"
    assert not _baixou(portal, "reimpressa.pdf")
    assert not _baixou(portal, "guia.pdf")
