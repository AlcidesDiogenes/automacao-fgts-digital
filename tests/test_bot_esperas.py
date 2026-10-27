"""
Testes das esperas do robô (Playwright ignora is_visible(timeout=...)) e da
detecção imediata de 'sem débitos' na Guia Rápida (comportamento visto no portal real).
"""

import time

from src.modules.fgts_digital.bot import FGTSDigitalBot

URL = "https://fgtsdigital.sistema.gov.br/cobranca/#/gestao-guias/emissao-guia-rapida"

HTML_APARECE_DEPOIS = """
<html><body>
<script>
setTimeout(() => {
  const b = document.createElement('button');
  b.id = 'tardio'; b.textContent = 'Tardio';
  b.onclick = () => { window.__clicado = true; };
  document.body.appendChild(b);
}, 1000);
</script>
</body></html>"""

# Texto copiado do portal real (27/10/2026)
HTML_SEM_DEBITOS = """
<html><body>
<div class="br-message"><div>Não há débitos de interesse para o empregador em qualquer competência.
(27/10/2026 16:38:57) (COB0003)</div></div>
</body></html>"""


def _bot(portal, html, tmp_path):
    portal.paginas["/cobranca/"] = html
    portal.paginas["/portal/servicos"] = "<html><body>servicos</body></html>"
    portal.page.goto(URL)
    return FGTSDigitalBot(page=portal.page, output_base_dir=tmp_path)


def test_elemento_visivel_aguarda_ate_o_timeout(portal, tmp_path):
    bot = _bot(portal, HTML_APARECE_DEPOIS, tmp_path)
    assert bot._elemento_visivel(["#tardio"], timeout_ms=3000) is True


def test_timeout_zero_verifica_so_o_instante(portal, tmp_path):
    bot = _bot(portal, HTML_APARECE_DEPOIS, tmp_path)
    inicio = time.time()
    assert bot._elemento_visivel(["#tardio"], timeout_ms=0) is False
    assert time.time() - inicio < 0.5


def test_clicar_aguarda_elemento_aparecer(portal, tmp_path):
    bot = _bot(portal, HTML_APARECE_DEPOIS, tmp_path)
    assert bot._clicar_primeiro_disponivel(["#tardio"], timeout_ms=3000) is True
    assert portal.avaliar("window.__clicado") is True


def test_sem_debitos_detectado_sem_esperar_filtro(portal, tmp_path):
    bot = _bot(portal, HTML_SEM_DEBITOS, tmp_path)
    inicio = time.time()
    res = bot.emitir_guia_e_relatorios("11444777000161", "Empresa", "10/2026", apenas_conferir=True)
    assert res["status"] == "Sem Débitos / Movimento"
    assert time.time() - inicio < 8, "não deveria esperar os 10 s do filtro de competência"
