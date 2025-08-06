# === IMPORTACIONES ===
import streamlit as st
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import hashlib
import pytz
from pytz import timezone

# === CONFIGURACIÓN DE GOOGLE SHEETS ===
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
gc = gspread.authorize(creds)

# ID de la nueva hoja de cálculo (reemplaza con tu ID)
NUEVA_SHEET_ID = "1RHlwv_Y0UKxEA-WgxUQrD6vj1iUr6PzpI7gfbnwm8MU"
sh = gc.open_by_key(NUEVA_SHEET_ID)

# Configurar zona horaria Argentina
tz = timezone('America/Argentina/Buenos_Aires')

# === CONFIGURACIÓN DE USUARIOS ===
USUARIOS = {
    "Bruno": hashlib.sha256("tu_contraseña".encode()).hexdigest(),
    "Matias": hashlib.sha256("contraseña_matias".encode()).hexdigest(),
    "Juan": hashlib.sha256("contraseña_juan".encode()).hexdigest()
}

# === FUNCIONES PARA INICIALIZAR HOJAS ===
def inicializar_hojas():
    """Crea las hojas necesarias con sus encabezados si no existen"""
    try:
        # Intentar obtener la hoja de Gastos o crearla
        try:
            worksheet_gastos = sh.worksheet("Gastos")
        except:
            worksheet_gastos = sh.add_worksheet(title="Gastos", rows=1000, cols=10)
            worksheet_gastos.append_row(["Fecha", "Usuario", "Descripción", "Monto", "Tipo", "Destinatario"])
        
        # Intentar obtener la hoja de Pagos o crearla
        try:
            worksheet_pagos = sh.worksheet("Pagos")
        except:
            worksheet_pagos = sh.add_worksheet(title="Pagos", rows=1000, cols=10)
            worksheet_pagos.append_row(["Fecha", "Usuario Paga", "Usuario Recibe", "Monto", "Descripción", "Estado"])
        
        # Intentar obtener la hoja de Saldos o crearla
        try:
            worksheet_saldos = sh.worksheet("Saldos")
        except:
            worksheet_saldos = sh.add_worksheet(title="Saldos", rows=100, cols=5)
            worksheet_saldos.append_row(["Usuario", "Saldo"])
            # Inicializar saldos a cero
            for usuario in USUARIOS:
                worksheet_saldos.append_row([usuario, 0.0])
        
        return worksheet_gastos, worksheet_pagos, worksheet_saldos
    except Exception as e:
        st.error(f"Error inicializando hojas: {str(e)}")
        st.stop()

# Inicializar hojas
worksheet_gastos, worksheet_pagos, worksheet_saldos = inicializar_hojas()

# === FUNCIONES PRINCIPALES ===
def obtener_saldos():
    """Obtiene los saldos actuales de todos los usuarios"""
    try:
        records = worksheet_saldos.get_all_records()
        if not records:
            # Si no hay registros, inicializar saldos a cero
            saldos_iniciales = {usuario: 0.0 for usuario in USUARIOS}
            for usuario, saldo in saldos_iniciales.items():
                worksheet_saldos.append_row([usuario, saldo])
            return saldos_iniciales
        return {r['Usuario']: float(r['Saldo']) for r in records}
    except:
        return {usuario: 0.0 for usuario in USUARIOS}

def actualizar_saldos(nuevos_saldos):
    """Actualiza los saldos en Google Sheets"""
    try:
        # Borrar datos existentes (excepto encabezados)
        if worksheet_saldos.row_count > 1:
            worksheet_saldos.delete_rows(2, worksheet_saldos.row_count)
        
        # Escribir nuevos saldos
        for usuario, saldo in nuevos_saldos.items():
            worksheet_saldos.append_row([usuario, saldo])
    except Exception as e:
        st.error(f"Error al actualizar saldos: {str(e)}")

def registrar_gasto(usuario_registro, descripcion, monto, tipo, destinatario=None):
    """Registra un nuevo gasto en la hoja de cálculo"""
    fecha_hora = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")
    nuevo_gasto = [
        fecha_hora,
        usuario_registro,
        descripcion,
        float(monto),
        tipo,
        destinatario if destinatario else ""
    ]
    worksheet_gastos.append_row(nuevo_gasto)
    return True

def registrar_pago(usuario_paga, usuario_recibe, monto, descripcion=""):
    """Registra un pago entre usuarios"""
    fecha_hora = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")
    nuevo_pago = [
        fecha_hora,
        usuario_paga,
        usuario_recibe,
        float(monto),
        descripcion,
        "Pendiente"  # Estado de verificación
    ]
    worksheet_pagos.append_row(nuevo_pago)
    return True

def calcular_saldos():
    """Calcula los saldos actualizados basado en gastos y pagos"""
    # Obtener todos los gastos
    try:
        gastos = worksheet_gastos.get_all_records()
    except:
        gastos = []
    
    # Obtener todos los pagos
    try:
        pagos = worksheet_pagos.get_all_records()
    except:
        pagos = []
    
    saldos = {usuario: 0.0 for usuario in USUARIOS}
    
    # Procesar gastos
    for gasto in gastos:
        monto = float(gasto['Monto'])
        tipo = gasto['Tipo']
        usuario_registro = gasto['Usuario']
        
        if tipo == "Común":
            # Dividir entre los tres
            monto_por_persona = monto / 3
            for usuario in saldos:
                if usuario == usuario_registro:
                    # El que registra ya pagó todo, así que tiene crédito
                    saldos[usuario] += monto - monto_por_persona
                else:
                    # Los demás deben su parte
                    saldos[usuario] -= monto_por_persona
        else:
            # Gasto personal
            destinatario = gasto['Destinatario']
            if destinatario:
                # El destinatario debe el monto completo
                saldos[destinatario] -= monto
                # El que registra pagó, así que tiene crédito
                saldos[usuario_registro] += monto
    
    # Procesar pagos
    for pago in pagos:
        if pago['Estado'] == "Verificado":
            monto = float(pago['Monto'])
            saldos[pago['Usuario Paga']] -= monto
            saldos[pago['Usuario Recibe']] += monto
    
    return saldos

def obtener_historial_gastos():
    """Obtiene el historial completo de gastos"""
    try:
        return worksheet_gastos.get_all_records()
    except:
        return []

def obtener_historial_pagos():
    """Obtiene el historial completo de pagos"""
    try:
        return worksheet_pagos.get_all_records()
    except:
        return []

def autenticar():
    """Maneja la autenticación de usuarios"""
    if 'autenticado' not in st.session_state:
        st.session_state.autenticado = False
    
    if not st.session_state.autenticado:
        with st.sidebar:
            st.subheader("Acceso al Sistema")
            usuario = st.selectbox("Usuario", list(USUARIOS.keys()))
            password = st.text_input("Contraseña", type="password")
            
            if st.button("Ingresar"):
                if usuario in USUARIOS and hashlib.sha256(password.encode()).hexdigest() == USUARIOS[usuario]:
                    st.session_state.autenticado = True
                    st.session_state.usuario = usuario
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos")
        return False
    return True

def notificar_pago(usuario_paga, usuario_recibe, monto):
    """Muestra una notificación de pago pendiente de verificación"""
    st.session_state.notificacion = {
        "de": usuario_paga,
        "para": usuario_recibe,
        "monto": monto,
        "fecha": datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")
    }

# === INTERFAZ PRINCIPAL ===
if autenticar():
    # Calcular saldos actuales al cargar
    if 'saldos' not in st.session_state:
        st.session_state.saldos = calcular_saldos()
        actualizar_saldos(st.session_state.saldos)
    
    # Configurar página
    st.set_page_config(page_title="Gestor de Gastos Compartidos", layout="wide")
    st.title(f"💰 Gestor de Gastos Compartidos - {st.session_state.usuario}")
    
    # Tabs principales
    tab1, tab2, tab3, tab4 = st.tabs(["🏠 Inicio", "➕ Registrar Gasto", "💸 Registrar Pago", "📜 Historial"])

    with tab1:
        st.subheader("📊 Estado de Cuentas")
        
        # Mostrar saldos
        col1, col2, col3 = st.columns(3)
        col1.metric("Bruno", f"${st.session_state.saldos['Bruno']:,.2f}")
        col2.metric("Matias", f"${st.session_state.saldos['Matias']:,.2f}")
        col3.metric("Juan", f"${st.session_state.saldos['Juan']:,.2f}")
        
        # Interpretación de saldos
        st.info("""
        **Interpretación de saldos:**
        - **Positivo**: Tienes crédito (los demás te deben dinero)
        - **Negativo**: Tienes deuda (debes dinero a otros)
        """)
        
        # Resumen de deudas
        st.subheader("🔍 Resumen de Deudas")
        deudas_encontradas = False
        for usuario, saldo in st.session_state.saldos.items():
            if usuario != st.session_state.usuario and saldo < 0:
                deuda = abs(saldo)
                st.write(f"🔴 Le debes **${deuda:,.2f}** a {usuario}")
                deudas_encontradas = True
            elif usuario != st.session_state.usuario and saldo > 0:
                st.write(f"🟢 {usuario} te debe **${saldo:,.2f}**")
                deudas_encontradas = True
        
        if not deudas_encontradas:
            st.info("No hay deudas pendientes entre los usuarios.")

    with tab2:
        st.subheader("➕ Registrar Nuevo Gasto")
        
        with st.form("form_gasto", clear_on_submit=True):
            descripcion = st.text_input("Descripción del gasto*", max_chars=100)
            monto = st.number_input("Monto (ARS)*", min_value=1.0, step=100.0)
            
            tipo = st.radio("Tipo de gasto*", ["Común", "Personal"], horizontal=True)
            
            destinatario = None
            if tipo == "Personal":
                destinatario = st.selectbox("¿Para quién fue el gasto?", [u for u in USUARIOS if u != st.session_state.usuario])
            
            submitted = st.form_submit_button("Registrar Gasto")
            
            if submitted:
                if not descripcion or not monto:
                    st.error("Por favor complete todos los campos obligatorios (*)")
                else:
                    if registrar_gasto(
                        usuario_registro=st.session_state.usuario,
                        descripcion=descripcion,
                        monto=monto,
                        tipo=tipo,
                        destinatario=destinatario
                    ):
                        st.success("Gasto registrado correctamente!")
                        # Recalcular saldos
                        st.session_state.saldos = calcular_saldos()
                        actualizar_saldos(st.session_state.saldos)
                    else:
                        st.error("Error al registrar el gasto")

    with tab3:
        st.subheader("💸 Registrar Pago")
        
        # Selección de destinatario
        otros_usuarios = [u for u in USUARIOS if u != st.session_state.usuario]
        usuario_destino = st.selectbox("¿A quién le estás pagando?", otros_usuarios)
        
        # Monto máximo que puede pagar (basado en su deuda)
        deuda_usuario = abs(min(0, st.session_state.saldos[st.session_state.usuario]))
        monto_max = deuda_usuario if deuda_usuario > 0 else 0
        
        with st.form("form_pago", clear_on_submit=True):
            monto = st.number_input(
                f"Monto a pagar (ARS)* - Máx: ${monto_max:,.2f}" if monto_max > 0 else "Monto a pagar (ARS)*",
                min_value=1.0, 
                max_value=monto_max if monto_max > 0 else None,
                step=100.0
            )
            descripcion = st.text_input("Descripción (opcional)", max_chars=100)
            
            submitted = st.form_submit_button("Registrar Pago")
            
            if submitted:
                if monto <= 0:
                    st.error("El monto debe ser positivo")
                elif monto_max > 0 and monto > monto_max:
                    st.error(f"No puedes pagar más de ${monto_max:,.2f}")
                else:
                    if registrar_pago(
                        usuario_paga=st.session_state.usuario,
                        usuario_recibe=usuario_destino,
                        monto=monto,
                        descripcion=descripcion
                    ):
                        st.success("Pago registrado correctamente!")
                        # Notificar al receptor
                        notificar_pago(st.session_state.usuario, usuario_destino, monto)
                        # Recalcular saldos
                        st.session_state.saldos = calcular_saldos()
                        actualizar_saldos(st.session_state.saldos)
                    else:
                        st.error("Error al registrar el pago")
        
        # Sección para verificar pagos recibidos
        st.subheader("🔍 Verificar Pagos Recibidos")
        pagos_recibidos = [p for p in obtener_historial_pagos() 
                          if p['Usuario Recibe'] == st.session_state.usuario 
                          and p['Estado'] == "Pendiente"]
        
        if not pagos_recibidos:
            st.info("No tienes pagos pendientes de verificación")
        else:
            for pago in pagos_recibidos:
                with st.expander(f"Pago de {pago['Usuario Paga']} - ${float(pago['Monto']):,.2f}"):
                    st.write(f"**Fecha:** {pago['Fecha']}")
                    st.write(f"**Descripción:** {pago.get('Descripción', 'Sin descripción')}")
                    
                    if st.button(f"Marcar como verificado", key=f"verificar_{pago['Fecha']}"):
                        # Actualizar estado en Google Sheets
                        cell = worksheet_pagos.find(pago['Fecha'])
                        worksheet_pagos.update_cell(cell.row, 6, "Verificado")
                        st.success("Pago verificado correctamente!")
                        st.rerun()

    with tab4:
        st.subheader("📜 Historial Completo")
        
        tab_hist_gastos, tab_hist_pagos = st.tabs(["Gastos", "Pagos"])
        
        with tab_hist_gastos:
            gastos = obtener_historial_gastos()
            if gastos:
                st.dataframe(gastos)
            else:
                st.info("No hay gastos registrados aún")
        
        with tab_hist_pagos:
            pagos = obtener_historial_pagos()
            if pagos:
                st.dataframe(pagos)
            else:
                st.info("No hay pagos registrados aún")

    # Mostrar notificación de pago si existe
    if 'notificacion' in st.session_state:
        notif = st.session_state.notificacion
        if notif['para'] == st.session_state.usuario:
            st.sidebar.success(f"✅ **Nuevo pago recibido!**\n\n"
                              f"De: {notif['de']}\n"
                              f"Monto: ${notif['monto']:,.2f}\n"
                              f"Fecha: {notif['fecha']}\n\n"
                              "Por favor verifícalo en la pestaña '💸 Registrar Pago'")
    
    # Botón de cierre de sesión
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.session_state.pop('usuario', None)
        st.rerun()
