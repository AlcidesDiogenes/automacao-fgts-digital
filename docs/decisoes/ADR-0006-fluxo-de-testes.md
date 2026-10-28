# ADR-0006 — Fluxo de testes: automáticos sem portal real e só com dados fictícios

- **Status:** Aceita
- **Data:** 28/10/2026
- **Escopo:** `tests/`, `pytest.ini`, `scripts/diagnostico/`, `scripts/capturar_telas.py`

## Contexto

- O robô depende do portal FGTS Digital, que exige certificado, procurações reais e às vezes captcha — não dá para rodar a cada mudança.
- A suíte antiga misturava testes automáticos com scripts que abriam o portal real (excluídos um a um no `pytest.ini`) e lia o **PDF real de clientes** do Domínio em `data/`, com CNPJs, nomes de empresas e de empregados nas verificações. O repositório é público.
- Travamentos entre threads da interface só apareciam em parte das execuções.

## Decisão

1. **`tests/` contém só testes automáticos**, que nunca acessam a internet. `pytest` roda tudo, sem exclusões.
2. **Portal simulado:** o robô é testado contra um "FGTS Digital falso" — HTML do próprio teste servido pelo Playwright com interceptação de rotas (`tests/conftest.py`); qualquer outra requisição é abortada. A estrutura do HTML imita o portal real (ex.: `span.dados-perfil`).
3. **Somente dados fictícios** em testes, documentação e imagens. O relatório do Domínio é gerado no teste (`gerar_pdf_dominio`) no mesmo layout do real.
4. **Interface testada de verdade:** janela real com robô/navegador simulados; laço de `update()` em vez de `mainloop()`+`quit()`.
5. **Diagnóstico de travamento:** `faulthandler_timeout = 300` no `pytest.ini`.
6. **Portal real só manualmente**, por `scripts/diagnostico/` e `main.py --cli --conferir`, seguindo o roteiro de [desenvolvimento](../desenvolvimento.md#roteiro-manual-no-portal-real-antes-de-usar-uma-versão-nova).
7. **Regressão:** todo bug corrigido ganha um teste que falha sem a correção.
8. **Quando rodar:** suíte completa antes de cada commit; mudanças em interface/threads rodam a suíte várias vezes seguidas.

## Alternativas consideradas

| Alternativa | Por que não foi adotada |
| :--- | :--- |
| Testar contra o portal real em homologação | Não há ambiente de homologação conhecido para procurador; usaria dados e procurações reais. |
| Manter o PDF real só localmente (teste pulado quando ausente) | Usa dados reais de clientes e não roda em outra máquina. |
| Mocks de `Page` do Playwright | Frágeis e não testam seletores reais; o portal falso executa o robô de verdade. |
| `pytest-xdist` / processo separado para a interface | Desnecessário depois de corrigir a causa dos travamentos. |

## Consequências

- O que só o portal real revela (formato dos PDFs reais, mudanças de tela) depende do roteiro manual — ver [problemas conhecidos](../problemas-conhecidos.md).
- O HTML do portal falso precisa ser atualizado quando o portal real mudar (copiar a estrutura nova sem dados).
