# ADR-0002 — Mascaramento de sinais de automação (stealth) no navegador

- **Status:** Aceita (código mantido como está)
- **Data:** 27/10/2026 (registro formal na auditoria de 27/10/2026; técnica adotada em 13/10/2026)
- **Escopo:** `src/core/browser.py` (`_args_base`, `_preparar_contexto`), dependência `playwright-stealth`

## Contexto

O portal FGTS Digital autentica pelo Gov.br, protegido por WAF (F5 BIG-IP / TSPD) e por desafios de captcha (Arkose Labs / hCaptcha). Navegadores com sinais de automação — `navigator.webdriver = true`, flag `--enable-automation`, barra "controlado por software automatizado" — recebem desafio com muito mais frequência ou são bloqueados. Não há API pública conhecida que permita ao procurador emitir guias do FGTS Digital em lote (**não verificado em fonte oficial**).

## Decisão

Manter o mascaramento como está hoje:

| Onde | O que é feito |
| :--- | :--- |
| Chrome nativo via CDP (modo padrão, [ADR-0001](ADR-0001-chrome-nativo-cdp-porta-9222.md)) | O Chrome é aberto **sem** flags de automação (processo normal do sistema). Nenhum script de stealth é injetado. |
| Navegador persistente do Playwright (reserva quando não há Chrome) | `ignore_default_args=["--enable-automation"]`, `--disable-blink-features=AutomationControlled`, `--disable-infobars`, `--test-type`, `navigator.webdriver` redefinido para `undefined` e `playwright-stealth` (idioma `pt-BR`). |

O robô **não** resolve captchas: quando um aparece, ele avisa no log e espera o operador resolver na janela (até 4 minutos).

## Riscos

- **Termos de uso:** contornar mecanismos de detecção de automação pode conflitar com os termos de uso do Gov.br/Serpro. **Não verificado** — a responsabilidade pelo uso é do escritório. O robô usa a credencial e as procurações do próprio contador, no mesmo ritmo aproximado de uma pessoa (pausas entre empresas).
- **Bloqueio:** o Serpro pode endurecer o WAF e passar a bloquear a sessão ou o IP; o robô então para no login (não emite nada errado).
- **Quebra silenciosa da técnica:** `playwright-stealth` é de terceiros e pode ficar defasada.
- **User-Agent fixo:** o navegador persistente declara `Chrome/128` fixo. Se a versão real do Chromium for diferente, essa divergência é ela própria um sinal de automação. Registrado como problema conhecido; não alterado nesta fase.

## Alternativas consideradas

| Alternativa | Por que não foi adotada |
| :--- | :--- |
| Remover todo o mascaramento | Captcha em praticamente todo login e falhas no fluxo (histórico de 13/10/2026). |
| Resolver captchas automaticamente (serviços de terceiros) | **Descartada:** burlar captcha não é aceitável; o operador resolve. |
| Usar só o Chrome nativo (sem o navegador do Playwright) | É o caminho padrão; o navegador do Playwright fica só como reserva quando o Chrome não está instalado. |

## Revisão

Rever esta decisão se o Serpro publicar API oficial para emissão de guias por procurador, se houver bloqueio recorrente, ou se os termos de uso forem esclarecidos.
