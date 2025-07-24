import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime
from config import SCOPES, SHEET_TRADES_ID, SHEET_CAPITAL_ID, TZ
import streamlit as st

class SheetsManager:
    def __init__(self):
        try:
            self.creds = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], scopes=SCOPES
            )
            self.gc = gspread.authorize(self.creds)
            self._setup_sheets()
        except Exception as e:
            st.error(f"Error al conectar con Google Sheets: {str(e)}")
            raise
    
    def _setup_sheets(self):
        self.sh_trades = self.gc.open_by_key(SHEET_TRADES_ID)
        self.worksheet_trades = self.sh_trades.sheet1
        self.sh_capital = self.gc.open_by_key(SHEET_CAPITAL_ID)
        self.worksheet_capital = self.sh_capital.sheet1

    def _parse_date(self, date_str):
        try:
            return datetime.strptime(date_str, '%d/%m/%Y').date()
        except:
            st.warning(f"Fecha inválida: {date_str}")
            return None

    def get_trades_data(self):
        try:
            records = self.worksheet_trades.get_all_records()
            df = pd.DataFrame(records)
            df.columns = df.columns.str.strip().str.lower()

            if "fecha" in df.columns:
                df["fecha"] = pd.to_datetime(df["fecha"], format='%d/%m/%Y', errors='coerce')
                df["mes"] = df["fecha"].dt.to_period("M")
            
            numeric_cols = ["ganancia", "capital_expuesto"]
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            return df
        except Exception as e:
            st.error(f"Error al cargar trades: {str(e)}")
            raise

    def get_capital_data(self):
        try:
            records = self.worksheet_capital.get_all_records()
            df = pd.DataFrame(records)
            df.columns = df.columns.str.strip().str.lower()

            if "fecha_ingreso" in df.columns:
                df["fecha_ingreso"] = pd.to_datetime(df["fecha_ingreso"], format='%d/%m/%Y', errors='coerce')
                df["mes_ingreso"] = df["fecha_ingreso"].dt.to_period("M").astype(str)

            if 'capital_inicial' in df.columns:
                df["capital_inicial"] = pd.to_numeric(df["capital_inicial"], errors='coerce').fillna(0)

            if 'tipo' not in df.columns:
                df['tipo'] = 'ingreso'
            
            return df
        except Exception as e:
            st.error(f"Error al cargar capital: {str(e)}")
            raise

    def add_trade(self, trade_data):
        try:
            fecha = self._parse_date(trade_data['fecha'])
            if not fecha:
                raise ValueError("Formato de fecha inválido. Use DD/MM/AAAA")
            
            row_data = [
                trade_data['fecha'],
                trade_data['moneda'].upper(),
                trade_data['exchange'],
                f"{float(trade_data['ganancia']):.4f}",
                f"{float(trade_data.get('capital_expuesto', 0)):.2f}",
                trade_data.get('comentarios', '')
            ]
            
            self.worksheet_trades.append_row(row_data)
            return True
        except Exception as e:
            st.error(f"Error al guardar trade: {str(e)}")
            raise

    def add_capital_movement(self, movement_data):
        try:
            fecha = self._parse_date(movement_data['fecha_ingreso'])
            if not fecha:
                raise ValueError("Formato de fecha inválido. Use DD/MM/AAAA")
            
            row_data = [
                movement_data['nombre'],
                f"{float(movement_data['capital_inicial']):.2f}",
                movement_data['fecha_ingreso'],
                movement_data['tipo'],
                movement_data.get('comentarios', '')
            ]
            
            self.worksheet_capital.append_row(row_data)
            return True
        except Exception as e:
            st.error(f"Error al guardar movimiento: {str(e)}")
            raise
