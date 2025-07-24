import base64
import pandas as pd
import streamlit as st
from config import MONEDAS_FRECUENTES, EXCHANGES_DISPONIBLES, TZ
from datetime import datetime

class AppUtils:
    @staticmethod
    def initialize_session_state():
        if 'autenticado' not in st.session_state:
            st.session_state.autenticado = False
        if 'usuario' not in st.session_state:
            st.session_state.usuario = None
        if 'backup_realizado' not in st.session_state:
            st.session_state.backup_realizado = False
    
    @staticmethod
    def validate_trade_form(fecha, moneda, exchange, ganancia):
        errors = []
        if not fecha:
            errors.append("La fecha es obligatoria")
        if not moneda:
            errors.append("La moneda es obligatoria")
        elif len(moneda) > 10:
            errors.append("La moneda no puede tener más de 10 caracteres")
        if not exchange:
            errors.append("El exchange es obligatorio")
        elif exchange not in EXCHANGES_DISPONIBLES:
            errors.append("Exchange no válido")
        if ganancia is None:
            errors.append("La ganancia es obligatoria")
        return errors
    
    @staticmethod
    def validate_capital_form(nombre, monto, fecha, tipo):
        errors = []
        if not nombre:
            errors.append("El nombre es obligatorio")
        elif len(nombre) > 50:
            errors.append("El nombre no puede tener más de 50 caracteres")
        if not monto or monto <= 0:
            errors.append("El monto debe ser mayor a cero")
        if not fecha:
            errors.append("La fecha es obligatoria")
        if tipo not in ['ingreso', 'retiro']:
            errors.append("Tipo de movimiento no válido")
        return errors
    
    @staticmethod
    def update_currencies_list(new_currency):
        if new_currency and new_currency.upper() not in MONEDAS_FRECUENTES:
            MONEDAS_FRECUENTES.append(new_currency.upper())
            return True
        return False
    
    @staticmethod
    def get_current_datetime():
        return datetime.now(TZ)
    
    @staticmethod
    def format_datetime(dt, format_str="%d/%m/%Y %H:%M:%S"):
        return dt.strftime(format_str)
    
    @staticmethod
    def display_dataframe(df, columns_to_format=None):
        if columns_to_format is None:
            columns_to_format = {}
        
        styled_df = df.copy()
        for col, format_spec in columns_to_format.items():
            if col in styled_df.columns:
                if format_spec.get('is_percentage', False):
                    styled_df[col] = styled_df[col].apply(
                        lambda x: f"{float(x):,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")
                    )
                else:
                    decimals = format_spec.get('decimals', 2)
                    styled_df[col] = styled_df[col].apply(
                        lambda x: f"{float(x):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    )
        
        st.dataframe(styled_df)
    
    @staticmethod
    def create_download_link(data, filename, file_type):
        if file_type == 'pdf':
            mime_type = 'application/octet-stream'
        elif file_type == 'excel':
            mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        else:
            mime_type = 'application/octet-stream'
        
        b64 = base64.b64encode(data).decode()
        return f'<a href="data:{mime_type};base64,{b64}" download="{filename}">Descargar {filename}</a>'
