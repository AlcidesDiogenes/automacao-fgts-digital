---
trigger: model_decision
description: "Diretrizes de arquitetura de interface, simetria de cards, responsividade e sincronização de estado em CustomTkinter/Tkinter."
---

# Diretrizes de Interface Desktop (CustomTkinter & Tkinter)

## 1. Grid e Simetria de Cards Executivos (KPIs)
- Em faixas de cartões distribuídos lado a lado (ex: 3 métricas), SEMPRE configure a grade com agrupamento uniforme:
  ```python
  for col in range(num_colunas):
      frame_pai.grid_columnconfigure(col, weight=1, uniform="kpi")
  frame_pai.grid_rowconfigure(0, weight=1)
  card.grid(row=0, column=col, padx=5, sticky="nsew")
  ```
- Isso impede que a variação de texto interno altere a largura ou altura de um card individualmente, garantindo proporção e simetria matemática rigorosa.

## 2. Responsividade e Rolagem
- Telas principais com empilhamento vertical de cards de configuração devem utilizar `ctk.CTkScrollableFrame` para comportar resoluções de notebooks (ex: 1366x768) e escalas de DPI (125%/150%).
- Configure o tamanho mínimo da janela (`minsize`) com altura de segurança de até 580px–600px para nunca transbordar abaixo da barra de tarefas do Windows.

## 3. Sincronização de Estado
- Métodos de renderização de listas/tabelas e carregamento de arquivos devem sincronizar os cartões de métricas superiores (`_atualizar_cards_kpi()`) em bloco `finally`.
- Diferencie explicitamente dados brutos de entidades validadas quando houver filtros.

## 4. Preservação de Identidade Visual em Avisos
- Avisos de modos operacionais ("Só Conferir", "Simulação") não devem sobrescrever a métrica principal do card; utilize tags/badges no topo ou rótulos secundários mantendo a paleta de cores padrão do sistema.
