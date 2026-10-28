# Registro de Decisões (ADR)

[← Índice da documentação](../README.md)

Cada decisão técnica relevante tem um arquivo `ADR-NNNN-titulo.md` com contexto, decisão, alternativas consideradas e consequências — inclusive decisões de **não** fazer algo.

| ADR | Título | Status | Data |
| :--- | :--- | :--- | :--- |
| [ADR-0001](ADR-0001-chrome-nativo-cdp-porta-9222.md) | Google Chrome nativo via CDP na porta 9222 (risco aceito para computador individual) | Aceita | 27/10/2026 |
| [ADR-0002](ADR-0002-mascaramento-de-automacao-stealth.md) | Mascaramento de sinais de automação (stealth) | Aceita | 27/10/2026 |
| [ADR-0003](ADR-0003-travas-da-emissao.md) | Emissão "na dúvida, não emite" (travas da v2.1) | Aceita | 27/10/2026 |
| [ADR-0004](ADR-0004-remocao-do-modo-pfx.md) | Remoção do modo de certificado em arquivo (.pfx) | Aceita | 27/10/2026 |
| [ADR-0005](ADR-0005-dados-de-navegador-fora-do-repositorio.md) | Dados de navegador e bancos locais fora do repositório | Aceita | 27/10/2026 |
| [ADR-0006](ADR-0006-fluxo-de-testes.md) | Fluxo de testes: automáticos sem portal real e só com dados fictícios | Aceita | 28/10/2026 |

## Modelo

```markdown
# ADR-NNNN — Título

- **Status:** Proposta | Aceita | Substituída por ADR-XXXX | Descartada
- **Data:** DD/MM/AAAA
- **Escopo:** arquivos/áreas afetados

## Contexto
## Decisão
## Alternativas consideradas
## Consequências
```
