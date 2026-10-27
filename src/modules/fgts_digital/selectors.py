"""
Mapeamento de seletores CSS, XPath e URLs para o portal do FGTS Digital e Gov.br.
Concentra todos os pontos de interação com o DOM para facilitar atualizações caso o layout mude.
"""

# URLs
URL_FGTS_DIGITAL = "https://fgtsdigital.sistema.gov.br"
URL_FGTS_PORTAL = "https://fgtsdigital.sistema.gov.br/portal"
URL_GOV_BR_SSO = "https://sso.acesso.gov.br"

# Login Gov.br
LOGIN_BTN_GOV_BR = [
    "button:has-text('Entrar com gov.br')",
    "a:has-text('Entrar com gov.br')",
    "button:has-text('gov.br')",
    "a:has-text('gov.br')",
    ".br-button:has-text('gov.br')",
    "button.br-button",
    "#login-button",
    "button[type='button']:has-text('Entrar')",
    "a:has-text('Entrar')"
]

LOGIN_BTN_CERTIFICADO = [
    "#login-certificate",
    "button#login-certificate",
    "button:has-text('Seu certificado digital')",
    "button:has-text('Certificado digital')",
    "button#cert-digital",
    "button[id*='cert']",
    "a:has-text('Seu certificado digital')",
    "a:has-text('Certificado digital')",
    "button.cert-digital",
    "#login-dados-certificado button"
]

CAPTCHA_DETECTORS = [
    "iframe[src*='captcha']",
    "iframe[src*='challenge']",
    "iframe[src*='hcaptcha']",
    "iframe[src*='arkose']",
    "iframe[src*='client-api']",
    "iframe[title*='desafio' i]",
    "iframe[title*='challenge' i]",
    "div[class*='captcha']",
    ".challenge-container",
    "#arkose-frame",
    "#fc-iframe-wrap",
    "div[id*='arkose']"
]

BTN_AUTORIZAR_GOV_BR = [
    "button:has-text('Autorizar')",
    "input[value='Autorizar']",
    "button.br-button:has-text('Autorizar')",
    "button#btn-autorizar"
]

# Troca de Perfil / Procuração Eletrônica
MODAL_PERFIL_CONTAINER = [
    "modal-container",
    "lib-fgtsd-modal-alterar-perfil",
    "lib-fgtsd-modal-definir-perfil",
    ".modal.show",
    "div[role='dialog']:has-text('Perfil')"
]

PERFIL_BTN_TROCAR = [
    "button.botao-barra-perfil:has-text('Trocar Perfil')",
    "button:has-text('Trocar Perfil')",
    "a:has-text('Trocar Perfil')",
    "button:has-text('Alterar Perfil')",
    "#btn-trocar-perfil"
]

PERFIL_MENU_USUARIO = [
    "button#dd-avatar-toggle",
    "#perfil-usuario",
    ".perfil-usuario",
    "button[aria-label*='Perfil']"
]

PERFIL_DROPDOWN_CONTAINER = [
    "br-select[formcontrolname='perfil'] ng-select",
    "ng-select",
    ".ng-select-container"
]

PERFIL_OPCAO_PROCURADOR = [
    ".ng-dropdown-panel .ng-option:has-text('Procurador')",
    "div[role='option']:has-text('Procurador')",
    ".ng-option:has-text('Procurador')"
]

PERFIL_INPUT_CNPJ_OUTORGANTE = [
    "input[placeholder*='Informe CNPJ ou CPF']",
    "br-input[formcontrolname='ni'] input",
    "input#cnpjOutorgante",
    "input[placeholder*='CNPJ']"
]

# Barra que exibe o perfil ativo após a troca (usada para confirmar o CNPJ selecionado).
# Confirmado no portal real em 27/10/2026: <span class="dados-perfil"> Empregador: 11.444.777/0001-61 | RAZÃO </span>
# (ao lado de <span class="dados-usuario"> Usuário (Procurador): CPF | NOME </span> e do botão 'Trocar Perfil').
PERFIL_INDICADOR_ATIVO = [
    "span.dados-perfil",
    "lib-fgtsd-barra-perfil",
    ".barra-perfil",
    "#perfil-usuario",
    ".perfil-usuario"
]

PERFIL_BTN_CONFIRMAR_TROCA = [
    ".modal-buttons button.primary",
    "button.br-button.primary:has-text('Selecionar')",
    "button.br-button.primary:has-text('Definir')",
    "button:has-text('Selecionar')",
    "button:has-text('Definir')",
    "button:has-text('Confirmar')"
]

# Menu e Cartões de Guias
CARD_GESTAO_GUIAS = [
    ".cardListItem:has-text('Gestão de Guias')",
    "span.title:has-text('Gestão de Guias')",
    "div:has-text('Gestão de Guias')",
    "a:has-text('Gestão de Guias')"
]

CARD_GUIA_RAPIDA = [
    ".cardListItem:has-text('Emissão de Guia Rápida')",
    ".cardListItem:has-text('EMISSÃO DE GUIA RÁPIDA')",
    "span.title:has-text('Guia Rápida')",
    "a:has-text('Emissão de Guia Rápida')"
]

CARD_GUIA_PARAMETRIZADA = [
    ".cardListItem:has-text('Emissão de Guia Parametrizada')",
    "span.title:has-text('Guia Parametrizada')"
]

# Pesquisa e Seleção de Competência na Guia Rápida
GUIA_RAPIDA_SELECT_COMPETENCIA = [
    "ng-select[formcontrolname='competencia']",
    "ng-select:has-text('Competência')",
    "ng-select:near(:text('Competência de Apuração'))",
    "ng-select.brx-input",
    "ng-select"
]

GUIA_RAPIDA_INPUT_COMPETENCIA = [
    "ng-select input[type='text']",
    "input[aria-autocomplete='list']"
]

GUIA_RAPIDA_BTN_PESQUISAR = [
    "button:has-text('Pesquisar')",
    "button.secondary:has-text('Pesquisar')",
    "button[type='submit']:has-text('Pesquisar')"
]

# Emissão da Guia (GFD)
BTN_EMITIR_GUIA = [
    "button:has-text('Emitir guia')",
    "button:has-text('Emitir Guia')",
    "button:has-text('Gerar Guia')",
    "button.primary:has-text('Emitir')",
    "button#btnEmitirGuia",
    "button.br-button:has-text('Emitir')"
]

# Captura de Valor Total Apurado na Tela de Guia Rápida
CAMPOS_VALOR_TOTAL_TELA = [
    "*:has-text('Total Guia') + *",
    "*:has-text('Total Devedor') + *",
    "div:has-text('Total Guia') ~ div",
    "div:has-text('Total Devedor') ~ div",
    ".valor-total",
    ".total-recolher",
    "td.valor-total",
    "tfoot td.valor",
    "label:has-text('Total') + *",
    ".resumo-valores .valor",
    "span.badge-valor"
]

# Ícones / Botões de Download de Relatórios PDF (FGTS e Consignado)
BTN_RELATORIO_PDF_FGTS = [
    "h2:has-text('FGTS') ~ * button:has(.fa-file-pdf)",
    "div:has-text('FGTS') button[title*='PDF' i]",
    "div:has-text('FGTS') button:has(i.fa-file-pdf)",
    "div:has-text('FGTS') .fa-file-pdf",
    "button[title*='PDF do FGTS' i]",
    "button[aria-label*='PDF do FGTS' i]"
]

BTN_RELATORIO_PDF_CONSIGNADO = [
    "h2:has-text('Consignado') ~ * button:has(.fa-file-pdf)",
    "div:has-text('Consignado') button[title*='PDF' i]",
    "div:has-text('Consignado') button:has(i.fa-file-pdf)",
    "div:has-text('Consignado') .fa-file-pdf",
    "button[title*='PDF do Consignado' i]",
    "button[aria-label*='PDF do Consignado' i]"
]

BTN_BAIXAR_RELATORIO_ANALITICO = [
    "button:has-text('Relatório Analítico')",
    "a:has-text('Relatório Analítico')",
    "button:has-text('Baixar Relatório')",
    "button:has-text('Exportar PDF')"
]

BTN_FECHAR_AVISO = [
    "button:has-text('Fechar')",
    ".br-modal button:has-text('Fechar')",
    "button.circle:has-text('Fechar')"
]

BTN_ACEITAR_COOKIES = [
    "button:has-text('Aceitar')",
    ".br-cookiebar button:has-text('Aceitar')"
]

# Alertas e mensagens de status
ALERTA_SEM_DEBITOS = [
    "div:has-text('Não há débitos de interesse')",
    "div:has-text('COB0003')",
    "div:has-text('Não existem débitos apurados')",
    "div:has-text('Sem movimento para a competência')",
    "div:has-text('Não foram encontrados débitos')",
    ".alerta-sem-debitos"
]

ALERTA_ESOCIAL_PENDENTE = [
    "div:has-text('eSocial não transmitido')",
    "div:has-text('folha de pagamento pendente')",
    "div:has-text('Débito não apurado no eSocial')"
]

ALERTA_PROCURACAO_INVALIDA = [
    "div:has-text('Não possui procuração')",
    "div:has-text('Procuração vencida ou inexistente')",
    "div:has-text('Usuário não autorizado para este CNPJ')",
    "div:has-text('não possui procuração eletrônica ativa')"
]

