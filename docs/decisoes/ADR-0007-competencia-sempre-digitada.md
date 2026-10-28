# ADR-0007 — Competência sempre digitada pelo usuário

- **Status:** Aceita
- **Data:** 28/10/2026
- **Escopo:** `src/ui/app.py` (Painel), `src/modules/fgts_digital/parser.py` (`normalizar_competencia`), `src/core/excel_manager.py` (`competencias_divergentes`), `main.py` (`--competencia`)

## Contexto

O Painel oferecia três opções de competência — **Anterior** (marcada por padrão), **Atual** e **Manual** — calculadas pela data do computador. Em outubro/2026 o padrão era 09/2026, o que causou dúvida ("se já estamos em 10/2026, por que 09/2026?"). O padrão está alinhado ao prazo legal (o FGTS do mês é depositado até o dia 20 do mês seguinte — art. 15 da Lei 8.036/1990, na redação da Lei 14.438/2022), mas:

- o robô podia rodar numa competência que ninguém escolheu conscientemente;
- se o valor digitado em **Manual** fosse inválido (ex.: `13/2026`), a função antiga **voltava em silêncio para o mês anterior**;
- a competência de cada empresa vinda da planilha tinha prioridade sobre a da tela, sem aviso — uma planilha de outro mês seria processada no mês da planilha;
- a linha de comando usava `anterior` quando `--competencia` não era informado.

## Decisão

1. **Sem competência implícita:** o Painel tem só o campo **Competência FGTS** (MM/AAAA), que abre vazio. As opções Anterior/Atual foram removidas. Na linha de comando, `--competencia MM/AAAA` é obrigatório; `anterior`/`atual` são recusados.
2. **Validação estrita:** aceita `MM/AAAA`, `M/AAAA`, `MM-AAAA`, `MM.AAAA` e data do Excel (`AAAA-MM-DD`); mês 01–12 e ano 2000–2100. Valor inválido não inicia o robô (interface: mensagem; linha de comando: código de saída **2**).
3. **Planilha coerente:** se alguma empresa da planilha tiver competência diferente da digitada (ou inválida), o robô **não inicia** e lista as empresas (interface: mensagem; linha de comando: código de saída **3**). Empresas sem competência na planilha usam a digitada.
4. O programa **não mostra data de vencimento** (opção testada e descartada pelo usuário em 28/10/2026).

## Alternativas consideradas

| Alternativa | Por que não foi adotada |
| :--- | :--- |
| Manter "Anterior" como padrão | É o correto pelo prazo legal, mas permite rodar sem escolher a competência e gerou dúvida. |
| Mostrar o vencimento ao lado das opções | Implementado e descartado pelo usuário: o programa não precisa informar vencimento. |
| Opções visíveis, mas nenhuma marcada | Usuário preferiu um único campo digitado. |
| Usar a competência digitada para todas as empresas da planilha | Esconderia uma planilha do mês errado; o bloqueio com aviso é mais seguro. |

## Consequências

- O operador precisa digitar a competência a cada execução.
- Planilhas antigas com competência preenchida de outro mês passam a bloquear o lote até serem corrigidas.
- Testes: `tests/test_parser.py` (validação), `tests/test_excel.py` (divergência), `tests/test_ui_execucao.py` (Painel) e `tests/test_cli.py` (linha de comando, sem abrir navegador).
