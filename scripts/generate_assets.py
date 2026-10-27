"""
Script automatizado para geração dos assets visuais do README.md
(Banners, Mockups da UI, Infográfico Multi-Cards e GIF animado da esteira).
Utiliza Playwright Headless para renderização web de alta resolução e Pillow para compilação do GIF.
"""

import os
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

ASSETS_DIR = Path("docs/assets")
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR = Path("docs/assets/temp_frames")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

HTML_BANNER = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
  body {
    width: 1200px;
    height: 380px;
    background: radial-gradient(circle at 10% 20%, #1e1b4b 0%, #0f172a 50%, #030712 100%);
    color: #f8fafc;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 0 60px;
    position: relative;
    overflow: hidden;
  }
  .glow-cyan {
    position: absolute;
    top: -80px;
    right: 50px;
    width: 380px;
    height: 380px;
    background: radial-gradient(circle, rgba(56, 189, 248, 0.22) 0%, rgba(56, 189, 248, 0) 70%);
    pointer-events: none;
  }
  .glow-indigo {
    position: absolute;
    bottom: -60px;
    left: 100px;
    width: 320px;
    height: 320px;
    background: radial-gradient(circle, rgba(99, 102, 241, 0.20) 0%, rgba(99, 102, 241, 0) 70%);
    pointer-events: none;
  }
  .tag {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(56, 189, 248, 0.12);
    border: 1px solid rgba(56, 189, 248, 0.35);
    padding: 6px 14px;
    border-radius: 9999px;
    font-size: 13px;
    font-weight: 600;
    color: #38bdf8;
    width: fit-content;
    margin-bottom: 16px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  h1 {
    font-size: 46px;
    font-weight: 800;
    line-height: 1.15;
    margin-bottom: 14px;
    background: linear-gradient(135deg, #ffffff 30%, #38bdf8 70%, #818cf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.02em;
  }
  p {
    font-size: 16px;
    line-height: 1.5;
    color: #94a3b8;
    max-width: 860px;
    margin-bottom: 24px;
  }
  .badges {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }
  .badge {
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(30, 41, 59, 0.7);
    border: 1px solid rgba(71, 85, 105, 0.4);
    backdrop-filter: blur(8px);
    padding: 8px 16px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
    color: #e2e8f0;
  }
  .badge span.icon { font-size: 16px; }
  .badge span.hl { color: #38bdf8; font-weight: 600; }
</style>
</head>
<body>
  <div class="glow-cyan"></div>
  <div class="glow-indigo"></div>
  <div class="tag">⚡ Versão 2.0 Enterprise • Produção</div>
  <h1>Automação FGTS Digital Pro</h1>
  <p>Plataforma de alta performance para escritórios contábeis e departamentos fiscais. Auditoria de encargos da folha (Sistema Domínio), integração mTLS Gov.br e emissão automatizada de GFD e relatórios analíticos em lote.</p>
  <div class="badges">
    <div class="badge"><span class="icon">🔒</span> Autenticação <span class="hl">mTLS Certificado Windows</span></div>
    <div class="badge"><span class="icon">📑</span> Leitor Exclusivo <span class="hl">Sistema Domínio</span></div>
    <div class="badge"><span class="icon">🧠</span> Seleção Inteligente <span class="hl">Multi-Cards</span></div>
    <div class="badge"><span class="icon">🛡️</span> Trava <span class="hl">Anti-Divergência</span></div>
    <div class="badge"><span class="icon">⚡</span> Motor <span class="hl">Playwright CDP</span></div>
  </div>
</body>
</html>
"""

HTML_UI = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
  body {
    width: 1280px;
    height: 760px;
    background: #0f172a;
    display: flex;
    overflow: hidden;
    color: #e2e8f0;
  }
  /* Sidebar */
  .sidebar {
    width: 270px;
    background: #090d16;
    border-right: 1px solid #1e293b;
    display: flex;
    flex-direction: column;
    padding: 24px 16px;
    flex-shrink: 0;
  }
  .brand {
    display: flex;
    flex-direction: column;
    margin-bottom: 24px;
    padding: 0 8px;
  }
  .brand-title {
    font-size: 19px;
    font-weight: 800;
    color: #38bdf8;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .brand-sub {
    font-size: 11px;
    color: #64748b;
    margin-top: 3px;
    font-weight: 500;
  }
  .nav-menu {
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex: 1;
  }
  .nav-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 14px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    color: #94a3b8;
    text-decoration: none;
    transition: all 0.2s;
  }
  .nav-item.active {
    background: #1e293b;
    color: #38bdf8;
    border-left: 3px solid #38bdf8;
  }
  .sidebar-footer {
    border-top: 1px solid #1e293b;
    padding-top: 16px;
    padding-left: 8px;
    font-size: 11px;
    color: #64748b;
  }

  /* Main Container */
  .main {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 24px 28px;
    overflow: hidden;
    gap: 20px;
  }
  .header-view {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .view-title h2 {
    font-size: 22px;
    font-weight: 700;
    color: #f8fafc;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .view-title p {
    font-size: 12px;
    color: #64748b;
    margin-top: 4px;
  }

  /* KPIs */
  .kpi-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
  }
  .kpi-card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 16px 20px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .kpi-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 11px;
    font-weight: 700;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .kpi-value {
    font-size: 22px;
    font-weight: 800;
    color: #f1f5f9;
  }
  .kpi-sub {
    font-size: 11px;
    color: #10b981;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 4px;
  }

  /* Section Card */
  .card-section {
    background: #162032;
    border: 1px solid #243247;
    border-radius: 10px;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .section-title {
    font-size: 14px;
    font-weight: 700;
    color: #e2e8f0;
    display: flex;
    align-items: center;
    gap: 8px;
    padding-bottom: 10px;
    border-bottom: 1px solid #243247;
  }
  .field-row {
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .field-label {
    font-size: 13px;
    color: #94a3b8;
    width: 140px;
  }
  .field-input {
    flex: 1;
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    color: #f8fafc;
  }
  .radio-group {
    display: flex;
    gap: 20px;
    align-items: center;
  }
  .radio-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: #cbd5e1;
  }
  .radio-dot {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    border: 2px solid #38bdf8;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .radio-dot::after {
    content: "";
    width: 8px;
    height: 8px;
    background: #38bdf8;
    border-radius: 50%;
  }

  /* Switches */
  .switch-row {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 13px;
    color: #cbd5e1;
  }
  .switch-pill {
    width: 36px;
    height: 20px;
    background: #0284c7;
    border-radius: 9999px;
    position: relative;
  }
  .switch-pill::after {
    content: "";
    position: absolute;
    top: 2px;
    right: 2px;
    width: 16px;
    height: 16px;
    background: #ffffff;
    border-radius: 50%;
  }

  /* Bottom Actions */
  .actions-row {
    margin-top: auto;
    display: flex;
    justify-content: flex-end;
    gap: 14px;
    padding-top: 10px;
  }
  .btn-primary {
    background: linear-gradient(135deg, #0284c7 0%, #2563eb 100%);
    color: #ffffff;
    border: none;
    padding: 12px 28px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 8px;
    box-shadow: 0 4px 14px rgba(2, 132, 199, 0.4);
  }
  .btn-secondary {
    background: #1e293b;
    border: 1px solid #334155;
    color: #e2e8f0;
    padding: 12px 20px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 8px;
  }
</style>
</head>
<body>
  <div class="sidebar">
    <div class="brand">
      <div class="brand-title">⚡ FGTS DIGITAL</div>
      <div class="brand-sub">Automação de Encargos Pro</div>
    </div>
    <div class="nav-menu">
      <div class="nav-item active">⚙  Painel de Controle</div>
      <div class="nav-item">📑  Importar Relatório (PDF)</div>
      <div class="nav-item">📋  Fila de Empresas</div>
      <div class="nav-item">🛠  Parâmetros</div>
      <div class="nav-item">📜  Logs & Auditoria</div>
    </div>
    <div class="sidebar-footer">
      <div>Aparência: <strong>Dark Mode</strong></div>
      <div style="margin-top: 4px;">Versão 2.0.0 • mTLS & CDP</div>
    </div>
  </div>

  <div class="main">
    <div class="header-view">
      <div class="view-title">
        <h2>⚙ Painel de Controle e Execução</h2>
        <p>Configuração de certificado, competência e acionamento do robô em lote</p>
      </div>
    </div>

    <div class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-header"><span>Empresas no Lote</span> <span>🏢</span></div>
        <div class="kpi-value">96 Empresas</div>
        <div class="kpi-sub">Fila carregada da folha</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-header"><span>Certificado Digital</span> <span>🔒</span></div>
        <div class="kpi-value">Windows A1/A3</div>
        <div class="kpi-sub">Repositório Nativo Conectado</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-header"><span>Auditoria de Valores</span> <span>🛡️</span></div>
        <div class="kpi-value">Trava Ativa</div>
        <div class="kpi-sub">Bloqueia guias divergentes</div>
      </div>
    </div>

    <div class="card-section">
      <div class="section-title">📁 Pastas e Armazenamento</div>
      <div class="field-row">
        <div class="field-label">Salvar Arquivos em:</div>
        <div class="field-input">C:/Projetos/Automações de encargos/data/output/09-2026</div>
        <div class="btn-secondary" style="padding: 8px 14px;">Alterar...</div>
      </div>
    </div>

    <div class="card-section">
      <div class="section-title">⚙️ Parâmetros da Rodada</div>
      <div class="field-row">
        <div class="field-label">Competência FGTS:</div>
        <div class="radio-group">
          <div class="radio-item"><div class="radio-dot"></div> <strong>Anterior (09/2026)</strong></div>
          <div class="radio-item"><div class="radio-dot" style="border-color:#64748b;"><div style="display:none;"></div></div> Atual (10/2026)</div>
          <div class="radio-item"><div class="radio-dot" style="border-color:#64748b;"><div style="display:none;"></div></div> Manual: [ __ / ____ ]</div>
        </div>
      </div>
      <div class="switch-row" style="margin-top: 6px;">
        <div class="switch-pill"></div>
        <div><strong>Bloquear emissão em caso de divergência de valores com a folha (Recomendado)</strong></div>
      </div>
      <div class="switch-row">
        <div class="switch-pill" style="background:#334155;"><div style="display:none;"></div></div>
        <div style="color:#94a3b8;">Apenas conferir se os valores do relatório e FGTS Digital são iguais (Sem emitir guia)</div>
      </div>
    </div>

    <div class="actions-row">
      <div class="btn-secondary">📂 Abrir Pasta de Destino</div>
      <div class="btn-secondary">🔄 Recarregar Dados</div>
      <div class="btn-primary">▶ Iniciar Emissão em Lote</div>
    </div>
  </div>
</body>
</html>
"""

HTML_MULTICARDS = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
  body {
    width: 1200px;
    height: 680px;
    background: #0b1120;
    color: #e2e8f0;
    padding: 30px 40px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }
  .header-box {
    text-align: center;
  }
  .header-box h2 {
    font-size: 26px;
    font-weight: 800;
    color: #38bdf8;
    margin-bottom: 6px;
  }
  .header-box p {
    font-size: 14px;
    color: #94a3b8;
  }
  .cards-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
    flex: 1;
  }
  .card-portal {
    background: #151d30;
    border-radius: 12px;
    padding: 22px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    position: relative;
    border: 2px solid transparent;
  }
  .card-portal.rejected {
    border-color: #ef4444;
    background: linear-gradient(180deg, rgba(239, 68, 68, 0.06) 0%, rgba(21, 29, 48, 1) 40%);
  }
  .card-portal.selected {
    border-color: #10b981;
    background: linear-gradient(180deg, rgba(16, 185, 129, 0.08) 0%, rgba(21, 29, 48, 1) 40%);
    box-shadow: 0 0 25px rgba(16, 185, 129, 0.15);
  }
  .card-badge {
    padding: 4px 12px;
    border-radius: 9999px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    width: fit-content;
  }
  .badge-rejected { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #ef4444; }
  .badge-selected { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #10b981; }

  .card-title {
    font-size: 17px;
    font-weight: 700;
    color: #f1f5f9;
  }
  .portal-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    background: #0e1526;
    border-radius: 8px;
    overflow: hidden;
  }
  .portal-table th {
    background: #1e293b;
    padding: 8px 10px;
    text-align: left;
    color: #94a3b8;
    font-weight: 600;
  }
  .portal-table td {
    padding: 8px 10px;
    border-bottom: 1px solid #1e293b;
    color: #cbd5e1;
  }
  .total-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #090e1a;
    padding: 12px 14px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 700;
  }
  .decision-box {
    margin-top: auto;
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .dec-rejected { background: rgba(239, 68, 68, 0.15); color: #fca5a5; }
  .dec-selected { background: rgba(16, 185, 129, 0.15); color: #6ee7b7; }

  .summary-bar {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 14px 24px;
    display: flex;
    justify-content: space-around;
    align-items: center;
    font-size: 14px;
  }
  .summary-item strong { color: #38bdf8; font-size: 16px; margin-left: 6px; }
</style>
</head>
<body>
  <div class="header-box">
    <h2>🧠 Seleção Inteligente de Múltiplos Cards no FGTS Digital</h2>
    <p>O robô analisa todos os blocos mensais da competência e seleciona o card de valor idêntico à soma da folha (FGTS + Consignado).</p>
  </div>

  <div class="cards-grid">
    <!-- Card 1 Rejeitado -->
    <div class="card-portal rejected">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <span class="card-badge badge-rejected">❌ Ignorado pelo Robô</span>
        <span style="font-size: 11px; color: #94a3b8;">Vencimento: 19/10/2026</span>
      </div>
      <div class="card-title">Card 1: Débito Residual / Retificadora</div>
      <table class="portal-table">
        <tr><th>Seção</th><th>Trabalhadores</th><th>Valor</th></tr>
        <tr><td>FGTS Mensal</td><td>1 colaborador</td><td>R$ 23,45</td></tr>
        <tr><td>Consignado</td><td>-</td><td>R$ 0,00</td></tr>
      </table>
      <div class="total-row">
        <span>Total Guia deste Card:</span>
        <span style="color: #f87171;">R$ 23,45</span>
      </div>
      <div class="decision-box dec-rejected">
        ⚠️ Rejeitado: Valor de R$ 23,45 não coincide com os R$ 12.345,67 apurados no Sistema Domínio.
      </div>
    </div>

    <!-- Card 2 Selecionado -->
    <div class="card-portal selected">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <span class="card-badge badge-selected">✅ Selecionado Automaticamente</span>
        <span style="font-size: 11px; color: #94a3b8;">Vencimento: 20/10/2026</span>
      </div>
      <div class="card-title">Card 2: Guia Principal Consolidada da Folha</div>
      <table class="portal-table">
        <tr><th>Seção</th><th>Trabalhadores</th><th>Valor</th></tr>
        <tr><td>FGTS Mensal</td><td>42 colaboradores</td><td>R$ 10.000,00</td></tr>
        <tr><td>Consignado</td><td>7 contratos</td><td>R$ 2.345,67</td></tr>
      </table>
      <div class="total-row">
        <span>Total Guia deste Card:</span>
        <span style="color: #34d399;">R$ 12.345,67</span>
      </div>
      <div class="decision-box dec-selected">
        🎯 Correspondência Perfeita: R$ 12.345,67 confere rigorosamente com a folha contábil (Divergência: R$ 0,00).
      </div>
    </div>
  </div>

  <div class="summary-bar">
    <div class="summary-item">Total Devedor na Tela: <strong>R$ 12.369,12</strong></div>
    <div class="summary-item">Relatório Sistema Domínio: <strong>R$ 12.345,67</strong></div>
    <div class="summary-item">Guia GFD Emitida: <strong>R$ 12.345,67</strong></div>
    <div class="summary-item">Status: <strong style="color: #34d399;">Valores Conferem (Sucesso)</strong></div>
  </div>
</body>
</html>
"""

# Slides para o GIF animado
SLIDES_HTML = [
    # Slide 1: Leitura PDF
    """
    <div class="slide-badge">ETAPA 1 DE 5</div>
    <h2>📑 Importação & Leitura Inteligente do PDF</h2>
    <p>O robô processa o relatório de encargos do Sistema Domínio (Thomson Reuters) e extrai CNPJs, Razões Sociais e bases de cálculo.</p>
    <div class="code-box">
      <div class="line"><span class="c-blue">✓ PDF Identificado:</span> Relatorio_Folha_Competencia_09-2026.pdf</div>
      <div class="line"><span class="c-green">✓ CNPJ:</span> 11.444.777/0001-61 - ALFA COMERCIO FICTICIO LTDA</div>
      <div class="line"><span class="c-yellow">✓ Encargos Apurados:</span> FGTS Mensal (R$ 10.000,00) + Consignado (R$ 2.345,67)</div>
      <div class="line"><span class="c-cyan">➜ Total Esperado para o FGTS Digital:</span> <strong>R$ 12.345,67</strong></div>
    </div>
    """,
    # Slide 2: Conexão mTLS
    """
    <div class="slide-badge">ETAPA 2 DE 5</div>
    <h2>🔒 Autenticação mTLS & Conexão Gov.br</h2>
    <p>Abertura do navegador Chromium controlado por CDP com o Certificado Digital A1/A3 instalado no Windows.</p>
    <div class="code-box">
      <div class="line"><span class="c-blue">✓ Handshake Criptográfico:</span> Conectando ao repositório nativo do Windows...</div>
      <div class="line"><span class="c-green">✓ Certificado Ativo:</span> ESCRITORIO CONTABIL EXEMPLO LTDA (Validade: 2028)</div>
      <div class="line"><span class="c-cyan">✓ Login Gov.br:</span> Sessão autenticada no FGTS Digital sem digitação de senhas.</div>
    </div>
    """,
    # Slide 3: Troca Perfil SPE
    """
    <div class="slide-badge">ETAPA 3 DE 5</div>
    <h2>👥 Troca de Perfil por Procuração Eletrônica (SPE)</h2>
    <p>Troca automática do usuário logado para a empresa cliente outorgante da procuração.</p>
    <div class="code-box">
      <div class="line"><span class="c-blue">✓ Acionando Modal:</span> 'Trocar Perfil de Acesso'...</div>
      <div class="line"><span class="c-yellow">✓ Perfil Selecionado:</span> Procurador Eletrônico</div>
      <div class="line"><span class="c-green">✓ Empresa Representada:</span> 11.444.777/0001-61</div>
      <div class="line"><span class="c-cyan">➜ Perfil Ativado com Sucesso:</span> Navegando para Emissão de Guia Rápida...</div>
    </div>
    """,
    # Slide 4: Seleção Multi-Card e Emissão
    """
    <div class="slide-badge">ETAPA 4 DE 5</div>
    <h2>🧠 Seleção do Card Correto & Emissão da GFD</h2>
    <p>O robô filtra múltiplos cards mensais, isola o card correspondente à folha e dispara o download.</p>
    <div class="code-box">
      <div class="line"><span class="c-yellow">! Alerta Detectado:</span> 2 cards mensais encontrados na tela (R$ 23,45 e R$ 12.345,67).</div>
      <div class="line"><span class="c-green">✓ Card Selecionado:</span> Card 2 (R$ 12.345,67 = R$ 10.000,00 FGTS + R$ 2.345,67 Consignado).</div>
      <div class="line"><span class="c-cyan">✓ Ação:</span> Clicando em 'Emitir guia' e confirmando modal de emissão...</div>
      <div class="line"><span class="c-green">✓ Download Concluído:</span> FGTS - 09-2026.pdf (Guia GFD salva).</div>
    </div>
    """,
    # Slide 5: Finalização e Auditoria
    """
    <div class="slide-badge" style="background:rgba(16,185,129,0.2);color:#34d399;border-color:#10b981;">ETAPA 5 DE 5 • CONCLUÍDO</div>
    <h2>📊 Auditoria de Valores & Exportação dos Arquivos</h2>
    <p>Todos os relatórios analíticos são arquivados e a planilha consolidada de auditoria é gerada.</p>
    <div class="code-box">
      <div class="line"><span class="c-green">✓ Relatório Analítico FGTS:</span> RE FGTS - 09-2026.pdf</div>
      <div class="line"><span class="c-green">✓ Relatório Analítico Consignado:</span> Consignado FGTS - 09-2026.pdf</div>
      <div class="line"><span class="c-cyan">✓ Planilha de Auditoria:</span> Auditoria_FGTS_Digital_09-2026.xlsx</div>
      <div class="line"><span class="c-green" style="font-weight:700;">➜ 96 Empresas Processadas com 100% de Sucesso e Zero Divergências!</span></div>
    </div>
    """
]

TEMPLATE_SLIDE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
  body {
    width: 900px;
    height: 480px;
    background: #090e1a;
    color: #e2e8f0;
    padding: 36px 44px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    position: relative;
    overflow: hidden;
    border: 2px solid #1e293b;
  }
  .slide-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 9999px;
    background: rgba(56, 189, 248, 0.15);
    color: #38bdf8;
    border: 1px solid rgba(56, 189, 248, 0.4);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.05em;
    width: fit-content;
    margin-bottom: 12px;
  }
  h2 {
    font-size: 26px;
    font-weight: 800;
    color: #f8fafc;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  p {
    font-size: 14px;
    color: #94a3b8;
    margin-bottom: 22px;
  }
  .code-box {
    background: #030712;
    border: 1px solid #1f293d;
    border-radius: 10px;
    padding: 18px 22px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 13px;
    line-height: 1.5;
  }
  .line { display: flex; align-items: center; gap: 8px; }
  .c-blue { color: #60a5fa; font-weight: 600; }
  .c-green { color: #34d399; font-weight: 600; }
  .c-yellow { color: #fbbf24; font-weight: 600; }
  .c-cyan { color: #38bdf8; font-weight: 600; }
  .progress-bar {
    position: absolute;
    bottom: 0;
    left: 0;
    height: 5px;
    background: linear-gradient(90deg, #0284c7, #38bdf8);
    width: {{PROGRESS}}%;
  }
</style>
</head>
<body>
  {{CONTENT}}
  <div class="progress-bar"></div>
</body>
</html>
"""

def gerar_assets():
    print("Iniciando geração de assets visuais com Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1. Gerar Banner
        print("-> Renderizando banner.png...")
        page_banner = browser.new_page(viewport={"width": 1200, "height": 380}, device_scale_factor=2)
        page_banner.set_content(HTML_BANNER)
        page_banner.wait_for_timeout(500)
        page_banner.screenshot(path=str(ASSETS_DIR / "banner.png"))
        page_banner.close()

        # 2. Gerar Mockup UI Overview
        print("-> Renderizando ui_overview.png...")
        page_ui = browser.new_page(viewport={"width": 1280, "height": 760}, device_scale_factor=2)
        page_ui.set_content(HTML_UI)
        page_ui.wait_for_timeout(500)
        page_ui.screenshot(path=str(ASSETS_DIR / "ui_overview.png"))
        page_ui.close()

        # 3. Gerar Infográfico Multi-Cards
        print("-> Renderizando portal_multicards.png...")
        page_multi = browser.new_page(viewport={"width": 1200, "height": 680}, device_scale_factor=2)
        page_multi.set_content(HTML_MULTICARDS)
        page_multi.wait_for_timeout(500)
        page_multi.screenshot(path=str(ASSETS_DIR / "portal_multicards.png"))
        page_multi.close()

        # 4. Gerar Frames do GIF
        print("-> Renderizando frames do demo.gif...")
        frames_paths = []
        page_slide = browser.new_page(viewport={"width": 900, "height": 480}, device_scale_factor=1)
        for idx, slide_html in enumerate(SLIDES_HTML, 1):
            prog = int((idx / len(SLIDES_HTML)) * 100)
            html_final = TEMPLATE_SLIDE.replace("{{CONTENT}}", slide_html).replace("{{PROGRESS}}", str(prog))
            page_slide.set_content(html_final)
            page_slide.wait_for_timeout(300)
            frame_path = TEMP_DIR / f"frame_{idx}.png"
            page_slide.screenshot(path=str(frame_path))
            frames_paths.append(frame_path)
        page_slide.close()

        browser.close()

    # 5. Compilar o GIF animado
    print("-> Compilando demo.gif...")
    images = [Image.open(f) for f in frames_paths]
    gif_path = ASSETS_DIR / "demo.gif"
    images[0].save(
        gif_path,
        save_all=True,
        append_images=images[1:],
        duration=2200,  # 2.2 segundos por slide
        loop=0
    )
    print(f"Sucesso! Todos os assets gerados em {ASSETS_DIR.resolve()}:")
    for f in ASSETS_DIR.glob("*.*"):
        print(f"  - {f.name} ({f.stat().st_size // 1024} KB)")

if __name__ == "__main__":
    gerar_assets()
