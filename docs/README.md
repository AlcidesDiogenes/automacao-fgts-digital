# Documentação — Automação FGTS Digital Pro

| Documento | Conteúdo |
| :--- | :--- |
| [README do projeto](../README.md) | Visão geral, funcionalidades, telas, instalação e uso. |
| [Arquitetura](arquitetura.md) | Componentes, fluxo de uma empresa no lote, modelo de threads, integrações e tecnologias. |
| [Desenvolvimento](desenvolvimento.md) | Ambiente, como rodar, configuração, estrutura de pastas, convenções, **fluxo de testes**, roteiro manual no portal real, imagens do README e checklist de mudança. |
| [Problemas conhecidos](problemas-conhecidos.md) | Pendências abertas com status e registro de causas raiz já resolvidas. |
| [Decisões (ADR)](decisoes/README.md) | Decisões técnicas com contexto, alternativas e consequências. |

## Decisões registradas

- [ADR-0001](decisoes/ADR-0001-chrome-nativo-cdp-porta-9222.md) — Google Chrome nativo via CDP na porta 9222
- [ADR-0002](decisoes/ADR-0002-mascaramento-de-automacao-stealth.md) — Mascaramento de sinais de automação
- [ADR-0003](decisoes/ADR-0003-travas-da-emissao.md) — Emissão "na dúvida, não emite"
- [ADR-0004](decisoes/ADR-0004-remocao-do-modo-pfx.md) — Remoção do modo de certificado em arquivo
- [ADR-0005](decisoes/ADR-0005-dados-de-navegador-fora-do-repositorio.md) — Dados de navegador fora do repositório
- [ADR-0006](decisoes/ADR-0006-fluxo-de-testes.md) — Fluxo de testes
