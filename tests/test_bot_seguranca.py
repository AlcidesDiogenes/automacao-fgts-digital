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


def html_guia_rapida(cards: str) -> str:
    return f"""
<html><body>
<ng-select><div class="ng-value">09/2026</div><input type="text"></ng-select>
<button class="secondary" onclick="document.getElementById('res').style.display='block'">Pesquisar</button>
<div id="res" style="display:none">{cards}</div>
<script>
window.__emitido = null;
function emitir(m) {{
  window.__emitido = m;
  window.location.href = "https://fgtsdigital.sistema.gov.br/download/guia.pdf";
}}
</script>
</body></html>"""


def _abrir_guia_rapida(portal, tmp_path, cards):
    portal.paginas["/cobranca/"] = html_guia_rapida(cards)
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
