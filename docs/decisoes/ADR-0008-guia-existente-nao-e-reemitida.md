# ADR-0008 — Guia já emitida não é reemitida; reimprime só se o valor for o do relatório

- **Status:** Aceita
- **Data:** 12/11/2026
- **Escopo:** `src/modules/fgts_digital/bot.py` (`emitir_guia_e_relatorios`, `_emitir_guia_gfd`, `_guias_relacionadas`, `_reimprimir_guia`, `_modal_nova_emissao`), `src/modules/fgts_digital/selectors.py` (`LINK_REIMPRIMIR_GUIA`, `MODAL_CONFIRMACAO_EMISSAO`), `tests/test_bot_seguranca.py`

## Contexto

A varredura de 11/11/2026 ([mapa do portal](../fgts-digital-mapa-do-portal.md)) mostrou que o card Mensal da Guia Rápida informa quando a competência já tem guia ("Guias relacionadas aguardando pagamento", com link **Reimprimir guia**). O robô ignorava essa informação e, quando o portal perguntava **"Gerar guia - Confirma nova emissão?"**, clicava em Confirmar sozinho. Também clicava em qualquer botão "Confirmar" que já estivesse visível antes de emitir.

Os logs do app instalado confirmaram o efeito:

- **11/11/2026:** primeiras emissões, sem nenhuma tela de confirmação.
- **12/11/2026:** o modal "Confirma nova emissão?" apareceu 3 vezes e o robô confirmou, gerando guias em duplicidade.

Também ficou confirmado no portal real (12/11/2026):

- o link é `<a aria-label="Reimprimir guia">`, com o número da guia como texto;
- o clique baixa o PDF direto, sem modal e sem gerar guia nova;
- a validação de PDF do projeto aprovou a GFD real reimpressa e recusou valor, competência e empresa errados.

O usuário definiu a regra (12/11/2026): **pode reimprimir a guia existente, desde que o valor seja igual ao do relatório.**

## Decisão

| Situação no card Mensal | O robô faz | Status |
| :--- | :--- | :--- |
| Uma guia relacionada, valor da tela conferido com o relatório (≤ R$ 0,02, a mesma tolerância de "valores iguais" da ADR-0003) | Reimprime, valida CNPJ, competência e valor no PDF e salva com o nome da guia | `Sucesso - Guia Já Emitida (Reimpressa)` |
| Uma guia relacionada, PDF reimpresso com outro valor, competência ou CNPJ | Move para `_rejeitados/` e não emite | `Divergência na Guia Existente (Conferir no Portal)` |
| Uma guia relacionada sem valor de referência (exigência desligada) ou fora da tolerância | Não reimprime nem emite | `Guia Existente sem Valor Conferido (Não Reimpressa)` |
| Mais de uma guia relacionada | Não reimprime nem emite | `Guia Existente - Mais de Uma Relacionada (Conferir no Portal)` |
| Reimpressão sem download | Não emite | `Guia Existente - Falha na Reimpressão` |
| Sem guia relacionada, mas o portal abre o modal de confirmação depois de "Emitir guia" | Clica em **Cancelar**, nunca em Confirmar | `Guia Existente - Reemissão Bloqueada (Conferir no Portal)` |

O robô nunca clica em "Confirmar" na emissão. Qualquer modal (`modal-container`, `.modal.show`, `div[role=dialog]`, `br-modal`) com "Confirmar" ou "nova emissão" depois de "Emitir guia" é tratado como reemissão. Botões "Confirmar" fora de modal são ignorados. O método `_confirmar_modal_se_houver`, que clicava em qualquer "Sim/Emitir/Ok" e não era usado, foi removido.

A conferência do valor da guia existente usa o valor da tela, que já passou pela trava de divergência contra o relatório. Assim, "igual ao relatório" segue a mesma regra de "Conferido (Valores Iguais)": diferença de até R$ 0,02.

## Alternativas consideradas

| Alternativa | Por que não foi adotada |
| :--- | :--- |
| Só avisar e não baixar nada | Deixa a pasta da empresa sem a guia; o usuário autorizou a reimpressão com valor conferido. |
| Reemitir quando o valor mudou | Gera mais de uma guia aberta para a mesma competência; decidir qual pagar é do operador. |
| Ler `guiaExistente` do JSON da API interna | Mais robusto, mas muda a forma de leitura do robô; fica para a ideia #3 do mapa do portal. A detecção pelo link da tela foi conferida no portal real. |
| Exigir valor idêntico ao centavo | Seria diferente do restante do sistema, que chama de "iguais" valores com até R$ 0,02 de diferença. |

## Consequências

- Rodar o lote de novo na mesma competência é seguro: as empresas já emitidas saem como "Guia Já Emitida (Reimpressa)", sem guia nova.
- Se a folha mudou depois da emissão, o PDF reimpresso não confere com o valor atual e cai em "Divergência na Guia Existente": o operador decide no portal.
- Se o portal mudar o rótulo do link ou do modal, a detecção prévia pode falhar. Mesmo assim, o robô **cancela** qualquer modal de confirmação (segunda proteção).
- As guias duplicadas geradas em 12/11/2026 antes desta correção precisam de conferência manual no portal (lista local em `data/output/reemissoes_2026-11-12.txt`, fora do Git).
- Testes de regressão em `tests/test_bot_seguranca.py`: falham com o código anterior (5 de 5) e passam com o novo.
