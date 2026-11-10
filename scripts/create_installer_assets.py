"""
Script para geração automática dos assets visuais do instalador Windows:
- assets/icon.ico (ícone multi-resolução para o executável e instalador)
- assets/icon.png (ícone em alta resolução para a interface)
- assets/wizard_header.bmp (cabeçalho 55x58 para Inno Setup)
- assets/wizard_welcome.bmp (banner lateral 164x314 para Inno Setup)
"""

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def criar_icone_alta_resolucao(tamanho=512) -> Image.Image:
    """Cria o ícone oficial do FGTS Digital em altíssima resolução com supersampling."""
    img = Image.new("RGBA", (tamanho, tamanho), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Cores
    bg_start = (15, 23, 42)     # Slate 900
    bg_end = (30, 41, 59)       # Slate 800
    border_color = (56, 189, 248) # Sky 400
    accent_blue = (2, 132, 199)   # Sky 600
    gold_bolt = (56, 189, 248)    # Cyan bolt

    # Desenhar fundo squircle com gradiente sutil
    padding = tamanho * 0.06
    raio = tamanho * 0.22
    
    # Borda externa com brilho (glow)
    draw.rounded_rectangle(
        [padding - 4, padding - 4, tamanho - padding + 4, tamanho - padding + 4],
        radius=raio + 4,
        fill=(56, 189, 248, 40)
    )
    
    # Borda principal
    draw.rounded_rectangle(
        [padding, padding, tamanho - padding, tamanho - padding],
        radius=raio,
        fill=bg_start,
        outline=border_color,
        width=int(tamanho * 0.025)
    )

    # Detalhe geométrico de fundo (círculo sutil translúcido)
    centro = tamanho / 2
    r_circulo = tamanho * 0.28
    draw.ellipse(
        [centro - r_circulo, centro - r_circulo, centro + r_circulo, centro + r_circulo],
        fill=(2, 132, 199, 45),
        outline=(56, 189, 248, 80),
        width=int(tamanho * 0.01)
    )

    # Desenho do Raio Estilizado (⚡) de alta precisão
    # Coordenadas relativas ao centro
    escala = tamanho * 0.55
    pontos_raio = [
        (centro + escala * 0.08, centro - escala * 0.48),  # Topo
        (centro - escala * 0.26, centro - escala * 0.02),  # Meio-esquerda
        (centro - escala * 0.02, centro - escala * 0.02),  # Reentrância
        (centro - escala * 0.16, centro + escala * 0.48),  # Ponta inferior
        (centro + escala * 0.26, centro + escala * 0.02),  # Meio-direita
        (centro + escala * 0.02, centro + escala * 0.02),  # Reentrância direita
    ]

    # Sombra do raio
    pontos_sombra = [(x + tamanho * 0.015, y + tamanho * 0.015) for x, y in pontos_raio]
    draw.polygon(pontos_sombra, fill=(2, 44, 84, 180))

    # Raio em preenchimento brilhante
    draw.polygon(pontos_raio, fill=(56, 189, 248, 255))
    draw.line(pontos_raio + [pontos_raio[0]], fill=(255, 255, 255, 220), width=int(tamanho * 0.012))

    return img


def gerar_pacote_assets():
    print("🎨 Gerando pacote de assets visuais para o instalador...")
    
    # 1. Ícone em 512x512
    icone_512 = criar_icone_alta_resolucao(512)
    
    # Salvar PNG
    png_path = ASSETS_DIR / "icon.png"
    icone_512.resize((256, 256), Image.Resampling.LANCZOS).save(png_path, format="PNG")
    print(f" -> Salvo: {png_path}")

    # Salvar ICO multi-resolução
    ico_path = ASSETS_DIR / "icon.ico"
    tamanhos_ico = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icone_512.save(
        ico_path,
        format="ICO",
        sizes=tamanhos_ico
    )
    print(f" -> Salvo: {ico_path} (Multi-resolução: 16px a 256px)")

    # 2. Inno Setup Wizard Small Image (Header: 55x58)
    header_img = Image.new("RGB", (55, 58), (15, 23, 42))
    header_draw = ImageDraw.Draw(header_img)
    # Linha divisória inferior sutil
    header_draw.line([(0, 57), (55, 57)], fill=(56, 189, 248), width=1)
    # Mini ícone centralizado
    mini_ico = icone_512.resize((44, 44), Image.Resampling.LANCZOS)
    header_img.paste(mini_ico, (5, 6), mini_ico)
    header_path = ASSETS_DIR / "wizard_header.bmp"
    header_img.save(header_path, format="BMP")
    print(f" -> Salvo: {header_path}")

    # 3. Inno Setup Wizard Image (Welcome/Finish banner: 164x314)
    welcome_img = Image.new("RGB", (164, 314), (15, 23, 42))
    welcome_draw = ImageDraw.Draw(welcome_img)
    
    # Gradiente vertical simulado
    for y in range(314):
        r = int(15 + (y / 314) * 15)
        g = int(23 + (y / 314) * 18)
        b = int(42 + (y / 314) * 20)
        welcome_draw.line([(0, y), (164, y)], fill=(r, g, b))

    # Adicionar ícone centralizado na metade superior
    ico_welcome = icone_512.resize((96, 96), Image.Resampling.LANCZOS)
    welcome_img.paste(ico_welcome, (34, 45), ico_welcome)

    # Detalhe tecnológico / barras decorativas
    welcome_draw.rectangle([20, 160, 144, 162], fill=(56, 189, 248))
    welcome_draw.rectangle([45, 168, 119, 169], fill=(2, 132, 199))

    welcome_path = ASSETS_DIR / "wizard_welcome.bmp"
    welcome_img.save(welcome_path, format="BMP")
    print(f" -> Salvo: {welcome_path}")

    print("✅ Todos os assets visuais gerados com sucesso!")


if __name__ == "__main__":
    gerar_pacote_assets()
