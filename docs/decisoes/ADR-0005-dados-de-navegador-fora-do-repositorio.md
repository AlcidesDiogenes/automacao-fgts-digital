# ADR-0005 — Dados de navegador e bancos locais nunca entram no repositório

- **Status:** Aceita
- **Data:** 27/10/2026
- **Escopo:** `.gitignore`, pasta `data/`

## Contexto

Na auditoria v2.1 foram encontradas em `data/` duas cópias do **histórico do Google Chrome** (`h_copy.db`, `hb_copy.db`, com as tabelas `urls`, `visits` e `downloads`), provavelmente criadas durante a investigação do login no Gov.br. Histórico de navegação é dado pessoal (LGPD) e pode revelar sites de clientes e do contador. Os arquivos estavam ignorados por `data/*.db`, mas uma cópia salva fora de `data/` entraria no Git.

O perfil de navegador do robô (`data/browser_profile/`) também guarda cookies de sessão do Gov.br.

## Decisão

1. O `.gitignore` ignora `*.db` e `*.db-journal` **em qualquer pasta**: o projeto não usa banco SQLite versionado.
2. Perfis de navegador ficam em `data/*_profile/`, já ignorados.
3. Cópias de histórico, cookies ou perfis de navegador **não devem ser criadas** dentro do projeto para depuração. Diagnósticos com dados de clientes (screenshots, HTML do portal) ficam em pasta temporária fora do repositório.
4. Os arquivos existentes `data/h_copy.db` e `data/hb_copy.db` **permanecem somente no computador do usuário** (decisão do usuário em 28/10/2026), protegidos pelo `.gitignore`.

## Alternativas consideradas

| Alternativa | Por que não foi adotada |
| :--- | :--- |
| Manter só `data/*.db` | Não cobre cópias salvas em outras pastas. |
| Apagar os arquivos automaticamente | Exclusão de dados é decisão do usuário. |

## Pendências

- Nenhuma: arquivos mantidos localmente por decisão do usuário (28/10/2026).
