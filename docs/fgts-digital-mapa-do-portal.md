# FGTS Digital — mapa do portal e APIs internas

> Levantamento feito em 11/11/2026 por varredura **somente leitura** no portal real, com perfil de procurador, sobre as 16 empresas do relatório do Domínio. Nenhuma guia foi emitida ou reimpressa, e nada foi salvo, solicitado ou alterado. Este documento não traz dado de cliente: os resultados por empresa ficam só no PC, em `data/output/varredura_<data>/` (fora do Git).
>
> O portal muda sem aviso. Tudo aqui vale para a data acima: conferir antes de usar em código novo.

## Sumário

- [Menu principal](#menu-principal)
- [Telas de consulta](#telas-de-consulta)
- [APIs internas observadas](#apis-internas-observadas)
- [Códigos de mensagem do portal](#códigos-de-mensagem-do-portal)
- [Comportamentos não óbvios](#comportamentos-não-óbvios)
- [Como a varredura foi feita](#como-a-varredura-foi-feita)
- [Oportunidades para o projeto](#oportunidades-para-o-projeto)

## Menu principal

Tela inicial: `https://fgtsdigital.sistema.gov.br/portal/servicos`. Cada item é um `div.cardListItem` com o título em `span.title`. Ao clicar, abre `/portal/servicos/<área>`, com os subitens no mesmo formato.

| Área (rota) | Subitens | Tipo |
| :--- | :--- | :--- |
| Calamidade RS (`calamidade-rs`) | Formulário de conta bancária para restituição (Portaria MTE 729/2024) | Formulário: **não usar** |
| Gestão de Guias (`gestao-guias`) | Emissão de Guia Rápida · Emissão de Guia Parametrizada · Consulta de Guias · Emissão de Guia de Notificação · Emissão de Guia de Consignados Vencidos | Emissão + consulta |
| Remunerações para Fins Rescisórios (`ficha`) | Gestão de Histórico de Remunerações · Concluir Histórico em Lote · Importar Histórico em Lote · Histórico de Processo Trabalhista | Escrita |
| Consultas do Empregador (`consultas-empregador`) | Consulta de Vínculos · Consulta de Competências de Referência · Consulta de Guias · Consulta da Conta Virtual do Empregador | Consulta |
| Parcelamento (`parcelamento`) | Solicitação de Parcelamento · Consulta de Parcelamentos · Solicitação de Parcelamento Especial · Consulta de Parcelamentos Especiais | Escrita + consulta |
| CVE – Estorno e Restituição (`estorno`) | Solicitação de Estorno · Consulta de Estornos · Solicitação de Restituição · Consulta de Restituições · Consulta da Conta Virtual | Escrita + consulta |
| Dados do Empregador (`dados-empregador`) | Cadastro (dados da Receita), e-mail, telefone, frase de segurança, contatos adicionais | Formulário |
| Central de Mensagens (`central-mensagens`) | Caixa de entrada e arquivadas | Consulta |
| Procurações | Outorga e manutenção de procurações | Escrita |
| Notícias, Manuais e Dúvidas | Links externos | Informativo |
| Canais de Atendimento (`canais-de-atendimento`) | Formulário · Chatbot · WhatsApp | Informativo |

Os subsistemas são aplicações separadas: `cobranca/#/…` (guias, consultas, estorno), `cve/home/…` (conta virtual, restituições), `parcelamento/…`, `parcelamento-especial/…`, `extrato/…` e `consignado/…`.

## Telas de consulta

| Tela | URL | Filtros | O que mostra |
| :--- | :--- | :--- | :--- |
| Emissão de Guia Rápida | `cobranca/#/gestao-guias/emissao-guia-rapida` | Competência de apuração (`ng-select`, só lista competências com débito); tipo de débito (Mensal, Rescisório, Processo Trabalhista, Consignado) | Por competência: cards por tipo e vencimento, com "Emitir guia", **Guias relacionadas aguardando pagamento** (com "Reimprimir guia"), detalhamento e botões `aria-label="Imprimir relatório em PDF"` / `"Imprimir relatório em CSV"` |
| Consulta de Guias | `cobranca/#/gestao-guias/consulta-guias` | Situação (padrão: não expiradas), número, data de pagamento, vencimento (até 12 meses), competência (3, 6 ou 12 meses ou período), CPF de trabalhador (até 1.000, inclusive por .txt) | Guias emitidas: número, tipo, emissão, pagar até, valor, situação, arrecadação |
| Consulta de Competências de Referência | `cobranca/#/consultas-empregador/extrato/consulta-consolidada` | Período (2, 6 ou 12 meses ou personalizado); situação (Irregular/Regular); com créditos, com débitos, sem remuneração | Por competência: trabalhadores, remuneração, devido, suspenso, arrecadado, amortização, bloqueado p/ estorno, créditos, débitos e **situação** |
| Consulta de Vínculos | `cobranca/#/consultas-empregador/extrato/consulta-vinculo` | Nome, CPF, matrícula, processo, local de trabalho, com/sem vínculo | Abas Ativos / Afastados / Desligados com contagem |
| Conta Virtual do Empregador | `cve/home/extrato` | — | Movimentações de crédito, total disponível/solicitado/restituído |
| Consulta de Parcelamentos (e Especiais) | `parcelamento/consulta/…`, `parcelamento-especial/consulta/…` | Número, situação | Contratos e saldo devedor |
| Consulta de Estornos / Restituições | `cobranca/#/estorno/consulta-estorno`, `cve/home/consultar-restituicao` | Origem, documento, datas, situação | Solicitações e situação |
| Guia de Notificação / Consignados Vencidos | `cobranca/#/gestao-guias/emissao-guia-notificacao`, `…/emissao-guia-consignados-vencidos` | — | Aviso quando não há nada (códigos abaixo) |

## APIs internas observadas

As telas são Angular e buscam os dados em APIs JSON do próprio portal, na mesma sessão do navegador. Não são APIs públicas nem documentadas: podem mudar sem aviso. `<raiz>` é a raiz do CNPJ (8 dígitos) seguida do tipo de inscrição (`1` = CNPJ); `<AAAAMM>` é a competência; `13` no mês indica 13º salário (ex.: `202513`).

| Método e caminho | Retorno (campos principais) |
| :--- | :--- |
| `GET /extrato/api/v2/empregadores/<raiz>/competencias` | Lista de competências do período |
| `GET /extrato/api/v2/empregadores/<raiz>/competencias/<AAAAMM>/resumo` | `situacao` (`REGULAR`, `IRREGULAR`, `EM_BRANCO`), `qtdTrabalhadores`, `valorRemuneracao`, `valorDevido`, `valorArrecadado`, `valorDebitos`, `valorCreditos`, `semRemuneracao`, `icPendente`, `apuracoes[]` |
| `GET /cobranca/api/guia-rapida/` | Competências com débito: `competencia`, `status` (`Aberta`…), `vlTotal` |
| `GET /cobranca/api/guia-rapida/v2/<AAAAMM>` | `agrupamentos[]` por tipo e vencimento: `tipo`, `pagamentoAte`, `totalizador` (`vlMensal`, `vlRescisorio`, `vlEncargos`, `vlJuros`, `vlMulta`, `vlAtualizacaoMonetaria`, `vlTotal`), `totalConsignado`, `totalGuia`, **`guiaExistente`** (`numero`, `linkPdf`), `temGuiasRelacionadas`, `alertas[]` |
| `GET /cobranca/api/guia-rapida/agrupamento/<filtro>/guias-relacionadas` | Guias já emitidas para o card: `numeroFormatado`, `linkGuiaPdf` |
| `GET /cobranca/api/guia-rapida/agrupamento/corrigir` | Recalcula o card vencido para a data de hoje (encargos atualizados) |
| `GET /cobranca/api/folha/verificar-{notificacao-debito, consignados-vencidos, indenizacao-compensatoria, situacao-trabalhista}` | `true`/`false`: alertas do empregador |
| `GET /cobranca/api/download/previsualizar/{detalhe,consignado}-guia-rapida-{pdf,csv}/<filtro>` | Gera o relatório antes do download (`gerouDetalheGuia`) |
| `POST /cobranca/api/consultar-guias/guias` | Guias emitidas: `numero`, `tipo`, `dtEmissao`, `dtLimitePagamento`, `vlTotal`, `situacao`, `dtArrecadacao`, `origem` |
| `POST /parcelamento/api/consulta-parcelamentos/parcelamentos` e `GET /parcelamento-especial/api/consulta-parcelamentos/parcelamentos` | `listaParcelamento[]`, `totalRegistros` |
| `GET /estorno/api/empregadores/<raiz>/solicitacoes/count` | Mensagem COB0300 quando não há estorno |
| `POST /cve/restituicao/api/v1/restituicoes/listacomfiltro` | `quantidade`, `lista[]` |
| `POST /cve/restituicao/api/v1/movimentacoes/extrato` | `totalDisponivel`, `totalSolicitado`, `totalRestituido`, `lista[]` |
| `GET /cobranca/api/guia-notificacao/dados-filtro` | Mensagem COB0318 quando não há notificação |
| `GET /consignado/api/empregadores/<raiz>/competencias` | Mensagem COB0003 quando não há consignado vencido |
| `GET /portal/mensagem/v1/mensagens` | Mensagens da central |
| `GET /portal/empregador/v1/empregadores/recuperar` | Cadastro do empregador (e-mail, telefone, frase de segurança, responsável) |
| `GET /extrato/api/vinculos/{ativo,afastado,desligado}/…` | Vínculos com totais |
| `GET /cobranca/api/usuario` | Perfil ativo: empregador, procurador e lista de serviços permitidos |

A varredura lê essas respostas **ouvindo a rede do navegador** enquanto navega pelas telas (`page.on("response")`); não chama as APIs diretamente.

## Códigos de mensagem do portal

| Código | Texto | Onde |
| :--- | :--- | :--- |
| COB0003 | Não há débitos de interesse para o empregador em qualquer competência | Guia Rápida, Consignados Vencidos (já tratado no robô) |
| COB0300 | Não há solicitações de estorno do empregador em qualquer competência | Consulta de Estornos |
| COB0318 | Não há débitos notificados com saldo em aberto para o empregador | Guia de Notificação |

## Comportamentos não óbvios

1. **Sessão com contador de 30 minutos** visível no topo; navegar entre telas renova.
2. **Competência vencida é recalculada na hora** (`agrupamento/corrigir`): o card mostra juros, multa e atualização até a data de hoje, com novo vencimento.
3. **Guia já emitida aparece na Guia Rápida** ("Guias relacionadas aguardando pagamento", `guiaExistente`), com o link `<a aria-label="Reimprimir guia">`, que baixa o PDF sem gerar guia nova. Ao clicar em "Emitir guia" nesse caso, o portal pergunta "Confirma nova emissão?". Desde 12/11/2026 o robô reimprime em vez de reemitir ([ADR-0008](decisoes/ADR-0008-guia-existente-nao-e-reemitida.md)).
4. **Competência parcelada aparece como Regular** na Consulta de Competências, mesmo sem estar quitada (aviso da própria tela).
5. A lista de competências da Guia Rápida traz **todas** as competências com débito em aberto, não só a do mês.
6. Empregador pessoa física (CPF) é aceito na troca de perfil, mas o robô transforma o CPF em CNPJ (problema conhecido #12).
7. **Estrutura do card** (12/11/2026): cada agrupamento é um `div.border-solid-sm` dentro de `app-agrupamento-guia-rapida-consignado`. As linhas são: título `<b>Mensal</b> - Vencimento da Guia` + "Emitir guia"; "Guias relacionadas"; `span.titleConsignado <b>FGTS</b>` + botões PDF/CSV (detalhe da guia); `span.titleConsignado <b>Consignado</b>` + botão PDF (só quando há consignado). O texto da página inteira também contém "Mensal - Vencimento", por isso o card tem de ser o quadro, não um bloco qualquer.
8. **Relatórios em PDF**: o detalhe FGTS traz "Total da Guia (FGTS + Consignado)"; só o de Consignado traz "Qtd. Trabalhadores Consignado". No de Consignado, o extrator de texto cola a competência no CPF do trabalhador.

## Como a varredura foi feita

Script descartável, fora do repositório (não faz parte do produto). Por empresa: troca de perfil com `FGTSDigitalBot.trocar_perfil` (confirmação pela barra de perfil) → Competências 12 meses → Guia Rápida para cada competência aberta, baixando os relatórios PDF/CSV → Consulta de Guias 12 meses → Parcelamentos, Estornos, Restituições, Conta Virtual, Notificação, Consignados → Central de Mensagens → Dados do Empregador → Vínculos.

Cliques permitidos: menus, Trocar Perfil, filtros, Pesquisar/Filtrar, Fechar alertas e os botões de relatório pelo `aria-label`. Uma trava recusa qualquer rótulo com *emitir, reimprimir, salvar, solicitar, confirmar, excluir, enviar, concluir, importar*. Tempo: cerca de 3 min por empresa.

Saída local: `data/output/varredura_<data>/<documento>/resultado.json` (respostas brutas), relatórios PDF/CSV e `Varredura_FGTS_Digital.xlsx` (abas Resumo, Competencias 12m, Guia Rapida, Guias emitidas, Etapas).

## Resultado da varredura de 11/11/2026 (agregado, sem identificação)

A carteira tinha 16 empregadores (15 CNPJ e 1 CPF). **11 foram varridos por completo**. A sessão do portal expirou na 12ª empresa e o usuário decidiu fechar com as 11. Todas as trocas de perfil foram confirmadas, todas as etapas rodaram e foram baixados 35 relatórios (PDF/CSV), em cerca de 3 min por empresa.

| Achado | Empresas |
| :--- | :--- |
| Guia de 10/2026 **já emitida**, aguardando pagamento | 10 de 11 |
| Valor do portal confere com o Domínio (≤ R$ 0,02) | 10 de 11 |
| **Divergência** portal x Domínio (R$ 17,73), sem guia emitida | 1 |
| **Competência 09/2026 em aberto** (vencida, já com encargos, juros e multa recalculados pelo portal) | 2 (1 Mensal, 1 Rescisória) |
| Consignado vencido | 1 |
| Indenização compensatória sinalizada | 1 |
| Crédito disponível na Conta Virtual (CVE) | 1 |
| Estorno solicitado | 2 |
| Restituições registradas | 1 |
| Parcelamentos, notificações de débito, mensagens na central | 0 |
| E-mail, telefone e frase de segurança cadastrados | 11 de 11 |
| Competências nos últimos 12 meses: 113 regulares, 2 irregulares, 28 em branco | — |
| Guias dos últimos 12 meses: 100 pagas e individualizadas, 10 aguardando pagamento | — |

As duas competências 09/2026 em aberto não aparecem no relatório do Domínio de 10/2026, que só traz o mês. **Só a consulta ao portal mostra esse atraso.**

## Oportunidades para o projeto (priorizadas)

| # | Ideia | Valor | Esforço | Base |
| :--- | :--- | :--- | :--- | :--- |
| 1 | **Não reemitir guia existente.** Antes de emitir, ler `guiaExistente` / "Guias relacionadas" no card; se houver, baixar a guia existente (Reimprimir) ou marcar "Guia já emitida", e **nunca** confirmar "Confirma nova emissão?" sozinho. | Segurança: um segundo lote emitia outra guia para a mesma competência | Baixo | **Feito em 12/11/2026** ([ADR-0008](decisoes/ADR-0008-guia-existente-nao-e-reemitida.md)) |
| 2 | **Modo "Raio-X da carteira"** no app, a partir do script da varredura: competências irregulares, meses anteriores em aberto (com juros/multa), consignado vencido, notificação, indenização compensatória, crédito na CVE, estornos e guias não pagas, com a coluna "O que fazer" | Acha atraso que a folha do mês não mostra (2 de 11 empresas) | Médio | Esta varredura |
| 3 | **Ler valores do JSON** que o portal já carrega (`guia-rapida/v2`) em vez do texto da tela: valores exatos convertidos para `Decimal`, tipo do card, vencimento e guia existente, sem depender de seletor de layout | Menos quebra quando o portal muda; menos dependência da estrutura da tela (o card errado causou o relatório Consignado trocado, corrigido em 12/11/2026) | Médio | APIs internas acima |
| 4 | **Conferir pagamento das guias** depois do vencimento (`consultar-guias`: Aguardando Pagamento × Paga) e listar quem não pagou | Cobrança do cliente antes de gerar encargos | Baixo | Consulta de Guias |
| 5 | **Corrigir empregador CPF** na troca de perfil | Hoje 1 dos 16 empregadores não seria processado | Baixo | Problema conhecido #12 |
| 6 | **Retomar o lote quando a sessão expira** (detectar `/portal/login`, pedir novo login e continuar de onde parou) | Lotes com mais de cerca de 10 empresas | Médio | Problema conhecido #14 |
| 7 | Conferência **por trabalhador** usando o relatório CSV da Guia Rápida contra a folha | Achar a origem de divergências como a de R$ 17,73 | Alto | Relatório CSV |

A ideia #1 foi implementada em 12/11/2026. As demais não; cada uma precisa de plano e aprovação antes (regra do workspace).
