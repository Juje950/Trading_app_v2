from fpdf import FPDF
import tempfile
import base64
import pandas as pd
from modules.calculations import Calculations
from config import TZ

class ReportGenerator:
    def __init__(self, calculations):
        self.calc = calculations
    
    def generate_investor_pdf(self, investor, df_trades, df_capital, df_capital_mes):
        """Genera reporte PDF para un inversor"""
        try:
            # Filtrar datos del inversor
            df_inversor_capital = df_capital[df_capital['nombre'] == investor]
            
            # Calcular métricas
            ingresos = df_inversor_capital[df_inversor_capital['tipo'] == 'ingreso']['capital_inicial'].sum()
            retiros = df_inversor_capital[df_inversor_capital['tipo'] == 'retiro']['capital_inicial'].sum()
            capital_neto = ingresos - retiros
            
            # Obtener ganancia del inversor
            ganancia_inversor = df_capital_mes[df_capital_mes["nombre"] == investor]["ganancia_proporcional"].values[0]
            
            # ROI
            roi = (ganancia_inversor / capital_neto) * 100 if capital_neto > 0 else 0
            
            # Crear PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            
            # Título
            pdf.cell(0, 10, f"Reporte de Inversión - {investor}", 0, 1, 'C')
            pdf.ln(10)
            
            # Información general
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, "Resumen General", 0, 1)
            pdf.set_font("Arial", '', 10)
            
            pdf.cell(0, 10, f"Capital Invertido: ${self.calc.format_number(capital_neto, 2)}", 0, 1)
            pdf.cell(0, 10, f"Ganancias Acumuladas: ${self.calc.format_number(ganancia_inversor, 4)}", 0, 1)
            pdf.cell(0, 10, f"ROI: {self.calc.format_number(roi, 2, True)}", 0, 1)
            pdf.ln(5)
            
            # Movimientos de capital
            self._add_capital_movements(pdf, df_inversor_capital)
            
            # Últimos trades
            self._add_recent_trades(pdf, df_trades)
            
            # Guardar PDF en un archivo temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmpfile:
                pdf.output(tmpfile.name)
                with open(tmpfile.name, "rb") as f:
                    pdf_bytes = f.read()
            
            return pdf_bytes
        
        except Exception as e:
            raise Exception(f"Error al generar reporte PDF: {str(e)}")
    
    def _add_capital_movements(self, pdf, df_movimientos):
        """Añade tabla de movimientos de capital al PDF"""
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Movimientos de Capital", 0, 1)
        pdf.set_font("Arial", '', 10)
        
        # Encabezados de tabla
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(40, 10, "Fecha", 1, 0, 'C', 1)
        pdf.cell(40, 10, "Tipo", 1, 0, 'C', 1)
        pdf.cell(40, 10, "Monto (USD)", 1, 1, 'C', 1)
        
        # Datos de movimientos
        df_movimientos = df_movimientos.sort_values('fecha_ingreso', ascending=False)
        for _, row in df_movimientos.iterrows():
            pdf.cell(40, 10, row['fecha_ingreso'].strftime('%d/%m/%Y'), 1, 0, 'C')
            pdf.cell(40, 10, 'Ingreso' if row['tipo'] == 'ingreso' else 'Retiro', 1, 0, 'C')
            pdf.cell(40, 10, self.calc.format_number(row['capital_inicial'], 2), 1, 1, 'C')
        
        pdf.ln(10)
    
    def _add_recent_trades(self, pdf, df_trades):
        """Añade tabla de últimos trades al PDF"""
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "Últimos Trades", 0, 1)
        pdf.set_font("Arial", '', 10)
        
        # Encabezados de tabla
        pdf.set_fill_color(200, 220, 255)
        pdf.cell(30, 10, "Fecha", 1, 0, 'C', 1)
        pdf.cell(30, 10, "Moneda", 1, 0, 'C', 1)
        pdf.cell(30, 10, "Exchange", 1, 0, 'C', 1)
        pdf.cell(30, 10, "Ganancia (USD)", 1, 1, 'C', 1)
        
        # Datos de trades
        df_trades_recent = df_trades.sort_values('fecha', ascending=False).head(10)
        for _, row in df_trades_recent.iterrows():
            pdf.cell(30, 10, row['fecha'].strftime('%d/%m/%Y'), 1, 0, 'C')
            pdf.cell(30, 10, row['moneda'], 1, 0, 'C')
            pdf.cell(30, 10, row['exchange'], 1, 0, 'C')
            pdf.cell(30, 10, self.calc.format_number(row['ganancia'], 4), 1, 1, 'C')
    
    def export_to_excel(self, df_trades, df_capital, filename="reporte_trading.xlsx"):
        """Exporta datos a Excel para contabilidad"""
        try:
            with pd.ExcelWriter(filename) as writer:
                df_trades.to_excel(writer, sheet_name='Trades', index=False)
                df_capital.to_excel(writer, sheet_name='Capital', index=False)
            return filename
        except Exception as e:
            raise Exception(f"Error al exportar a Excel: {str(e)}")
