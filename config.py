import hashlib
from datetime import datetime
from pytz import timezone

# Configuración de Google Sheets
SHEET_TRADES_ID = "1qv6cOLEJcikp1CAWIblJF3WlRhd6yDiVXCCMkdriwx4"
SHEET_CAPITAL_ID = "1g-5XseQ_cTyjbd7nqy6GM9KEPJNQQRm4nJr9jsDGjow"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Configuración de usuarios
USUARIOS = {
    "Bruno": hashlib.sha256("swmnt..".encode()).hexdigest(),
    "Sabrina": hashlib.sha256("inv123".encode()).hexdigest()
}

# Configuración fija
EXCHANGES_DISPONIBLES = ["Bitget", "Bybit", "Bitunix", "Otro"]
MONEDAS_FRECUENTES = ["BTC", "ETH", "SOL", "XRP", "LINK"]

# Paleta de colores
COLORES_INVERSORES = {
    "Bruno": "#636EFA",
    "Inversor1": "#EF553B",
    "Inversor2": "#00CC96",
    "Inversor3": "#AB63FA",
    "Inversor4": "#FFA15A"
}

# Zona horaria
TZ = timezone('America/Argentina/Buenos_Aires')
