import pandas as pd
import numpy as np
import streamlit as st
from config import TZ  # ← Import corregido para Streamlit Cloud

def calculate_monthly_distribution(df_trades, df_capital):
    """Versión definitiva con manejo robusto de errores"""
    try:
        # 1. Validación inicial de datos
        if df_trades.empty or df_capital.empty:
            return pd.DataFrame(), 0, 0, 0, 0

        # 2. Verificar columnas esenciales
        required_trade_cols = ["fecha", "ganancia"]
        required_capital_cols = ["nombre", "capital_inicial", "fecha_ingreso"]
        
        missing_trade = [col for col in required_trade_cols if col not in df_trades.columns]
        missing_capital = [col for col in required_capital_cols if col not in df_capital.columns]
        
        if missing_trade or missing_capital:
            raise ValueError(f"Columnas faltantes: Trades={missing_trade}, Capital={missing_capital}")

        # 3. Preparación de datos
        hoy = pd.Timestamp.now(TZ)
        mes_actual = hoy.to_period("M")
        
        # Crear columna 'mes' si no existe
        if 'mes' not in df_trades.columns:
            df_trades['mes'] = df_trades['fecha'].dt.to_period('M')
        
        # 4. Cálculo de ganancia mensual
        try:
            df_mes = df_trades[df_trades['mes'] == mes_actual]
            ganancia_mes = df_mes['ganancia'].sum()
        except:
            ganancia_mes = 0

        # 5. Procesamiento de capital
        df_capital = df_capital.copy()
        if 'tipo' not in df_capital.columns:
            df_capital['tipo'] = 'ingreso'
            
        # Filtrar capital vigente
        df_capital_vigente = df_capital[
            (df_capital['tipo'] == 'ingreso') & 
            (df_capital['fecha_ingreso'].notna()) &
            (df_capital['fecha_ingreso'] <= hoy)
        ]
        
        # Calcular retiros
        retiros = df_capital[
            (df_capital['tipo'] == 'retiro') & 
            (df_capital['fecha_ingreso'].notna())
        ]
        
        # 6. Cálculo de capital neto por inversor
        capital_inicial = df_capital_vigente.groupby('nombre')['capital_inicial'].sum()
        retirado = retiros.groupby('nombre')['capital_inicial'].sum()
        
        df_capital_mes = pd.DataFrame({
            'capital_inicial': capital_inicial,
            'total_retirado': retirado
        }).fillna(0).reset_index()
        
        df_capital_mes['capital_neto'] = df_capital_mes['capital_inicial'] - df_capital_mes['total_retirado']
        capital_total = df_capital_mes['capital_neto'].sum()
        
        # 7. Distribución si hay capital
        if capital_total <= 0:
            return df_capital_mes, ganancia_mes, 0, 0, 0
            
        # 8. Cálculo de comisiones
        rendimiento_pct = (ganancia_mes / capital_total) * 100
        
        if rendimiento_pct > 30:
            comision_pct = 35
        elif rendimiento_pct >= 10:
            comision_pct = 25
        elif rendimiento_pct > 0:
            comision_pct = 100
        else:
            comision_pct = 0
        
        comision_bruno = ganancia_mes * (comision_pct / 100)
        resto_ganancia = ganancia_mes - comision_bruno
        
        # 9. Distribución proporcional
        df_capital_mes['porcentaje'] = df_capital_mes['capital_neto'] / capital_total
        df_capital_mes['ganancia_proporcional'] = df_capital_mes['porcentaje'] * resto_ganancia
        
        # Bruno recibe su comisión adicional
        bruno_mask = df_capital_mes['nombre'].str.lower() == 'bruno'
        df_capital_mes.loc[bruno_mask, 'ganancia_proporcional'] += comision_bruno
        
        # 10. Cálculo final
        df_capital_mes['capital_actual'] = df_capital_mes['capital_neto'] + df_capital_mes['ganancia_proporcional']
        df_capital_mes['rendimiento_pct'] = (
            df_capital_mes['ganancia_proporcional'] / df_capital_mes['capital_neto']
        ).replace([np.inf, -np.inf], 0) * 100
        
        return df_capital_mes, ganancia_mes, rendimiento_pct, comision_pct, comision_bruno

    except Exception as e:
        error_info = {
            "error": str(e),
            "trade_columns": list(df_trades.columns) if 'df_trades' in locals() else None,
            "capital_columns": list(df_capital.columns) if 'df_capital' in locals() else None,
            "hoy": str(pd.Timestamp.now(TZ))
        }
        st.error(f"Error crítico en cálculo de distribución. Datos: {error_info}")
        return pd.DataFrame(), 0, 0, 0, 0
