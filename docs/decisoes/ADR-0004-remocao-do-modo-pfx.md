# ADR-0004 — Remoção do modo de certificado em arquivo (.pfx)

- **Status:** Aceita
- **Data:** 27/10/2026
- **Escopo:** `src/core/browser.py`, `src/ui/app.py`, `main.py`, `config/settings.py`, `config/.env.example`; removidos `src/auth/cert_manager.py` e `tests/test_cert_manager.py`

## Contexto

O programa oferecia dois modos de certificado: **instalado no Windows** e **arquivo .pfx** (com senha). Na auditoria v2.1 (Fase 2) o modo arquivo foi "corrigido" para injetar o `.pfx` via `client_certificates` do Playwright, porque o Chrome do sistema só enxerga certificados instalados no Windows.

Na Fase 3 constatou-se que essa abordagem **já tinha sido descartada em 13/10/2026**: o `client_certificates` cria um proxy interno no Playwright que bloqueia a resolução dos serviços de captcha (hCaptcha/Arkose), e o Gov.br responde **ERL0033800 – "Captcha inválido"**. Nas execuções reais de 27/10/2026 o Gov.br pediu captcha em 2 de 3 logins — o modo PFX falharia nesses casos.

O modo certificado do Windows foi validado no portal real (login, troca de perfil e conferência de 3 empresas).

## Decisão

Remover o modo de certificado em arquivo:

- `BrowserManager` não recebe mais `pfx_path`/`pfx_password` e **nenhum caminho do navegador usa `client_certificates`** (garantido por `tests/test_browser_modos.py`).
- Interface: a tela de Parâmetros mostra só o certificado do Windows; o cartão "Certificado Digital" mostra "Certificado do Windows".
- Linha de comando: removidos `--pfx` e `--senha`.
- `PFX_PATH`/`PFX_PASSWORD` não são mais lidos do `.env`.
- `CertManager` (validador de `.pfx`) e seus testes foram apagados: a funcionalidade deixou de existir. A dependência explícita `cryptography` saiu do `requirements.txt` (continua instalada como dependência do `pdfminer.six`).

Para usar um certificado A1 em arquivo, o usuário o **instala no Windows** (duplo clique no `.pfx` → Usuário Atual) e usa o modo único.

## Alternativas consideradas

| Alternativa | Por que não foi adotada |
| :--- | :--- |
| Manter o modo PFX com aviso | Opção que falha justamente quando aparece captcha; confunde o operador. |
| Testar com um `.pfx` real antes de decidir | O histórico já documenta a falha; o usuário optou por remover. |
| Importar o `.pfx` no repositório do Windows automaticamente | Altera o repositório de certificados do usuário sem ação explícita dele; a instalação manual é simples e fica sob controle do usuário. |

## Consequências

- Um único caminho de autenticação, já validado no portal real.
- Quem só tem o arquivo `.pfx` precisa instalá-lo no Windows antes de usar o robô.
- Linhas `PFX_PATH`/`PFX_PASSWORD` antigas em `config/.env` passam a ser ignoradas e devem ser apagadas pelo usuário (contêm a senha do certificado em texto puro).
- **Lição registrada:** antes de mudar o mecanismo de login/navegador, consultar o histórico do WAF/captcha (nota do projeto em `Skills`, seções 4–6, e [ADR-0001](ADR-0001-chrome-nativo-cdp-porta-9222.md)).
