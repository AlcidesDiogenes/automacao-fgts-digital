"""
Módulo de gerenciamento de planilhas Excel e CSV.
Lê listas de empresas e gera relatórios consolidados de execução com formatação profissional.
"""

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from src.modules.fgts_digital.parser import limpar_cnpj, formatar_cnpj, validar_cnpj
from src.utils.logger import logger


class ExcelManager:
    """Gerencia a leitura de entradas e geração de relatórios de saída."""

    @staticmethod
    def criar_planilha_modelo(destino: Path) -> Path:
        """Cria uma planilha modelo caso o usuário ainda não tenha uma."""
        destino.parent.mkdir(parents=True, exist_ok=True)
        wb = Workbook()
        ws = wb.active
        ws.title = "Empresas"

        # Cabeçalhos
        headers = ["CNPJ", "Razão Social", "Competência (Opcional)", "Observações"]
        ws.append(headers)

        # Exemplos
        ws.append(["12.345.678/0001-90", "Empresa Exemplo Alfa Ltda", "", "Exemplo 1"])
        ws.append(["98.765.432/0001-10", "Empresa Exemplo Beta S/A", "", "Exemplo 2"])

        # Estilização
        header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Ajuste de largura das colunas
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 15)

        wb.save(destino)
        logger.info(f"Planilha modelo criada em: {destino}")
        return destino

    @staticmethod
    def ler_empresas(caminho: Path, competencia_padrao: str = "") -> List[Dict[str, Any]]:
        """
        Lê uma planilha .xlsx ou arquivo .csv e retorna lista padronizada de empresas.
        """
        if not caminho.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

        if caminho.suffix.lower() == ".csv":
            df = pd.read_csv(caminho, dtype=str)
        else:
            df = pd.read_excel(caminho, dtype=str)

        # Normaliza nomes de colunas (minúsculo, sem acento básico)
        col_map = {}
        for col in df.columns:
            norm = str(col).strip().lower()
            if "cnpj" in norm or "cpf" in norm:
                col_map[col] = "cnpj"
            elif any(k in norm for k in ["razao", "social", "empresa", "nome"]):
                col_map[col] = "razao_social"
            elif any(k in norm for k in ["competencia", "mes", "periodo"]):
                col_map[col] = "competencia"
            elif any(k in norm for k in ["fgts_esperado", "total_fgts", "valor_folha", "fgts_folha", "valor_esperado", "total fgts"]):
                col_map[col] = "fgts_esperado"

        df = df.rename(columns=col_map)

        if "cnpj" not in df.columns:
            raise ValueError(f"Coluna 'CNPJ' não encontrada no arquivo {caminho.name}.")

        empresas = []
        for _, row in df.iterrows():
            cnpj_raw = str(row.get("cnpj", "")).strip()
            cnpj_limpo = limpar_cnpj(cnpj_raw)

            if not cnpj_limpo or cnpj_limpo == "nan":
                continue

            razao = str(row.get("razao_social", "")).strip()
            if not razao or razao == "nan":
                razao = f"Empresa CNPJ {formatar_cnpj(cnpj_limpo)}"

            comp = str(row.get("competencia", "")).strip()
            if not comp or comp == "nan":
                comp = competencia_padrao

            # FGTS esperado da folha/planilha
            val_folha_obj = row.get("fgts_esperado", 0.0)
            if isinstance(val_folha_obj, (int, float)):
                fgts_esperado = float(val_folha_obj)
            else:
                val_folha_raw = str(val_folha_obj).replace("R$", "").strip()
                if not val_folha_raw or val_folha_raw.lower() == "nan":
                    fgts_esperado = 0.0
                elif "," in val_folha_raw and "." in val_folha_raw:
                    # Formato brasileiro com milhar: 1.234,56
                    val_folha_raw = val_folha_raw.replace(".", "").replace(",", ".")
                    try:
                        fgts_esperado = float(val_folha_raw)
                    except ValueError:
                        fgts_esperado = 0.0
                elif "," in val_folha_raw:
                    # Formato brasileiro decimal simples: 1234,56
                    val_folha_raw = val_folha_raw.replace(",", ".")
                    try:
                        fgts_esperado = float(val_folha_raw)
                    except ValueError:
                        fgts_esperado = 0.0
                else:
                    # Formato numérico padrão/americano: 1234.56
                    try:
                        fgts_esperado = float(val_folha_raw)
                    except ValueError:
                        fgts_esperado = 0.0

            empresas.append({
                "cnpj": cnpj_limpo,
                "cnpj_formatado": formatar_cnpj(cnpj_limpo),
                "razao_social": razao,
                "competencia": comp,
                "fgts_esperado": fgts_esperado,
                "valido": validar_cnpj(cnpj_limpo)
            })

        logger.info(f"Carregadas {len(empresas)} empresas do arquivo {caminho.name}.")
        return empresas

    @staticmethod
    def gerar_relatorio_execucao(
        resultados: List[Dict[str, Any]],
        destino_dir: Path,
        competencia: str
    ) -> Path:
        """
        Gera uma planilha executiva com os resultados da rodada de automação.
        """
        destino_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_nome = f"Relatorio_FGTS_Digital_{competencia.replace('/', '-')}_{timestamp}.xlsx"
        arquivo_path = destino_dir / arquivo_nome

        wb = Workbook()
        ws = wb.active
        ws.title = "Status FGTS Digital"

        headers = [
            "CNPJ",
            "Razão Social",
            "Competência",
            "Status",
            "Valor Folha (R$)",
            "Valor Portal (R$)",
            "Diferença (R$)",
            "Arquivo da Guia",
            "Arquivo do Relatório",
            "Data/Hora",
            "Detalhes / Mensagem"
        ]
        ws.append(headers)

        # Cores para cabeçalho
        header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Cores de status
        fill_sucesso = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
        font_sucesso = Font(color="006100", bold=True)

        fill_aviso = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
        font_aviso = Font(color="9C6500", bold=True)

        fill_divergencia = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
        font_divergencia = Font(color="9C0006", bold=True)

        for item in resultados:
            val_folha = float(item.get("fgts_esperado", 0.0) or 0.0)
            val_portal = float(item.get("valor_guia", 0.0) or 0.0)
            diferenca = val_portal - val_folha if val_folha > 0 else 0.0

            row_data = [
                item.get("cnpj_formatado", formatar_cnpj(item.get("cnpj", ""))),
                item.get("razao_social", ""),
                item.get("competencia", competencia),
                item.get("status", "Pendente"),
                val_folha,
                val_portal,
                diferenca,
                item.get("arquivo_guia", ""),
                item.get("arquivo_relatorio", ""),
                item.get("data_hora", datetime.now().strftime("%d/%m/%Y %H:%M:%S")),
                item.get("detalhes", "")
            ]
            ws.append(row_data)

            # Estiliza linha de status
            current_row = ws.max_row
            status_cell = ws.cell(row=current_row, column=4)
            status_txt = str(status_cell.value).lower()

            if any(k in status_txt for k in ["sucesso", "emitid", "conferid", "valores iguais", "igual"]):
                status_cell.fill = fill_sucesso
                status_cell.font = font_sucesso
            elif any(k in status_txt for k in ["pendente", "sem debito", "sem movimento"]):
                status_cell.fill = fill_aviso
                status_cell.font = font_aviso
            else:
                status_cell.fill = fill_divergencia
                status_cell.font = font_divergencia

            # Formata células de moeda (colunas 5, 6, 7)
            for c_idx in [5, 6, 7]:
                ws.cell(row=current_row, column=c_idx).number_format = 'R$ #,##0.00'

        # Ajuste de largura das colunas
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 14), 45)

        wb.save(arquivo_path)
        logger.info(f"Relatório de execução gerado com sucesso: {arquivo_path}")

        return arquivo_path

    @staticmethod
    def gerar_relatorio_divergencias(
        divergencias: List[Dict[str, Any]],
        destino_dir: Path,
        competencia: str
    ) -> Path:
        """
        Gera uma planilha específica e destacada apenas com as divergências de valores encontradas.
        """
        destino_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_nome = f"DIVERGENCIAS_FGTS_{competencia.replace('/', '-')}_{timestamp}.xlsx"
        arquivo_path = destino_dir / arquivo_nome

        wb = Workbook()
        ws = wb.active
        ws.title = "Divergências de FGTS"

        # Título chamativo
        ws.merge_cells("A1:G1")
        top_title = ws["A1"]
        top_title.value = f"RELATÓRIO DE AUDITORIA E DIVERGÊNCIAS DE FGTS - COMPETÊNCIA {competencia}"
        top_title.font = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
        top_title.fill = PatternFill(start_color="9C0006", end_color="9C0006", fill_type="solid")
        top_title.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 28

        headers = [
            "CNPJ",
            "Razão Social",
            "Competência",
            "Valor Folha (R$)",
            "Valor FGTS Digital (R$)",
            "Diferença (R$)",
            "Motivo / Ação Tomada"
        ]
        ws.append(headers)

        header_fill = PatternFill(start_color="C00000", end_color="C00000", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=2, column=col_num)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        fill_row_alerta = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
        font_alerta = Font(name="Calibri", size=10, bold=True, color="9C6500")

        for item in divergencias:
            val_folha = float(item.get("fgts_esperado", 0.0) or 0.0)
            val_portal = float(item.get("valor_guia", 0.0) or 0.0)
            diferenca = val_portal - val_folha

            row_data = [
                item.get("cnpj_formatado", formatar_cnpj(item.get("cnpj", ""))),
                item.get("razao_social", ""),
                item.get("competencia", competencia),
                val_folha,
                val_portal,
                diferenca,
                item.get("detalhes", "Valor apurado no portal difere do total da folha.")
            ]
            ws.append(row_data)

            curr = ws.max_row
            ws.cell(row=curr, column=4).number_format = 'R$ #,##0.00'
            ws.cell(row=curr, column=5).number_format = 'R$ #,##0.00'
            
            dif_cell = ws.cell(row=curr, column=6)
            dif_cell.number_format = 'R$ #,##0.00'
            dif_cell.font = Font(bold=True, color="9C0006")

        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 15), 45)

        wb.save(arquivo_path)
        logger.warning(f"Planilha de divergências gerada: {arquivo_path}")
        return arquivo_path
