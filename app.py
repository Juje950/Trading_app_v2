
import os
os.environ["STREAMLIT_WATCHER_TYPE"] = "none"

import sys
from pathlib import Path

current_dir = Path(__file__).parent
root_dir = current_dir.parent

sys.path.append(str(root_dir))
sys.path.append(str(current_dir))

from modules.calculations import (
    calculate_monthly_distribution,
    calculate_combined_evolution,
    calculate_historical_evolution,
    format_number
)
from modules.auth import AuthManager
from modules.sheets import SheetsManager
from modules.plots import PlotGenerator
from modules.reports import ReportGenerator
from modules.utils import AppUtils

from config import (
    TZ,
    MONEDAS_FRECUENTES,
    EXCHANGES_DISPONIBLES,
    COLORES_INVERSORES,
    USUARIOS
)

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import hashlib

sheets_manager = SheetsManager()
plot_generator = PlotGenerator()
report_generator = ReportGenerator(calculate_monthly_distribution)
auth_manager = AuthManager(sheets_manager)
app_utils = AppUtils()

st.title("Bienvenido al Dashboard de Trading")


if __name__ == "__main__":
    app_utils.initialize_session_state()
    if auth_manager.authenticate():
        df_trades, df_capital, ganancia_dia, cant_trades_dia, ganancia_total = load_data()
        if 'backup_realizado' not in st.session_state:
            if sheets_manager.backup_data():
                st.session_state.backup_realizado = True
        if st.session_state.usuario == "Bruno":
            st.set_page_config(page_title="Dashboard Trading Bruno", layout="wide")
            show_admin_dashboard(df_trades, df_capital)
        else:
            st.set_page_config(page_title=f"Dashboard de {st.session_state.usuario}", layout="wide")
            show_investor_dashboard(df_trades, df_capital)
        if st.sidebar.button("Cerrar Sesión"):
            auth_manager.logout()

def load_data():
    try:
        df_trades = sheets_manager.get_trades_data()
        df_capital = sheets_manager.get_capital_data()
        required_trades = ["fecha", "moneda", "exchange", "ganancia"]
        required_capital = ["nombre", "capital_inicial", "fecha_ingreso", "tipo"]
        for col in required_trades:
            if col not in df_trades.columns:
                st.error(f"Columna requerida faltante en trades: {col}")
                st.stop()
        for col in required_capital:
            if col not in df_capital.columns:
                st.error(f"Columna requerida faltante en capital: {col}")
                st.stop()
        today = pd.Timestamp.now(TZ).date()
        df_today = df_trades[df_trades["fecha"].dt.date == today]
        ganancia_dia = df_today["ganancia"].sum() if not df_today.empty else 0
        cant_trades_dia = df_today.shape[0]
        ganancia_total = df_trades["ganancia"].sum()
        return df_trades, df_capital, ganancia_dia, cant_trades_dia, ganancia_total
    except Exception as e:
        st.error(f"Error al cargar datos: {str(e)}")
        sheets_manager.log_action(f"Error carga datos: {str(e)}")
        st.stop()

def show_admin_dashboard(df_trades, df_capital):
    tabs = [
        "📊 Resumen", "📄 Reporte por Inversor", "📈 Evolución Histórica",
        "➕ Cargar Trade", "💸 Gestión de Capital",
        "⚙️ Configuración", "📜 Log"
    ]
    main_tab, report_tab, grafico_tab, carga_tab, capital_tab, config_tab, log_tab = st.tabs(tabs)
    with main_tab:
        show_admin_summary(df_trades, df_capital)
    with report_tab:
        show_investor_reports(df_trades, df_capital)
    with grafico_tab:
        show_historical_evolution(df_trades, df_capital)
    with carga_tab:
        show_trade_form(df_trades)
    with capital_tab:
        show_capital_management(df_capital)
    with config_tab:
        show_configuration()
    with log_tab:
        show_activity_log()

def show_admin_summary(df_trades, df_capital):
    st.subheader("🗓 Filtros por Fecha")
    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio = st.date_input("Desde", value=df_trades['fecha'].min().date())
    with col2:
        fecha_fin = st.date_input("Hasta", value=df_trades['fecha'].max().date())
    df_filtrado = df_trades[
        (df_trades['fecha'].dt.date >= fecha_inicio) &
        (df_trades['fecha'].dt.date <= fecha_fin)
    ]
    st.subheader("🧾 Últimos Trades")
    ver_todos = st.checkbox("Ver Todos los Trades")
    df_to_show = (
        df_filtrado.sort_values("fecha", ascending=False)
        if ver_todos
        else df_filtrado.sort_values("fecha", ascending=False).head(8)
    )
    app_utils.display_dataframe(
        df_to_show,
        columns_to_format={
            "ganancia": {"decimals": 4},
            "capital_expuesto": {"decimals": 2}
        }
    )
    st.subheader("📊 Indicadores del Día")
    today = pd.Timestamp.now(TZ).date()
    df_today = df_trades[df_trades['fecha'].dt.date == today]
    ganancia_dia = df_today['ganancia'].sum() if not df_today.empty else 0
    cant_trades_dia = len(df_today)
    col1, col2, col3 = st.columns(3)
    col1.metric("Ganancia del Día (USD)", f"${format_number(ganancia_dia, 4)}")
    col2.metric("Cantidad de Trades Hoy", cant_trades_dia)
    col3.metric("Ganancia Total Acumulada", f"${format_number(df_trades['ganancia'].sum(), 4)}")
    st.subheader("📊 Rendimiento por Moneda")
    rendimiento_moneda = df_trades.groupby("moneda").agg(
        cantidad_trades=("moneda", "count"),
        ganancia_total=("ganancia", "sum")
    ).sort_values("ganancia_total", ascending=False)
    app_utils.display_dataframe(
        rendimiento_moneda,
        columns_to_format={"ganancia_total": {"decimals": 4}}
    )
    try:
        df_capital_mes, ganancia_mes, rendimiento_pct, comision_pct, comision_bruno = (
            calculate_monthly_distribution(df_trades, df_capital)
        )
    except Exception as e:
        st.error("⚠️ Error al calcular la distribución mensual. Verifique:")
        st.write("1. Que las columnas 'fecha', 'ganancia' (trades) y 'nombre', 'capital_inicial', 'fecha_ingreso' (capital) existan")
        st.write("2. Que los formatos de fecha sean consistentes (DD/MM/AAAA)")
        st.write(f"Detalle técnico: {str(e)}")
        df_capital_mes = pd.DataFrame(columns=["nombre", "capital_neto", "ganancia_proporcional"])
        ganancia_mes, rendimiento_pct, comision_pct, comision_bruno = 0, 0, 0, 0
    st.subheader("💰 Reparto de Ganancias Mensual")
    st.markdown(
        f"**Configuración actual:** Bruno recibe {comision_pct}% "
        f"de comisión sobre ganancias (${format_number(comision_bruno, 4)})"
    )
    col1, col2, col3 = st.columns(3)
    col1.metric("Rendimiento mensual (%)", format_number(rendimiento_pct, 2, True))
    col2.metric("Ganancia mensual", f"${format_number(ganancia_mes, 4)}")
    col3.metric("Comisión Bruno", f"${format_number(comision_bruno, 4)}")
    df_mensual = df_capital_mes.copy()
    df_mensual["Total"] = df_mensual["capital_neto"] + df_mensual["ganancia_proporcional"]
    app_utils.display_dataframe(
        df_capital_mes[[
            "nombre", "capital_neto", "ganancia_proporcional", "capital_actual", "rendimiento_pct"
        ]].rename(columns={
            "capital_neto": "Capital Invertido",
            "ganancia_proporcional": "Ganancia",
            "capital_actual": "Capital Actual",
            "rendimiento_pct": "Rendimiento %"
        }),
        columns_to_format={
            "Capital Invertido": {"decimals": 2},
            "Ganancia": {"decimals": 4},
            "Capital Actual": {"decimals": 2},
            "Rendimiento %": {"decimals": 2, "is_percentage": True}
        }
    )
    total_general = df_capital_mes["capital_actual"].sum() if not df_capital_mes.empty else 0
    st.markdown(f"**🧮 Total general (debe coincidir con Exchange):** ${format_number(total_general, 2)}")
    st.subheader("📊 Evolución Combinada")
    df_evolucion = calculate_combined_evolution(df_trades, df_capital)
    inversores = ['Todos'] + df_capital['nombre'].unique().tolist()
    inversor_seleccionado = st.selectbox("Filtrar por inversor:", inversores)
    fig_combinado = plot_generator.create_combined_chart(
        df_evolucion,
        None if inversor_seleccionado == 'Todos' else inversor_seleccionado
    )
    st.plotly_chart(fig_combinado, use_container_width=True)

def show_investor_reports(df_trades, df_capital):
    st.subheader("📄 Reporte por Inversor")
    inversores = df_capital[df_capital["tipo"] == "ingreso"]["nombre"].unique()
    seleccion = st.selectbox("Seleccionar inversor", inversores)
    if seleccion:
        df_capital_mes, _, _, _, _ = calculate_monthly_distribution(df_trades, df_capital)
        st.subheader(f"📈 Evolución para {seleccion}")
        df_evolucion = calculate_combined_evolution(df_trades, df_capital)
        df_inversor = df_evolucion[df_evolucion['Inversor'] == seleccion]
        fig = plot_generator.create_combined_chart(df_inversor)
        st.plotly_chart(fig, use_container_width=True)
        st.subheader(f"📊 Resumen de Rendimiento - {seleccion}")
        datos_inversor = df_capital_mes[df_capital_mes['nombre'] == seleccion].iloc[0]
        col1, col2, col3 = st.columns(3)
        col1.metric("Capital Invertido", f"${format_number(datos_inversor['capital_neto'], 2)}")
        col2.metric("Ganancia Total", f"${format_number(datos_inversor['ganancia_proporcional'], 4)}")
        col3.metric("ROI Total", format_number(datos_inversor['rendimiento_pct'], 2, True))
        st.subheader("📤 Exportar Reporte")
        if st.button("Generar Reporte PDF"):
            pdf_bytes = report_generator.generate_investor_pdf(
                seleccion, df_trades, df_capital, df_capital_mes
            )
            if pdf_bytes:
                st.success("Reporte generado correctamente")
                st.markdown(
                    app_utils.create_download_link(
                        pdf_bytes, f"reporte_{seleccion}.pdf", "pdf"
                    ),
                    unsafe_allow_html=True
                )

def show_historical_evolution(df_trades, df_capital):
    st.subheader("📈 Evolución Histórica por Inversor")
    inversores = df_capital[df_capital["tipo"] == "ingreso"]["nombre"].unique()
    seleccion_inversor = st.selectbox("Seleccionar inversor:", inversores)
    periodo = st.radio("Visualizar por:", ["Día", "Mes", "Año"], horizontal=True, index=1)
    if seleccion_inversor:
        df_evolucion = calculate_historical_evolution(
            df_trades, df_capital, seleccion_inversor, periodo
        )
        if not df_evolucion.empty:
            fig = plot_generator.create_historical_chart(df_evolucion, periodo)
            st.plotly_chart(fig, use_container_width=True)
            st.subheader("📊 Datos Detallados")
            app_utils.display_dataframe(
                df_evolucion,
                columns_to_format={
                    'Capital': {'decimals': 2},
                    'Ganancia': {'decimals': 4},
                    'Total': {'decimals': 2},
                    'ROI': {'decimals': 2, 'is_percentage': True}
                }
            )

def show_trade_form(df_trades):
    st.subheader("➕ Cargar Nuevo Trade")
    with st.form("form_trade", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input("Fecha del trade*", value=datetime.now().date())
        with col2:
            opcion_moneda = st.radio(
                "Seleccionar moneda:", ["Existente", "Nueva"],
                horizontal=True, key="moneda_opcion"
            )
            if opcion_moneda == "Existente":
                moneda = st.selectbox("Moneda*", MONEDAS_FRECUENTES)
            else:
                moneda = st.text_input("Nueva moneda* (Ej: BTC, ETH)", key="nueva_moneda").upper()
        col3, col4 = st.columns(2)
        with col3:
            exchange = st.selectbox("Exchange*", EXCHANGES_DISPONIBLES)
        with col4:
            ganancia = st.number_input("Ganancia (USD)*", step=0.0001, format="%.4f")
        capital_expuesto = st.number_input("Capital expuesto (USD) [Opcional]", min_value=0.0, step=0.01)
        comentarios = st.text_area("Comentarios")
        submitted = st.form_submit_button("Guardar Trade")
        if submitted:
            errors = app_utils.validate_trade_form(fecha, moneda, exchange, ganancia)
            if not errors:
                try:
                    trade_data = {
                        'fecha': fecha.strftime("%d/%m/%Y"),
                        'moneda': moneda.upper(),
                        'exchange': exchange,
                        'ganancia': ganancia,
                        'capital_expuesto': capital_expuesto if capital_expuesto > 0 else '',
                        'comentarios': comentarios
                    }
                    if sheets_manager.add_trade(trade_data):
                        st.success("Trade guardado exitosamente!")
                        if opcion_moneda == "Nueva":
                            app_utils.update_currencies_list(moneda)
                        st.experimental_rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {str(e)}")
            else:
                for error in errors:
                    st.error(error)

def show_capital_management(df_capital):
    st.subheader("💸 Gestión de Capital")
    tab_ingreso, tab_retiro = st.tabs(["➕ Ingreso de Capital", "➖ Retiro de Capital"])
    with tab_ingreso:
        with st.form("form_ingreso", clear_on_submit=True):
            inversores_existentes = df_capital[
                (df_capital["tipo"] == "ingreso")
            ]["nombre"].unique()
            col1, col2 = st.columns(2)
            with col1:
                opcion_inversor = st.radio("Tipo de inversor:", ["Existente", "Nuevo"], horizontal=True)
            with col2:
                if opcion_inversor == "Existente":
                    nombre = st.selectbox("Seleccionar inversor*", inversores_existentes)
                else:
                    nombre = st.text_input("Nombre del nuevo inversor*").strip()
            capital = st.number_input("Monto a ingresar (USD)*", min_value=0.01)
            fecha = st.date_input("Fecha de ingreso*", value=datetime.now().date())
            comentarios = st.text_area("Comentarios (opcional)")
            submitted = st.form_submit_button("Registrar Ingreso")
            if submitted:
                errors = app_utils.validate_capital_form(nombre, capital, fecha, 'ingreso')
                if not errors:
                    try:
                        movement_data = {
                            'nombre': nombre,
                            'capital_inicial': capital,
                            'fecha_ingreso': fecha.strftime("%d/%m/%Y"),
                            'tipo': 'ingreso',
                            'comentarios': comentarios
                        }
                        if sheets_manager.add_capital_movement(movement_data):
                            st.success("Ingreso registrado exitosamente!")
                            st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Error al registrar: {str(e)}")
                else:
                    for error in errors:
                        st.error(error)
    with tab_retiro:
        with st.form("form_retiro", clear_on_submit=True):
            inversores_con_capital = df_capital[
                (df_capital["tipo"] == "ingreso") &
                (df_capital["capital_inicial"] > 0)
            ]["nombre"].unique()
            nombre_retiro = st.selectbox("Nombre del inversor*", inversores_con_capital)
            capital_disponible = (
                df_capital[
                    (df_capital["nombre"] == nombre_retiro) &
                    (df_capital["tipo"] == "ingreso")
                ]["capital_inicial"].sum()
                - df_capital[
                    (df_capital["nombre"] == nombre_retiro) &
                    (df_capital["tipo"] == "retiro")
                ]["capital_inicial"].sum()
            )
            capital_retiro = st.number_input(
                "Monto a retirar (USD)*",
                min_value=0.01,
                max_value=float(capital_disponible),
                value=min(1000.0, float(capital_disponible))
            )
            fecha_retiro = st.date_input("Fecha de retiro*", value=datetime.now().date())
            comentarios_retiro = st.text_area("Comentarios (opcional)", key="comentarios_retiro")
            submitted = st.form_submit_button("Registrar Retiro")
            if submitted:
                try:
                    movement_data = {
                        'nombre': nombre_retiro,
                        'capital_inicial': capital_retiro,
                        'fecha_ingreso': fecha_retiro.strftime("%d/%m/%Y"),
                        'tipo': 'retiro',
                        'comentarios': comentarios_retiro
                    }
                    if sheets_manager.add_capital_movement(movement_data):
                        st.success("Retiro registrado exitosamente!")
                        st.experimental_rerun()
                except Exception as e:
                    st.error(f"Error al registrar: {str(e)}")

def show_configuration():
    st.subheader("⚙️ Configuración del Sistema")
    st.markdown("### 🔐 Cambiar Contraseña")
    with st.form("form_password"):
        usuario_config = st.selectbox("Usuario", list(USUARIOS.keys()))
        nueva_pass = st.text_input("Nueva Contraseña*", type="password")
        confirm_pass = st.text_input("Confirmar Contraseña*", type="password")
        submitted = st.form_submit_button("Actualizar Contraseña")
        if submitted:
            if not nueva_pass or not confirm_pass:
                st.error("Por favor complete ambos campos de contraseña")
            elif nueva_pass == confirm_pass:
                USUARIOS[usuario_config] = hashlib.sha256(nueva_pass.encode()).hexdigest()
                st.success("Contraseña actualizada correctamente")
                sheets_manager.log_action(f"Contraseña actualizada para {usuario_config}")
            else:
                st.error("Las contraseñas no coinciden")
    st.markdown("### 🔄 Realizar Backup")
    if st.button("Generar Backup Ahora"):
        if sheets_manager.backup_data():
            st.success("Backup realizado correctamente")
        else:
            st.error("Error al realizar backup")
    st.markdown("### 🗑️ Limpiar Datos")
    if st.button("Limpiar Trades y Capital"):
        if sheets_manager.clear_data():
            st.success("Datos limpiados correctamente")
            st.experimental_rerun()
        else:
            st.error("Error al limpiar datos")

def show_activity_log():
    st.subheader("📜 Registro de Actividades")
    log_data = sheets_manager.get_log()
    if log_data.empty:
        st.info("No hay registros aún.")
    else:
        st.dataframe(log_data.sort_values("fecha", ascending=False))

def show_investor_dashboard(df_trades, df_capital):
    st.title(f"Dashboard de {st.session_state.usuario}")
    st.subheader("Resumen de Rendimiento")
    df_capital_mes, ganancia_mes, rendimiento_pct, _, _ = calculate_monthly_distribution(df_trades, df_capital)
    datos = df_capital_mes[df_capital_mes["nombre"] == st.session_state.usuario]
    if datos.empty:
        st.info("No hay datos disponibles para este inversor.")
        return
    datos = datos.iloc[0]
    col1, col2, col3 = st.columns(3)
    col1.metric("Capital Invertido", f"${format_number(datos['capital_neto'], 2)}")
    col2.metric("Ganancia Total", f"${format_number(datos['ganancia_proporcional'], 4)}")
    col3.metric("ROI Total", format_number(datos['rendimiento_pct'], 2, True))
    st.subheader("Evolución Histórica")
    df_evolucion = calculate_historical_evolution(df_trades, df_capital, st.session_state.usuario, "Mes")
    if not df_evolucion.empty:
        fig = plot_generator.create_historical_chart(df_evolucion, "Mes")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos para mostrar la evolución histórica.")


