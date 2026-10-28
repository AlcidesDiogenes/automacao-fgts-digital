"""
Ponto de entrada principal do Sistema de Automações de Encargos - FGTS Digital.
Por padrão, inicia a interface gráfica nativa do Windows (CustomTkinter).
Suporta execução via linha de comando através da flag --cli.
"""

import sys
import argparse
from pathlib import Path

# Adiciona o diretório raiz ao sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.utils.logger import logger, setup_logger
from config import settings


def executar_modo_cli(args):
    """Executa a automação diretamente no terminal."""
    from src.core.excel_manager import ExcelManager
    from src.core.browser import BrowserManager
    from src.modules.fgts_digital.bot import FGTSDigitalBot
    from src.modules.fgts_digital.parser import normalizar_competencia

    logger.info("=== Iniciando Automação FGTS Digital via Linha de Comando ===")

    excel_path = Path(args.excel or settings.DEFAULT_EXCEL_PATH)
    output_dir = settings.resolver_caminho(args.output) if args.output else settings.DEFAULT_OUTPUT_DIR
    # Competência sempre informada pelo usuário, sem valor padrão (ADR-0007)
    competencia = normalizar_competencia(args.competencia)
    if not competencia:
        logger.error("Informe a competência com --competencia xx/xxxx (mês/ano).")
        sys.exit(2)
    headless = args.headless or settings.HEADLESS

    # Mesmas preferências da interface (config/parametros.json)
    parametros = settings.carregar_parametros()
    nomes = parametros.get("nomenclatura", {})
    templates_nomes = {
        "guia": nomes.get("guia") or "FGTS - Competencia",
        "relatorio_fgts": nomes.get("relatorio_fgts") or "RE FGTS - Competencia",
        "relatorio_consignado": nomes.get("relatorio_consignado") or "Consignado FGTS - Competencia",
    }
    exigir_valor_esperado = bool(parametros.get("emissao", {}).get("exigir_valor_esperado", True))

    # 1. Certificado: sempre o instalado no Windows (modo .pfx removido — ADR-0004)
    logger.info("Usando o certificado digital instalado no Windows.")

    # 2. Lê empresas
    if not excel_path.exists():
        logger.warning(f"Planilha não encontrada. Gerando modelo em: {excel_path}")
        ExcelManager.criar_planilha_modelo(excel_path)
        logger.info("Preencha a planilha com os CNPJs e execute novamente.")
        sys.exit(0)

    empresas = ExcelManager.ler_empresas(excel_path, competencia_padrao=competencia)
    if not empresas:
        logger.warning("Nenhuma empresa encontrada na planilha.")
        sys.exit(0)

    # A planilha não pode trazer empresa de outra competência (evita conferir/emitir o mês errado)
    divergentes = ExcelManager.competencias_divergentes(empresas, competencia)
    if divergentes:
        logger.error(f"Competência informada: {competencia}. {len(divergentes)} empresa(s) da planilha estão com outra competência:")
        for e in divergentes:
            logger.error(f"  {e['cnpj_formatado']} - {e['competencia'] or '(vazia)'}")
        logger.error("Corrija a planilha ou a competência informada. O robô não foi iniciado.")
        sys.exit(3)

    # 3. Execução do robô
    browser_mgr = BrowserManager(
        headless=headless,
        downloads_path=output_dir
    )

    try:
        page = browser_mgr.iniciar()
        bot = FGTSDigitalBot(page=page, output_base_dir=output_dir)

        if not bot.login():
            logger.error("Falha ao autenticar no FGTS Digital.")
            sys.exit(1)

        resultados = bot.processar_lote(
            empresas,
            competencia,
            apenas_conferir=args.conferir,
            exigir_valor_esperado=exigir_valor_esperado,
            templates_nomes=templates_nomes
        )
        rel_path = ExcelManager.gerar_relatorio_execucao(resultados, output_dir, competencia)
        logger.info(f"Processamento concluído com sucesso! Relatório gerado: {rel_path}")

    finally:
        browser_mgr.fechar()


def criar_parser_argumentos() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Automações de Encargos - FGTS Digital")
    parser.add_argument("--cli", action="store_true", help="Executar em modo linha de comando (sem janela gráfica)")
    parser.add_argument("--competencia", help="Competência a conferir/emitir, obrigatória na linha de comando (xx/xxxx: mês/ano)")
    parser.add_argument("--excel", help="Caminho da planilha de empresas (.xlsx)")
    parser.add_argument("--output", help="Pasta de saída para os arquivos")
    parser.add_argument("--headless", action="store_true", help="Executar navegador em segundo plano")
    parser.add_argument("--conferir", action="store_true", help="Apenas conferir valores no portal, sem emitir guias")
    return parser


def main():
    args = criar_parser_argumentos().parse_args()

    # Configura logs em arquivo na pasta data/logs
    setup_logger(log_dir=settings.LOGS_DIR)

    if args.cli:
        executar_modo_cli(args)
    else:
        # Inicia a Interface Gráfica Windows
        from src.ui.app import iniciar_aplicacao
        iniciar_aplicacao()


if __name__ == "__main__":
    main()
