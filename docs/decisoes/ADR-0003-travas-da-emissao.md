# ADR-0003 — Emissão "na dúvida, não emite"

- **Status:** Aceita
- **Data:** 27/10/2026 (implementada no commit `f873e40`; registrada em 28/10/2026)
- **Escopo:** `src/modules/fgts_digital/bot.py`, `src/modules/fgts_digital/validacao_pdf.py`, `src/modules/fgts_digital/selectors.py`, interruptor "Exigir valor esperado" (`src/ui/app.py`, `config/parametros.json`)

## Contexto

A auditoria v2.1 encontrou três caminhos em que o robô podia emitir ou salvar a guia errada **sem avisar**:

1. A troca de perfil por procuração era considerada bem-sucedida se nenhum alerta aparecesse — mesmo que o clique em "Selecionar" não tivesse funcionado. A guia seria emitida no perfil da empresa anterior e salva com o nome da atual.
2. Quando o evento de download não chegava, o robô copiava "o PDF mais recente da pasta temporária" — que podia ser o relatório analítico — e marcava "Sucesso".
3. Sem valor esperado da folha, não havia conferência; e um fallback clicava em qualquer botão "Emitir" visível, inclusive de guia Rescisória.

Emitir guia errada gera pagamento errado e retrabalho com o cliente; não emitir gera só uma pendência visível no relatório.

## Decisão

Toda incerteza bloqueia a emissão e vira um status explícito:

| Trava | Regra | Status quando bloqueia |
| :--- | :--- | :--- |
| Perfil | Após a troca, o modal fecha e `span.dados-perfil` exibe a raiz do CNPJ escolhido (confirmado no portal real em 27/10/2026). | `Perfil não confirmado` |
| Valor de referência | Sem valor esperado, não emite (interruptor "Exigir valor esperado", ligado por padrão). | `Sem Valor de Referência (Não Emitida)` |
| Card Mensal | O botão "Emitir guia" só é clicado dentro do card Mensal escolhido. | `Card Mensal Não Identificado (Não Emitida)` |
| Divergência | Diferença máxima de R$ 0,02 entre portal e folha (trava existente desde a v2.0). | `Divergência de Valores (Não Emitida)` |
| Relatórios | Cada relatório baixado deve conter a raiz do CNPJ e a competência; se reprovar, indica perfil/empresa errados e a guia não é emitida. | `Falha na Validação do PDF (Relatório) - Guia Não Emitida` |
| Guia | A GFD deve conter raiz do CNPJ, competência e valor do card, e não pode ser cópia de um PDF já salvo para a empresa. | `Falha na Validação do PDF (Guia)` |

PDFs reprovados vão para `_rejeitados/` e nunca ficam com o nome final.

## Alternativas consideradas

| Alternativa | Por que não foi adotada |
| :--- | :--- |
| Remover o fallback da pasta temporária | No Chrome via CDP o evento de download às vezes não chega; sem o fallback toda emissão nesse caso falharia. Mantido, restrito a arquivos criados após o clique, com hash diferente dos já salvos e conteúdo validado. |
| Permitir emissão sem valor esperado pelo maior card | Sem referência não há como saber se o card é o certo. Continua possível desligando a exigência, por decisão consciente do operador. |
| Confirmar o perfil pelo CNPJ completo | O FGTS Digital identifica o empregador pela raiz do CNPJ; a raiz basta e funciona para filiais. |

## Consequências

- Mais empresas podem terminar como "não emitida" — sempre com o motivo no relatório.
- A validação de PDF ainda não foi testada com a GFD real ([problemas conhecidos](../problemas-conhecidos.md) #4): se o texto real tiver outro formato, todas as guias serão reprovadas até ajustar.
- Testes de regressão: `tests/test_bot_seguranca.py`, `tests/test_validacao_pdf.py`.
