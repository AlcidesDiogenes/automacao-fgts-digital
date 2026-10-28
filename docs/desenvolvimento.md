# Desenvolvimento

## Ambiente

| Item | Versão / observação |
| :--- | :--- |
| Sistema | Windows 10/11 64 bits, **computador de uso individual** ([ADR-0001](decisoes/ADR-0001-chrome-nativo-cdp-porta-9222.md)) |
| Python | 3.12 (venv em `venv/`) |
| Navegador | Google Chrome instalado (usado via CDP) + Chromium do Playwright (testes e reserva) |
| Certificado | A1 importado ou token A3 **instalado no Windows** (Usuário Atual) |

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

## Como rodar

| Forma | Comando |
| :--- | :--- |
| Interface (duplo clique) | `iniciar.bat` (sem console) ou `iniciar_com_console.bat` (com console para depurar) |
| Interface (terminal) | `.\venv\Scripts\python.exe main.py` |
| Linha de comando | `.\venv\Scripts\python.exe main.py --cli --competencia xx/xxxx` |
| Só conferir valores | `.\venv\Scripts\python.exe main.py --cli --conferir --competencia xx/xxxx` |

Opções da linha de comando: `--competencia xx/xxxx` (mês/ano, **obrigatória**; sem ela o programa sai com código 2, e com empresa de outra competência na planilha sai com código 3 — [ADR-0007](decisoes/ADR-0007-competencia-sempre-digitada.md)), `--excel` (planilha de empresas), `--output` (pasta de saída), `--headless`, `--conferir`. A linha de comando usa as mesmas preferências da interface (`config/parametros.json`).

## Configuração

| Arquivo | Conteúdo |
| :--- | :--- |
| `config/parametros.json` (versionado) | `regras_leitura_pdf` (quais encargos do PDF compõem o FGTS esperado), `nomenclatura` (guia, relatório FGTS, relatório consignado; tags `Competencia`, `CNPJ`, `Empresa`, também entre chaves), `pastas.output_dir` (relativo à raiz), `emissao.exigir_valor_esperado`. Salvo pela tela Parâmetros e pelo interruptor do Painel. |
| `config/.env` (fora do Git; modelo em `config/.env.example`) | `HEADLESS` (`true`/`false`). `BROWSER_TIMEOUT` é lido mas ainda não aplicado ([problemas conhecidos](problemas-conhecidos.md)). |

Caminhos do projeto são sempre absolutos a partir da raiz (`config/settings.py`: `DATA_DIR`, `LOGS_DIR`, `BROWSER_PROFILE_DIR`, `PARAMETROS_PATH`, `resolver_caminho()`), para não depender da pasta de onde o programa foi aberto.

## Estrutura de pastas

```text
config/                 settings.py, parametros.json, .env.example
data/                   (fora do Git) logs/, output/, browser_profile/, planilhas e PDFs locais
docs/                   documentação, decisoes/ (ADR), assets/ (imagens do README)
scripts/                generate_assets.py, capturar_telas.py, diagnostico/ (portal real)
src/core/               browser.py, excel_manager.py
src/modules/fgts_digital/        bot.py, parser.py, selectors.py, validacao_pdf.py
src/modules/folha_relatorio/     parser_pdf.py
src/ui/                 app.py, theme.py
src/utils/              logger.py
tests/                  somente testes automáticos (pytest)
```

## Convenções

- Código, mensagens, logs e documentação em **português**.
- **Nada de dado real** de clientes ou empregados em código, testes, documentação ou imagens: use os dados fictícios (`11.444.777/0001-61 ALFA COMERCIO FICTICIO LTDA` etc.).
- **Tkinter só na thread principal.** Outras threads usam `_na_ui()` / logger (fila). Nunca `after()` nem widgets de outra thread.
- Esperas no robô: `_elemento_visivel` / `_clicar_primeiro_disponivel` aguardam de verdade até `timeout_ms` (o `is_visible(timeout=...)` do Playwright ignora o timeout). Use `timeout_ms=0` só quando a página já foi aguardada antes.
- Emissão: qualquer dúvida → **não emitir** e registrar o motivo no status ([ADR-0003](decisoes/ADR-0003-travas-da-emissao.md)).
- Antes de mexer em login/navegador: ler [ADR-0001](decisoes/ADR-0001-chrome-nativo-cdp-porta-9222.md), [ADR-0002](decisoes/ADR-0002-mascaramento-de-automacao-stealth.md) e [ADR-0004](decisoes/ADR-0004-remocao-do-modo-pfx.md) (histórico do captcha/WAF).
- Scripts `.bat`/`.cmd`: sempre **CRLF**, **só ASCII** (sem acentos: o console usa a página de código 850 e "Automação" gravado em ANSI aparece como "AutomaþÒo") e `cd /d "%~dp0"` com aspas. O `.gitattributes` força CRLF na extração em qualquer máquina (inclusive clone sem `core.autocrlf` e "Download ZIP" do GitHub); `tests/test_scripts_windows.py` verifica tudo isso.
- Decisões relevantes viram ADR em `docs/decisoes/`.

## Fluxo de testes

Decisão registrada em [ADR-0006](decisoes/ADR-0006-fluxo-de-testes.md).

| Tipo | Onde | O que cobre |
| :--- | :--- | :--- |
| Unitário | `test_parser.py`, `test_validacao_pdf.py`, `test_logger.py`, `test_excel.py` | CNPJ, competência, valores BR, nomenclatura, valor do card Mensal, validação de PDF, log em arquivo, planilhas. |
| Integração (arquivos) | `test_pdf_parser.py` | Leitor do Domínio com **PDF sintético** no layout real. |
| Integração (navegador) | `test_bot_seguranca.py`, `test_bot_esperas.py`, `test_browser_modos.py` | Robô contra um **portal FGTS Digital falso** (Playwright com rotas interceptadas, sem rede) e abertura do navegador simulada. |
| Ponta a ponta (interface) | `test_ui_execucao.py` | Janela real com robô simulado: contadores, mensagem final, Parar, regra de threads, logs simultâneos. |
| Regressão | todos acima | Cada bug corrigido na auditoria de 27–28/10/2026 tem teste que falhava antes. |
| Manual (portal real) | `scripts/diagnostico/`, `main.py --cli --conferir` | Login real e conferência em empresas reais — roteiro abaixo. |

**Rodar tudo:** `.\venv\Scripts\python.exe -m pytest -q` (≈ 80 s). Rodar a suíte completa **antes de cada commit**; ao mexer em interface/threads, rodar várias vezes seguidas (travamentos são intermitentes). Se algum teste passar de 5 min, o `faulthandler_timeout` do `pytest.ini` imprime a pilha de todas as threads.

### Mapa de cenários

| Categoria | Coberto | Fora (por quê) |
| :--- | :--- | :--- |
| Situação normal | Emissão com guia válida, conferência, leitura do PDF com vários encargos | — |
| Limites e bordas | Tolerância R$ 0,02, valor 0, competência por extenso, CNPJ dentro de número maior, PDF sem texto, página sem documento | Viradas de ano na competência (não testado no portal) |
| Ações do usuário | Parar no meio do lote, logs enquanto o lote roda | Clique duplo em "Iniciar" (botão vira "Parar"; sem teste dedicado) |
| Dados inválidos | PDF de outra empresa, competência/valor divergentes, arquivo que não é PDF, planilha sem valor esperado | Planilha corrompida (sem teste) |
| Falhas externas | Botão de confirmação que não age, perfil que não troca, download sem evento | Queda de internet / portal fora do ar (depende do portal real) |
| Domínio incomum | Vários cards Mensais, card Rescisório, sem débitos (COB0003), empregador doméstico, consignado rescindido | eSocial pendente no portal real |
| Concorrência | Duas threads logando ao mesmo tempo | Duas instâncias do programa (porta 9222 compartilhada) |

### Roteiro manual no portal real (antes de usar uma versão nova)

1. `.\venv\Scripts\python.exe scripts\diagnostico\login_real.py` → esperado: `Resultado do Login: SUCESSO` (resolver captcha se aparecer).
2. `main.py --cli --conferir --competencia xx/xxxx --excel <planilha com 3 empresas>` → esperado: 3 trocas de perfil confirmadas e status coerentes com o portal.
3. Emitir **uma** guia de empresa conhecida pela interface → esperado: status "Sucesso - Guia Emitida" e PDF aprovado na validação (nada em `_rejeitados/`).
4. Registrar o resultado na nota do projeto (pasta Skills) e em [problemas conhecidos](problemas-conhecidos.md) se algo divergir.

## Imagens do README

| Imagem | Como gerar |
| :--- | :--- |
| `tela_*.png`, `fluxo_app.gif` (interface real) | `.\venv\Scripts\python.exe scripts\capturar_telas.py` — abre a interface com dados fictícios, deixe a tela livre durante a captura. |
| `banner.png`, `portal_multicards.png`, `demo.gif` (ilustrativos) | `.\venv\Scripts\python.exe scripts\generate_assets.py` |

Refazer sempre que a tela ou o fluxo mudar.

## Checklist de mudança

- [ ] Ler os testes que cobrem a área e rodá-los antes.
- [ ] Teste novo para regra nova ou bug corrigido (vermelho antes, verde depois).
- [ ] Suíte completa verde.
- [ ] Documentação atualizada no mesmo commit (README, `docs/`, ADR se for decisão, imagens se a tela mudou).
- [ ] Nenhum dado real (`git grep` pelos CNPJs/nomes de clientes antes de commitar).
- [ ] Commit pequeno, em português; **push só com autorização**.
