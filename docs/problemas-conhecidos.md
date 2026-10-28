# Problemas conhecidos e pendências

Atualizado em 28/10/2026. Status: **aberto**, **mitigado** (risco reduzido, não eliminado), **resolvido** (mantido aqui como registro de causa raiz).

## Abertos

| # | Problema | Impacto | Status / próximo passo |
| :--- | :--- | :--- | :--- |
| 1 | **Valores monetários em `float`** em todo o projeto (leitor do PDF, robô, planilhas). A regra do workspace exige `Decimal` para dinheiro. | Somas de muitos centavos podem acumular erro de arredondamento; a trava de divergência usa tolerância de R$ 0,02. | Aberto. Migração para `Decimal` é mudança grande (leitor, robô, Excel, testes); precisa de plano próprio. |
| 2 | **Formato dos valores na interface**: resumo da importação e colunas "Guia FGTS" / "FGTS Folha" mostram `R$ 9,550.40` (padrão americano) em vez de `R$ 9.550,40`. | Confusão na leitura dos valores. | Aberto (visível nas imagens do README). |
| 3 | **Leitor do Domínio com valores fixos**: competência padrão `09/2026`, vencimento `20/10/2026` e filtros `"10/2026"`, `"13/10"` na detecção da razão social (`parser_pdf.py`). | Em outras competências a razão social ou o vencimento podem sair errados. | Aberto. |
| 4 | **PDFs reais não validados**: a validação de conteúdo (CNPJ, competência, valor) foi testada só com PDFs sintéticos. | Se a GFD ou o relatório real tiverem outro formato de texto, **todos** serão reprovados (nada errado é emitido, mas o lote não conclui). | Aberto. Validar na 1ª emissão real (roteiro em [desenvolvimento](desenvolvimento.md#roteiro-manual-no-portal-real-antes-de-usar-uma-versão-nova)). |
| 5 | **Versão atual não testada no portal real**: a fila da interface e a remoção do PFX foram testadas só com robô simulado. | — | Aberto. Rodar o roteiro manual. |
| 6 | `BROWSER_TIMEOUT` do `.env` é lido mas não é passado ao navegador (usa sempre 60 s). | Configuração sem efeito. | Aberto. |
| 7 | **User-Agent fixo `Chrome/128`** no navegador de reserva do Playwright. | Divergência de versão é sinal de automação ([ADR-0002](decisoes/ADR-0002-mascaramento-de-automacao-stealth.md)). | Aberto (só afeta a reserva sem Chrome). |
| 8 | **Download de relatório por índice global**: se o botão do relatório não for achado no card Mensal, o robô usa o n-ésimo botão de PDF da página. | Poderia baixar o relatório de outro card da mesma empresa. | Mitigado: a validação confere CNPJ e competência; não diferencia cards da mesma empresa. |
| 9 | **Captcha do Gov.br** exige operador. | Lote não começa sem alguém na tela no 1º login. | Aceito ([ADR-0002](decisoes/ADR-0002-mascaramento-de-automacao-stealth.md)). |
| 10 | **Dados reais no histórico do Git** (CNPJs/nomes de clientes em testes, docstring e imagens de versões antigas; repositório público). | Exposição de clientes. | Arquivos atuais limpos em 28/10/2026; **reescrita do histórico preparada, aguardando decisão de force push do usuário**. |
| 11 | Arquivos locais com dados reais fora do Git: `data/h_copy.db`, `data/hb_copy.db` (histórico do Chrome), `data/output/teste_export_encargos.*` (exportação antiga de testes) e linhas `PFX_PATH`/`PFX_PASSWORD` no `config/.env`. | Dados sensíveis na máquina. | Aguardando o usuário apagar. |

## Resolvidos (registro de causa raiz)

| Data | Problema | Causa raiz | Correção |
| :--- | :--- | :--- | :--- |
| 27/10/2026 | Robô podia emitir no perfil da empresa anterior | Troca de perfil não era conferida | Confirmação pela barra `span.dados-perfil` ([ADR-0003](decisoes/ADR-0003-travas-da-emissao.md)) |
| 27/10/2026 | Relatório salvo como guia com status "Sucesso" | Fallback "PDF mais recente da pasta temporária" | Validação de conteúdo + hash ([ADR-0003](decisoes/ADR-0003-travas-da-emissao.md)) |
| 27/10/2026 | Log em arquivo nunca criado | `setup_logger` retornava cedo se o logger já existia | `_adicionar_handler_arquivo` |
| 27/10/2026 | Esperas do robô não esperavam | `locator.is_visible(timeout=...)` ignora o timeout | Polling real em `_primeiro_visivel` |
| 27/10/2026 | 10 s perdidos + ERROR quando não há débitos | Sem débitos (COB0003) o portal não exibe o filtro de competência | Aguarda filtro **ou** alerta |
| 27/10/2026 | Modo PFX quebrava o captcha | `client_certificates` do Playwright bloqueia os serviços de captcha (ERL0033800) | Modo removido ([ADR-0004](decisoes/ADR-0004-remocao-do-modo-pfx.md)) |
| 28/10/2026 | Janela podia congelar durante o lote | Listener de log chamava `after()` da thread do robô segurando a trava do log | Fila única da interface |
| 28/10/2026 | Suíte travava ~50% das vezes | `quit()` dentro do `update()` interno do 1º `CTk.mainloop()` era descartado | Testes usam laço de `update()` |
| 28/10/2026 | Teste do leitor do Domínio usava PDF real de clientes | — | PDF sintético no mesmo layout ([ADR-0006](decisoes/ADR-0006-fluxo-de-testes.md)) |
