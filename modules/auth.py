import hashlib
import streamlit as st
from config import USUARIOS
from modules.sheets import SheetsManager
from datetime import datetime
from pytz import timezone
from config import TZ  # Asegúrate que TZ esté definido en config.py

fecha_hora = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")

class AuthManager:
    def __init__(self, sheets_manager):
        self.sheets = sheets_manager
    
    def authenticate(self):
        """Maneja el proceso de autenticación"""
        if 'autenticado' not in st.session_state:
            st.session_state.autenticado = False
        
        if not st.session_state.autenticado:
            return self._show_login_form()
        return True
    
    def _show_login_form(self):
        """Muestra el formulario de login"""
        with st.sidebar:
            st.subheader("Acceso al Dashboard")
            usuario = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            
            if st.button("Ingresar"):
                if self._check_credentials(usuario, password):
                    st.session_state.autenticado = True
                    st.session_state.usuario = usuario
                    self._log_login(usuario, success=True)
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos")
                    self._log_login(usuario, success=False)
        return False
    
    def _check_credentials(self, usuario, password):
        """Verifica las credenciales"""
        return usuario in USUARIOS and \
               hashlib.sha256(password.encode()).hexdigest() == USUARIOS[usuario]
    
    def _log_login(self, usuario, success):
        """Registra intentos de login"""
        accion = f"Login {'exitoso' if success else 'fallido'} - Usuario: {usuario}"
        self._log_action(accion)
    
    def _log_action(self, action):
        """Registra una acción en el log"""
        try:
            worksheet_log = self.sheets.sh_capital.worksheet("Log")
        except:
            worksheet_log = self.sheets.sh_capital.add_worksheet(title="Log", rows=1000, cols=20)
        
        fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_data = [fecha_hora, st.session_state.get('usuario', 'Sistema'), action]
        worksheet_log.append_row(log_data)
    
    def logout(self):
        """Cierra la sesión del usuario"""
        st.session_state.autenticado = False
        st.session_state.pop('usuario', None)
        self._log_action("Sesión cerrada")
        st.rerun()
