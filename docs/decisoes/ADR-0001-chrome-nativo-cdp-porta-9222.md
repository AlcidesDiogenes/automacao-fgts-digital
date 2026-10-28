# ADR-0001 — Google Chrome nativo controlado via CDP na porta 9222

- **Status:** Aceita
- **Data:** 27/10/2026 (registro formal de decisão tomada em 13/10/2026; risco da porta avaliado na auditoria de 27/10/2026)
- **Escopo:** `src/core/browser.py` (`_conectar_chrome_cdp`, `abrir_chrome_nativo_para_login`)

## Contexto

O login no Gov.br com certificado digital é bloqueado ou desafiado (captcha) quando o navegador tem sinais de automação. Os testes de outubro/2026 mostraram que:

- o Chromium do Playwright com flags de automação dispara o WAF do Serpro (desafio visual Arkose/hCaptcha);
- o `client_certificates` do Playwright cria um proxy interno que bloqueia a resolução de DNS dos serviços de captcha, e o Gov.br responde **ERL0033800 – "Captcha inválido"**;
- sessões descartáveis perdem os cookies de reputação do F5 (`TSPD_101`), aumentando a frequência de captcha.

## Decisão

1. No modo **certificado instalado no Windows**, o robô abre o **Google Chrome do sistema** com `--remote-debugging-port=9222` e perfil próprio (`data/browser_profile/`), e se conecta a ele via CDP (`connect_over_cdp`). O Chrome autentica o mTLS pela pilha nativa do Windows (Schannel), com `--auto-select-certificate-for-urls` para as origens `*.acesso.gov.br` e `*.sistema.gov.br`.
2. Ao fim do lote, o robô **desconecta mas mantém a janela aberta**, para que a próxima execução reaproveite a sessão já logada (menos logins, menos captcha).
3. A porta **9222 é fixa** e continua aberta enquanto a janela estiver aberta.

## Risco aceito (avaliado em 27/10/2026)

- O Chrome escuta a porta de depuração **somente em 127.0.0.1**: não é acessível pela rede. Páginas web não conseguem usar a porta (o Chrome recusa conexões de depuração vindas de sites).
- **Qualquer programa rodando no mesmo computador** pode se conectar à porta e controlar a sessão logada como procurador: consultar empresas, trocar perfil, emitir guias e copiar os cookies da sessão.
- Em **computador de uso individual** esse risco é baixo: um programa malicioso rodando com o usuário já teria acesso ao certificado instalado no Windows e ao perfil do Chrome, com ou sem a porta.
- Em **servidor compartilhado** (Terminal Server / RDS, vários usuários conectados), o 127.0.0.1 é o mesmo para todos os usuários: **outros usuários logados poderiam controlar a sessão**. Por isso:

> ⚠️ **Condição de uso:** o programa deve rodar **apenas em computador de uso individual** (confirmado pelo usuário em 27/10/2026). Se um dia for usado em servidor compartilhado, esta decisão precisa ser revista (ver alternativas).

## Alternativas consideradas

| Alternativa | Por que não foi adotada |
| :--- | :--- |
| Porta sorteada a cada execução | Proteção pequena: a porta aparece em `netstat` para qualquer programa local. Impede reaproveitar a janela aberta entre execuções. |
| Fechar o Chrome ao fim de cada lote | Reduz de verdade a janela de exposição, mas exige login a cada lote, com mais captcha. **É a alternativa indicada se o uso passar a ser em servidor compartilhado.** |
| Chromium do Playwright com `client_certificates` | Quebra a validação do captcha do Gov.br (ERL0033800). |
| Chromium do Playwright com perfil persistente e flags anti-automação | Mantido apenas como reserva quando o Chrome não está instalado. |

## Consequências

- Primeira execução do dia pode exigir captcha resolvido pelo operador (o robô espera até 4 minutos).
- O operador não deve fechar nem usar para outras coisas a janela do Chrome aberta pelo robô durante o lote.
- Outra automação que use a porta 9222 no mesmo computador entraria em conflito com esta.
