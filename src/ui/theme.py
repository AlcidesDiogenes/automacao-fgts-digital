"""
Módulo de Tokens de Design e Temas (UI/UX).
Padroniza cores, fontes, raios de borda e estilos visuais do aplicativo.
Inspirado em interfaces SaaS modernas e executivas (Linear, Stripe).
"""

# Paleta de Cores Corporativa (Navy & Slate)
CORES = {
    # Cores Principais
    "primary": "#1F497D",          # Azul Corporativo Escuro
    "primary_hover": "#16365C",
    "primary_light": "#EBF2FA",
    
    # Cores de Ação e Destaque
    "success": "#16A34A",          # Verde esmeralda para execução e sucesso
    "success_hover": "#15803D",
    "success_bg": "#DCFCE7",
    
    "warning": "#D97706",          # Âmbar para alertas e divergências
    "warning_hover": "#B45309",
    "warning_bg": "#FEF3C7",
    
    "danger": "#DC2626",           # Vermelho para erros e bloqueios
    "danger_hover": "#B91C1C",
    "danger_bg": "#FEE2E2",
    
    # Superfícies e Fundos (Dark Mode / Light Mode)
    "bg_sidebar_dark": "#0F172A",  # Slate 900
    "bg_sidebar_light": "#1E293B", # Slate 800
    
    "bg_main_dark": "#0B0F19",     # Fundo ultra escuro suave
    "bg_main_light": "#F8FAFC",    # Slate 50
    
    "card_dark": "#1E293B",        # Slate 800
    "card_light": "#FFFFFF",
    
    "card_border_dark": "#334155", # Slate 700
    "card_border_light": "#E2E8F0",# Slate 200
    
    # Textos
    "text_dark_primary": "#F8FAFC",
    "text_dark_muted": "#94A3B8",
    
    "text_light_primary": "#0F172A",
    "text_light_muted": "#64748B",
    
    # Terminal / Logs
    "terminal_bg": "#090D16",
    "terminal_text": "#38BDF8"
}

# Raios de Borda Padronizados
RAIO = {
    "sm": 6,
    "md": 10,
    "lg": 14,
    "pills": 20
}

# Definições Tipográficas
FONTE_FAMILIA = "Segoe UI"
FONTE_MONO = "Consolas"
