# 🏛️ Automação FGTS Digital Pro v2.0

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Playwright](https://img.shields.io/badge/playwright-chromium-green.svg)
![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-blueviolet.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)
![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)

Sistema corporativo de alto desempenho desenvolvido para escritórios de contabilidade e departamentos fiscais/DP. Automatiza o acesso ao portal **FGTS Digital**, gerencia procurações eletrônicas (**SPE**), audita valores de encargos e emite em lote as **Guias do FGTS Digital (GFD com PIX)** e seus respectivos **Relatórios Analíticos de Débitos**.

---

## 📑 Sumário

- [Visão Geral](#-visão-geral)
- [Principais Funcionalidades](#-principais-funcionalidades)
- [Arquitetura e Tecnologias](#-arquitetura-e-tecnologias)
- [Interface Gráfica (UI v2.0 Pro)](#-interface-gráfica-ui-v20-pro)
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
2. Lê a lista de empresas outorgantes (via Excel ou diretamente do relatório de folha de pagamento).
3. Efetua a troca de perfil para cada cliente no portal.
4. Audita se o valor no FGTS Digital bate com o relatório de encargos da folha (com suporte a FGTS de empréstimo consignado).
5. Emite as guias GFD em PDF com PIX e baixa os relatórios detalhados de débitos.
6. Organiza tudo em pastas por competência e gera uma planilha consolidada com o status de cada empresa.

---

## 🚀 Principais Funcionalidades

- **Duplo Modo de Certificado Digital**:
  - *Certificado Instalado no Windows*: Acesso automático e transparente aos certificados A1/A3 instalados na máquina, sem necessidade de selecionar arquivo ou redigitar senhas.
  - *Arquivo PFX/P12*: Carregamento seguro de arquivo físico com validação criptográfica de senha, titularidade e data de validade.
- **Importador Inteligente de Relatórios de Folha (PDF Parser)**:
  - Leitura de PDFs de encargos gerados por sistemas de folha (ex: Domínio, Fortes, Alterdata, Totvs).
  - Extração automática de CNPJs, Razões Sociais, valores de FGTS Mensal e FGTS Consignado.
- **Modo "Apenas Conferir Valores"**:
  - Consulta os débitos apurados no portal e cruza com a folha sem emitir ou recalcular guias.
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

## 🛠️ Arquitetura e Tecnologias

- **Linguagem**: Python 3.10+
- **Automação Web / Navegador**: [Playwright](https://playwright.dev/python/) com Chromium controlado por DevTools Protocol (CDP).
- **Interface Gráfica**: [CustomTkinter](https://customtkinter.tomschimansky.com/) com design system dark/light contemporâneo.
- **Processamento de Dados**: `pandas`, `openpyxl`.
- **Extração de Documentos**: `pypdf`, `pdfplumber` e expressões regulares especializadas em layouts contábeis.
- **Criptografia e Certificados**: `cryptography` (OpenSSL backend para parsing PKCS#12 e X.509).
- **Testes**: `pytest` com 100% dos testes unitários e de integração locais passando.

---

## 🖥️ Interface Gráfica (UI v2.0 Pro)

A interface foi projetada seguindo diretrizes rígidas de ergonomia e confiabilidade visual:

1. **Header Executivo**:
   - Título, versão e alternador instantâneo de tema (**Dark / Light**).
2. **Cards de Status e KPIs**:
   - **Total de Empresas**: Quantidade total de clientes na fila de processamento.
   - **Processando Atual**: Indicador em tempo real da empresa sob ação do robô.
   - **Guias / Divergências**: Contabiliza guias emitidas com sucesso (no modo padrão) ou empresas divergentes (no modo conferência).
3. **Painel de Configuração com Rolagem Integrada**:
   - Seletor de modo de certificado (Instalado vs Arquivo PFX).
   - Origem dos dados (Planilha Excel ou Relatório PDF).
   - Seleção da competência (Mês anterior, Mês atual ou Personalizada).
   - Checkbox "Apenas conferir se o valor do relatório e do sistema está igual".
   - Modelos de nomes de saída configuráveis.
4. **Console de Logs e Ações**:
   - Monitoramento linha a linha da execução.
   - Botão direto para **"Abrir Pasta de Arquivos"** gerados.

---

## 🎯 Modos de Operação

### 1. Emissão de Guias e Relatórios (Padrão)
Para cada empresa da lista:
1. Alterna o perfil do usuário logado para o CNPJ do cliente.
2. Acessa a opção **Gestão de Guias** > **Emissão de Guia Rápida**.
3. Seleciona a competência de apuração.
4. Emite a **GFD com PIX** e efetua o download do PDF.
5. Emite e baixa o **Relatório Analítico de Débitos**.
6. Salva e renomeia os arquivos na pasta da competência.

### 2. Modo "Apenas Conferir" (Auditoria de Folha)
Ativado marcando a opção **"Apenas conferir se o valor do relatório e do sistema está igual"**:
1. O robô acessa o FGTS Digital e localiza a apuração da competência.
2. Captura o valor total de débitos exibido pelo sistema federal.
3. Cruza com o valor extraído da folha de pagamento do cliente.
4. Se houver divergência, registra o valor da diferença no relatório e sinaliza no log.
5. **Nenhuma guia é emitida**, preservando o status da declaração para conferência prévia.

---

## 🔐 Autenticação e Certificados Digitais

O sistema oferece máxima flexibilidade de autenticação com o Gov.br:

| Método | Como Funciona | Recomendado para |
| :--- | :--- | :--- |
| **Certificado Instalado (Windows)** | Abre o navegador conectado ao repositório nativo do Windows (mTLS transparente). | Contadores que já possuem o certificado A1 ou token A3 configurado no computador. |
| **Arquivo PFX/P12** | O usuário seleciona o arquivo e digita a senha. O sistema valida os bytes criptográficos e autentica a sessão. | Ambientes onde o certificado não pode ser instalado de forma permanente no Windows. |

> **Nota de Segurança**: A senha e o certificado são manipulados exclusivamente em memória e nunca transmitidos externamente.

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
Você também pode disparar a automação diretamente por linha de comando:
```powershell
# Execução da competência anterior
.\venv\Scripts\python.exe main.py --cli --competencia anterior

# Execução com competência específica
.\venv\Scripts\python.exe main.py --cli --competencia 09/2026
```

---

## 📝 Personalização de Nomenclatura

Na tela da aplicação, é possível definir a estrutura do nome dos arquivos gerados:

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
│   └── settings.py             # Gerenciador central de configurações
├── data/
│   ├── logs/                   # Logs de execução (ignorado no git)
│   └── output/                 # Pastas de saída com PDFs e planilhas geradas
├── src/
│   ├── core/                   # Módulos de apoio (Excel, certificados, navegação)
│   │   ├── cert_manager.py     # Leitor e validador X.509 / PKCS#12
│   │   ├── excel_manager.py    # Geração e leitura de planilhas de lote
│   │   └── report_parser.py   # Parser de relatórios de folha e consignado
│   ├── modules/
│   │   └── fgts_digital/       # Robô de automação do portal federal
│   │       ├── bot.py          # Lógica de navegação, troca de perfil e download
│   │       └── selectors.py    # Mapeamento de seletores CSS e XPath
│   └── ui/                     # Interface Gráfica CustomTkinter
│       └── app.py              # Janela principal com responsividade e KPIs
├── tests/                      # Suíte de testes automatizados (pytest)
├── iniciar.bat                 # Script de inicialização rápida
├── main.py                     # Entrypoint da aplicação (GUI & CLI)
├── pytest.ini                  # Configurações do pytest
├── requirements.txt            # Dependências do projeto
└── README.md                   # Documentação oficial
```

---

## 🧪 Testes Automatizados

O projeto conta com testes unitários cobrindo o gerenciamento de certificados, validação de planilhas Excel, parsing de relatórios de encargos e estabilidade da interface:

```powershell
.\venv\Scripts\python.exe -m pytest -v
```

---

## 🔒 Segurança e Conformidade LGPD

* **Zero Exposição de Chaves**: Arquivos de certificados digitais (`.pfx`, `.p12`, `.pem`, `.key`, `.crt`) e arquivos `.env` com senhas estão permanentemente bloqueados pelo `.gitignore`.
* **Privacidade dos Trabalhadores**: Nenhum relatório com dados de colaboradores (CPF, salários, bases de cálculo) é mantido em repositórios remotos.
* **Isolamento de Sessão**: Cada execução limpa os dados temporários de navegação, preservando a segurança do certificado A1/A3.

---

## 👤 Autor e Manutenção

Desenvolvido para otimização e auditoria contábil digital por **Alcides Diogenes**.

Dúvidas ou sugestões? Abra uma [Issue](https://github.com/AlcidesDiogenes/automacao-fgts-digital/issues) no repositório.
