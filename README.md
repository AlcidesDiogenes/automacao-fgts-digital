<p align="center">
  <img src="docs/assets/banner.png" alt="Automação FGTS Digital Pro" width="100%">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/playwright-chromium-green.svg" alt="Playwright">
  <img src="https://img.shields.io/badge/GUI-CustomTkinter-blueviolet.svg" alt="CustomTkinter">
  <img src="https://img.shields.io/badge/status-active-success.svg" alt="Status">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey.svg" alt="License">
</p>

Sistema corporativo de alto desempenho desenvolvido para escritórios de contabilidade e departamentos fiscais/DP. Automatiza o acesso ao portal **FGTS Digital**, gerencia procurações eletrônicas (**SPE**), audita valores de encargos e emite em lote as **Guias do FGTS Digital (GFD)** e seus respectivos **Relatórios Analíticos de Débitos**.

---

## 📑 Sumário

- [Visão Geral](#-visão-geral)
- [Demonstração do Fluxo em Ação](#-demonstração-do-fluxo-em-ação)
- [Principais Funcionalidades](#-principais-funcionalidades)
- [Interface Gráfica (UI v2.0 Pro)](#-interface-gráfica-ui-v20-pro)
- [Inteligência de Reconhecimento Multi-Cards](#-inteligência-de-reconhecimento-multi-cards)
- [Arquitetura e Tecnologias](#-arquitetura-e-tecnologias)
- [Modos de Operação](#-modos-de-operação)
  - [1. Emissão de Guias e Relatórios (Padrão)](#1-emissão-de-guias-e-relatórios-padrão)
  - [2. Modo "Apenas Conferir" (Auditoria de Folha)](#2-modo-apenas-conferir-auditoria-de-folha)
- [Autenticação e Certificados Digitais](#-autenticação-e-certificados-digitais)
- [Instalação e Configuração](#-instalação-e-configuração)
- [Guia de Uso Passo a Passo](#-guia-de-uso-passo-a-passo)
- [Personalização de Nomenclatura](#-personalização-de-nomenclatura)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Testes Automatizados](#-testes-automatizados)
- [Segurança e Conformidade LGPD](#-segurança-e-conformidade-lgpd)

---

## 🌟 Visão Geral

O fechamento mensal de encargos trabalhistas exige a apuração e geração de guias para dezenas ou centenas de empresas clientes. O portal do **FGTS Digital** demanda autenticação Gov.br via mTLS, troca manual de perfil por procuração outorgada e consultas individuais.

A **Automação FGTS Digital Pro** elimina o trabalho manual repetitivo:
1. Conecta-se com o Certificado Digital do contador (instalado no Windows ou via arquivo `.pfx`).
2. Lê a lista de empresas outorgantes (via planilha Excel ou diretamente do relatório em PDF do Sistema Domínio).
3. Efetua a troca de perfil para cada cliente no portal via Procuração Eletrônica (SPE).
4. Audita se o valor no FGTS Digital bate com o relatório de encargos (com suporte consolidado a FGTS Mensal e FGTS de empréstimo consignado).
5. Emite as guias GFD em PDF e baixa os relatórios detalhados de débitos.
6. Organiza tudo em pastas por competência e gera uma planilha consolidada com o status de cada empresa.

---

## 🎬 Demonstração do Fluxo em Ação

<p align="center">
  <img src="docs/assets/demo.gif" alt="Demonstração do Fluxo de Automação" width="90%">
</p>

O GIF acima ilustra as cinco etapas executadas de forma contínua pelo robô:
1. **Importação e Leitura**: Extração precisa de CNPJs, Razões Sociais e encargos do Sistema Domínio.
2. **Conexão mTLS**: Handshake seguro com o Gov.br utilizando o repositório de certificados nativo do Windows.
3. **Troca de Perfil SPE**: Acesso automatizado à procuração de cada cliente.
4. **Seleção Inteligente**: Reconhecimento do card da guia correta mesmo quando há débitos residuais ou retificadoras.
5. **Emissão e Auditoria**: Download da GFD, relatórios analíticos em PDF e planilha Excel consolidada.

---

## 🚀 Principais Funcionalidades

- **Duplo Modo de Certificado Digital**:
  - *Certificado Instalado no Windows*: Acesso automático e transparente aos certificados A1/A3 instalados na máquina, sem necessidade de selecionar arquivo ou redigitar senhas.
  - *Arquivo PFX/P12*: Carregamento seguro de arquivo físico com validação criptográfica de senha, titularidade e data de validade.
- **Importador de Relatórios em PDF (Exclusivo Sistema Domínio)**:
  - Atualmente projetado para leitura e extração exclusiva do modelo de relatório em PDF gerado pelo **Sistema Domínio (Thomson Reuters)**.
  - Extração automática de CNPJs, Razões Sociais e consolidação precisa de encargos: **FGTS**, **FGTS 13°**, **Emp. Créd. Trab.** (Consignado Trabalhador Ativo) e **Emp. Créd. Tr. Resc.** (Consignado Rescindido).
- **Modo "Apenas Conferir Valores"**:
  - Consulta os débitos apurados no portal e cruza com os valores esperados sem emitir ou recalcular guias.
  - Alerta sobre divergências de centavos, guias já quitadas ou ausência de débitos.
- **Nomenclatura Totalmente Flexível**:
  - Padrões configuráveis para Guia FGTS, Relatório Analítico e Relatório Consignado.
  - Suporte a tags dinâmicas como `{competencia}`, `{cnpj}`, `{nome_empresa}`.
- **Painel Executivo em Tempo Real**:
  - Cards de KPI simétricos e responsivos acompanhando o progresso da fila.
  - Barra de rolagem nativa para acomodar telas de qualquer resolução (laptops a monitores ultrawide).
- **Relatório de Auditoria em Excel**:
  - Planilha analítica gerada ao final da execução detalhando cada operação, valores, diferenças e caminhos dos arquivos salvos.

---

## 🖥️ Interface Gráfica (UI v2.0 Pro)

<p align="center">
  <img src="docs/assets/ui_overview.png" alt="Visão Geral da Interface" width="95%">
</p>

A interface foi projetada seguindo diretrizes rígidas de ergonomia e confiabilidade visual, com arquitetura baseada em **Sidebar Lateral de Navegação** e **Paineis Temáticos**:

1. **Sidebar Lateral de Navegação**:
   - ⚙ **Painel de Controle**: Configuração da competência de apuração, opções de auditoria/emissão, seleção de pastas e armazenamento e acionamento do robô.
   - 📑 **Importar Relatório (PDF)**: Leitor inteligente do relatório de encargos do **Sistema Domínio** com visualização em tabela editável e exportação para Excel/PDF.
   - 📋 **Fila de Empresas**: Gestão da planilha de CNPJs carregados, contadores e status de execução.
   - 🛠 **Parâmetros**: Gestão do Certificado Digital (Windows ou Arquivo A1/PFX), regras de leitura do PDF (FGTS Mensal, Consignado e Complementares) e personalização da nomenclatura dos documentos emitidos, com persistência automática em `config/parametros.json`.
   - 📜 **Logs & Auditoria**: Console com terminal em tempo real e monitoramento dos passos do robô.
2. **Cards de Status e KPIs Executivos**:
   - **Empresas no Lote**: Quantidade de clientes na fila de processamento.
   - **Certificado Digital**: Indicador em tempo real do status e validade do certificado (Windows ou A1).
   - **Auditoria de Valores**: Indicador visual da trava anti-divergência de valores com a folha.
3. **Persistência Centralizada**:
   - Todas as configurações e regras de encargos são salvas em `config/parametros.json` e recarregadas automaticamente ao abrir o sistema.

---

## 🧠 Inteligência de Reconhecimento Multi-Cards

Em cenários reais do portal FGTS Digital, uma mesma competência pode apresentar **mais de um card de Guia Mensal** (por exemplo, quando há um débito residual de competência retificada e a guia principal da folha regular com empréstimo consignado):

<p align="center">
  <img src="docs/assets/portal_multicards.png" alt="Reconhecimento Multi-Cards no FGTS Digital" width="95%">
</p>

### Como o Robô Seleciona o Card Correto:
1. **Identificação dos Blocos**: O robô faz a varredura de todos os containers contendo o cabeçalho `Mensal - Vencimento`.
2. **Cálculo Consolidado**: Para cada card, soma as tabelas internas de **FGTS** e **Consignado**.
3. **Cruzamento de Precisão**: Compara o `Total Guia` de cada card com o valor apurado na folha do Sistema Domínio (`fgts_esperado`).
4. **Descarte de Falsas Divergências**: Ignora guias residuais ou retificadoras (ex: R$ 23,45) e foca exclusivamente no card de valor idêntico (ex: R$ 12.345,67), garantindo emissão correta sem falsos alertas.
5. **Independência de Vencimento**: A seleção independe de a data ser dia 20 ou antecipada por finais de semana e feriados.

---

## 🛠️ Arquitetura e Tecnologias

```mermaid
flowchart TD
    A["📑 Relatório em PDF (Sistema Domínio)"] --> B["⚙️ Parser Especializado (FGTS + Consignado)"]
    B --> C["📋 Fila Consolidada de Empresas"]
    C --> D["🔒 Conexão Segura Gov.br (mTLS Windows/PFX)"]
    D --> E["👥 Troca de Perfil Automática (SPE)"]
    E --> F{"🧠 Análise de Cards Mensais no Portal"}
    F -->|"Divergente / Residual (ex: R$ 23,45)"| G["❌ Descartado"]
    F -->|"Exato com a Folha (ex: R$ 12.345,67)"| H["✅ Card Selecionado"]
    H --> I["📄 Download Relatórios Analíticos (FGTS e Consignado)"]
    I --> J["⚡ Emissão Guia GFD (PDF)"]
    J --> K["📊 Auditoria Final & Planilha Excel"]
```

- **Linguagem**: Python 3.10+
- **Automação Web / Navegador**: [Playwright](https://playwright.dev/python/) com Chromium controlado por DevTools Protocol (CDP).
- **Interface Gráfica**: [CustomTkinter](https://customtkinter.tomschimansky.com/) com design system dark/light contemporâneo.
- **Processamento de Dados**: `pandas`, `openpyxl`.
- **Extração de Documentos**: `pypdf`, `pdfplumber` e expressões regulares especializadas no layout do Sistema Domínio.
- **Criptografia e Certificados**: `cryptography` (OpenSSL backend para parsing PKCS#12 e X.509).
- **Testes**: `pytest` com suíte completa de testes unitários e de integração locais.

---

## 🎯 Modos de Operação

### 1. Emissão de Guias e Relatórios (Padrão)
Para cada empresa da lista:
1. Alterna o perfil do usuário logado para o CNPJ do cliente.
2. Acessa a opção **Gestão de Guias** > **Emissão de Guia Rápida**.
3. Seleciona a competência de apuração.
4. Emite a **GFD** e efetua o download do PDF.
5. Emite e baixa o **Relatório Analítico de Débitos** (FGTS e Consignado).
6. Salva e renomeia os arquivos na pasta da competência.

### 🛡️ Travas de Segurança da Emissão (v2.1)
O robô segue a regra **"na dúvida, não emite"**. Cada empresa só tem guia emitida se passar por todas as travas:

| Trava | O que verifica | Status quando bloqueia |
| :--- | :--- | :--- |
| **Confirmação de perfil** | Após a troca por procuração, o modal fecha e a barra de perfil exibe a raiz do CNPJ escolhido. | `Perfil não confirmado` |
| **Valor de referência** | Existe valor esperado (folha/relatório) para conferir. Pode ser desligado no painel em *"Exigir valor esperado da folha para emitir a guia"*. | `Sem Valor de Referência (Não Emitida)` |
| **Card Mensal** | O botão *Emitir guia* clicado está dentro do card Mensal selecionado — nunca em card Rescisório ou residual. | `Card Mensal Não Identificado (Não Emitida)` |
| **Divergência** | Diferença entre portal e folha até R$ 0,02. | `Divergência de Valores (Não Emitida)` |
| **Conteúdo dos relatórios** | Cada relatório baixado contém a raiz do CNPJ e a competência. Se reprovar, a guia não é emitida. | `Falha na Validação do PDF (Relatório) - Guia Não Emitida` |
| **Conteúdo da guia** | A GFD baixada contém raiz do CNPJ, competência e valor do card, e não é cópia de um relatório já salvo. | `Falha na Validação do PDF (Guia)` |

PDFs reprovados nunca ficam com o nome final: são movidos para a subpasta `_rejeitados/` da empresa. No caso de `Falha na Validação do PDF (Guia)`, a guia **foi solicitada no portal** — confira manualmente no FGTS Digital.

> ✅ **Confirmação de perfil validada no portal real (27/10/2026):** o portal exibe `Empregador: 11.444.777/0001-61 | RAZÃO SOCIAL` em `span.dados-perfil`; a trava confirmou corretamente a troca para 3 empresas.
>
> ⚠️ **Validação pendente no portal real:** o formato do texto dos PDFs reais (GFD e relatórios analíticos) ainda precisa ser confirmado numa emissão real. Até lá, se os PDFs vierem em outro formato, as travas reprovam o arquivo em vez de arriscar.

### 2. Modo "Apenas Conferir" (Auditoria de Folha)
Ativado marcando a opção **"Apenas conferir se o valor do relatório e do sistema está igual"**:
1. O robô acessa o FGTS Digital e localiza a apuração da competência.
2. Captura o valor total de débitos apurados no portal.
3. Cruza com o valor extraído da folha de pagamento do cliente.
4. Se houver divergência, registra o valor da diferença no relatório e sinaliza no log.
5. **Nenhuma guia é emitida**, preservando o status da declaração para conferência prévia.

---

## 🔐 Autenticação e Certificados Digitais

O sistema oferece máxima flexibilidade de autenticação com o Gov.br:

| Método | Como Funciona | Recomendado para |
| :--- | :--- | :--- |
| **Certificado Instalado (Windows)** | Abre o navegador conectado ao repositório nativo do Windows (mTLS transparente). | Contadores que já possuem o certificado A1 ou token A3 configurado no computador. |
| **Arquivo PFX/P12** | O usuário seleciona o arquivo e digita a senha. O sistema valida o certificado (senha, validade, chave privada) e abre o **Chromium do Playwright** com o `.pfx` injetado via `client_certificates` nas origens do Gov.br e do FGTS Digital. Usa perfil próprio em `data/pfx_profile/`. | Ambientes onde o certificado não pode ser instalado de forma permanente no Windows. |

> **Nota de Segurança**: A senha e o certificado são manipulados exclusivamente em memória e nunca transmitidos externamente.
>
> **Por que o modo PFX não usa o Google Chrome?** O Chrome do sistema só enxerga certificados instalados no Windows; um arquivo `.pfx` só pode ser apresentado pelo Chromium controlado pelo Playwright. Por isso, no modo PFX a janela do Chrome na porta 9222 é ignorada.
>
> ⚠️ O modo PFX foi validado com testes automatizados, mas **ainda não com o portal real** (falta um teste com um `.pfx` válido).

---

## 📦 Instalação e Configuração

### Pré-requisitos
- **Windows 10 ou 11** (64 bits).
- **Python 3.10 ou superior** instalado e adicionado ao `PATH`.
- Google Chrome ou Chromium instalado.

### 1. Clonar o Repositório
```bash
git clone https://github.com/AlcidesDiogenes/automacao-fgts-digital.git
cd automacao-fgts-digital
```

### 2. Criar e Ativar o Ambiente Virtual
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Instalar Dependências
```powershell
pip install -r requirements.txt
playwright install chromium
```

### 4. Configurar Arquivo `.env` (Opcional)
Se desejar definir configurações padrão via linha de comando ou CLI:
```powershell
cp config/.env.example config/.env
```
Edite `config/.env` com seus caminhos preferenciais.

---

## 🚦 Guia de Uso Passo a Passo

### Inicialização Rápida no Windows
Basta dar um duplo clique no executável em lote:
- `iniciar.bat` (Abre a aplicação com interface gráfica)
- `iniciar_com_console.bat` (Abre a aplicação com janela de console auxiliar para depuração detalhada)

### Execução via Terminal (CLI)
A linha de comando usa as mesmas preferências da interface (`config/parametros.json`: nomenclatura e "exigir valor esperado"). Sem `--pfx` (e sem `PFX_PATH` no `.env`), usa o certificado instalado no Windows.
Você também pode disparar a automação diretamente por linha de comando:
```powershell
# Execução da competência anterior
.\venv\Scripts\python.exe main.py --cli --competencia anterior

# Execução com competência específica
.\venv\Scripts\python.exe main.py --cli --competencia 09/2026

# Apenas conferir valores (não emite guias)
.\venv\Scripts\python.exe main.py --cli --conferir --competencia 09/2026

# Com certificado A1 em arquivo
.\venv\Scripts\python.exe main.py --cli --pfx "C:\caminho\certificado.pfx" --senha "..." --competencia 09/2026
```

---

## 📝 Personalização de Nomenclatura

Na tela de **Parâmetros**, é possível definir a estrutura do nome dos arquivos gerados:

* **Guia FGTS**:
  - Padrão: `FGTS - {competencia}`
  - Exemplo gerado: `FGTS - 09-2026.pdf`
* **Relatório Analítico FGTS**:
  - Padrão: `RE FGTS - {competencia}`
  - Exemplo gerado: `RE FGTS - 09-2026.pdf`
* **Relatório Consignado**:
  - Padrão: `Consignado FGTS - {competencia}`
  - Exemplo gerado: `Consignado FGTS - 09-2026.pdf`

Também é possível combinar o CNPJ e o nome da empresa nas configurações avançadas.

---

## 📂 Estrutura do Projeto

```text
automacao-fgts-digital/
├── .agents/                    # Diretrizes e regras de arquitetura e UI
├── config/
│   ├── .env.example            # Modelo de configuração de variáveis
│   ├── parametros.json         # Persistência de preferências e regras
│   └── settings.py             # Gerenciador central de configurações
├── data/
│   ├── logs/                   # Logs de execução (ignorado no git)
│   └── output/                 # Pastas de saída com PDFs e planilhas geradas
├── docs/
│   └── assets/                 # Imagens, diagramas e GIFs do README
├── scripts/
│   └── generate_assets.py      # Gerador automatizado de assets visuais
├── src/
│   ├── core/                   # Módulos de apoio (Excel, certificados, navegação)
│   │   ├── cert_manager.py     # Leitor e validador X.509 / PKCS#12
│   │   ├── excel_manager.py    # Geração e leitura de planilhas de lote
│   │   └── report_parser.py   # Parser de relatórios de folha e consignado
│   ├── modules/
│   │   ├── fgts_digital/       # Robô de automação do portal federal
│   │   │   ├── bot.py          # Lógica de navegação, troca de perfil e download
│   │   │   ├── parser.py       # Extração e normalização de débitos
│   │   │   ├── selectors.py    # Mapeamento de seletores CSS e XPath
│   │   │   └── validacao_pdf.py # Conferência do conteúdo dos PDFs baixados (CNPJ, competência, valor)
│   │   └── folha_relatorio/    # Leitor de relatórios do Sistema Domínio
│   │       └── parser_pdf.py   # Parsing de PDFs e rubricas de encargos
│   └── ui/                     # Interface Gráfica CustomTkinter
│       ├── app.py              # Janela principal com responsividade e KPIs
│       └── theme.py            # Design tokens, cores e fontes
├── tests/                      # Suíte de testes automatizados (pytest)
├── iniciar.bat                 # Script de inicialização rápida
├── main.py                     # Entrypoint da aplicação (GUI & CLI)
├── pytest.ini                  # Configurações do pytest
├── requirements.txt            # Dependências do projeto
└── README.md                   # Documentação oficial
```

---

## 🧪 Testes Automatizados

O projeto conta com testes unitários cobrindo o gerenciamento de certificados, validação de planilhas Excel, parsing de relatórios de encargos e as travas de segurança da emissão:

```powershell
.\venv\Scripts\python.exe -m pytest -v
```

- `tests/test_bot_seguranca.py` roda o robô contra um **portal FGTS Digital falso** (HTML servido pelo próprio Playwright por interceptação de rotas — nenhuma requisição sai para a internet). Requer o Chromium do Playwright (`playwright install chromium`).
- `tests/test_validacao_pdf.py` gera PDFs sintéticos com `reportlab` e testa a validação de conteúdo.
- `tests/test_bot_esperas.py` testa as esperas do robô (o `is_visible(timeout=...)` do Playwright ignora o timeout) e a detecção imediata de "sem débitos".
- `tests/test_ui_execucao.py` abre a janela real com robô e navegador falsos: contadores, mensagem final, botão *Parar* e nenhuma alteração de widget fora da thread principal.
- `tests/test_browser_modos.py` confere a escolha do navegador por modo de certificado (PFX injetado via `client_certificates`, sem CDP).
- `tests/test_logger.py` garante que o arquivo `data/logs/execucao_AAAA-MM-DD.log` é criado.

---

## 🔒 Segurança e Conformidade LGPD

* **Zero Exposição de Chaves**: Arquivos de certificados digitais (`.pfx`, `.p12`, `.pem`, `.key`, `.crt`) e arquivos `.env` com senhas estão permanentemente bloqueados pelo `.gitignore`.
* **Privacidade dos Trabalhadores**: Nenhum relatório com dados de colaboradores (CPF, salários, bases de cálculo) é mantido em repositórios remotos.
* **Isolamento de Sessão**: Cada execução limpa os dados temporários de navegação, preservando a segurança do certificado A1/A3.

---

## 👤 Autor e Manutenção

Desenvolvido para otimização e auditoria contábil digital por **Alcides Diogenes**.

Dúvidas ou sugestões? Abra uma [Issue](https://github.com/AlcidesDiogenes/automacao-fgts-digital/issues) no repositório.
