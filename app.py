import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Finanzas Personales", layout="wide", page_icon="💰")

# --- FUNCIÓN DE LIMPIEZA ROBUSTA ---
def limpiar_monto_latino(valor):
    if pd.isna(valor): return 0.0
    s = str(valor).strip()
    s = s.replace('$', '').replace(' ', '')
    if ',' in s and '.' in s:
        s = s.replace('.', '')
    if ',' in s:
        s = s.replace(',', '.')
    elif '.' in s:
        partes = s.split('.')
        if len(partes[-1]) == 3:
            s = s.replace('.', '')
    try:
        return abs(float(s))
    except:
        return 0.0

@st.cache_data
def load_data():
    uri = "Data/GastosAgo25-Feb26.csv"
    try:
        df = pd.read_csv(uri, encoding='utf-8', skipinitialspace=True)
    except:
        st.error("No se encontró el archivo CSV.")
        return pd.DataFrame()

    columnas_ordenadas = ["Fecha", "Concepto","Periodicidad","Tipo","Categoría","Sub-Categoría","Monto"]
    df = df[columnas_ordenadas]
    df = df.dropna(subset=['Tipo', 'Fecha'])
    df['Monto'] = df['Monto'].apply(limpiar_monto_latino)

    meses_espanol = {
        'enero': 'January', 'febrero': 'February', 'marzo': 'March',
        'abril': 'April', 'mayo': 'May', 'junio': 'June',
        'julio': 'July', 'agosto': 'August', 'septiembre': 'September',
        'octubre': 'October', 'noviembre': 'November', 'diciembre': 'December'
    }
    fecha_limpia = df['Fecha'].str.lower().str.replace(' de ', ' ', regex=False)
    for esp, ing in meses_espanol.items():
        fecha_limpia = fecha_limpia.str.replace(esp, ing, regex=False)
    
    df['Fecha'] = pd.to_datetime(fecha_limpia, format='%d %B %Y', errors='coerce')
    return df.dropna(subset=['Fecha'])

# --- PROCESAMIENTO INICIAL ---
df_raw = load_data()
ahorro_total = 3100000 

# --- SIDEBAR (FILTROS) ---
st.sidebar.header("🛠️ Filtros")
categorias_disponibles = sorted(df_raw['Categoría'].unique())
cat_filter = st.sidebar.multiselect("Filtrar por Categoría", options=categorias_disponibles, default=categorias_disponibles)

# Filtrado dinámico
df = df_raw[df_raw['Categoría'].isin(cat_filter)]

# --- CÁLCULOS MAESTROS CORREGIDOS ---
# 1. Definimos qué es "Salida de dinero" (Gastos + Inversiones)
egresos_reales_df = df[df['Tipo'].isin(['Egreso', 'Inversión'])].copy()
ingresos_total = df[df['Tipo'] == 'Ingreso']['Monto'].sum()

if not egresos_reales_df.empty:
    # 2. Agrupamos por MES para tener una visión real de supervivencia
    # Usamos la suma mensual para que el alquiler y compras grandes pesen lo que deben
    gastos_mensuales = egresos_reales_df.resample('ME', on='Fecha')['Monto'].sum()
    
    # 3. Promedio Mensual (Más representativo que la mediana para el Runway)
    promedio_gasto_mensual = gastos_mensuales.mean()
    
    # 4. KPIs
    runway_meses = ahorro_total / promedio_gasto_mensual if promedio_gasto_mensual > 0 else 0
    tasa_ahorro = ((ingresos_total - egresos_reales_df['Monto'].sum()) / ingresos_total) if ingresos_total > 0 else 0
    costo_hora = promedio_gasto_mensual / (30 * 16)
else:
    promedio_gasto_mensual = runway_meses = tasa_ahorro = costo_hora = 0

# --- INTERFAZ STREAMLIT ---
st.title("🚀 Finanzas Personales: Toma de Decisiones")

# 1. KPIs
col1, col2, col3, col4 = st.columns(4)
col1.metric("Runway (Supervivencia)", f"{runway_meses:.1f} Meses")
col2.metric("Tasa de Ahorro Real", f"{tasa_ahorro:.1%}")
col3.metric("Costo x Hora de Vida", f"${costo_hora:,.0f}")
col4.metric("Promedio Gasto Mensual", f"${promedio_gasto_mensual:,.0f}")

st.divider()

if not egresos_reales_df.empty:
    # 2. ANÁLISIS VISUAL
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("🔍 Radiografía del Gasto (Inc. Inversiones)")
        fig_sun = px.sunburst(egresos_reales_df, path=['Categoría', 'Sub-Categoría'], values='Monto',
                              color='Monto', color_continuous_scale='RdBu_r')
        st.plotly_chart(fig_sun, use_container_width=True)

    with col_right:
        st.subheader("🐘 Elefantes vs 🐜 Hormigas")
        # El umbral ahora se basa en el promedio mensual para ser más preciso
        umbral_elefante = promedio_gasto_mensual * 0.05
        egresos_reales_df['Clasificación'] = egresos_reales_df['Monto'].apply(
            lambda x: 'Elefante (>5%)' if x > umbral_elefante else 'Hormiga (<5%)'
        )
        
        fig_pie = px.pie(egresos_reales_df, names='Clasificación', values='Monto', 
                         color_discrete_map={'Elefante (>5%)':'#EF553B', 'Hormiga (<5%)':'#636EFA'},
                         hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    # 3. TABLA DE CONTROL
    st.subheader("⚠️ Análisis de Gastos Mayores")
    elefantes = egresos_reales_df[egresos_reales_df['Clasificación'] == 'Elefante (>5%)'].sort_values('Fecha', ascending=False)
    
    st.data_editor(
        elefantes[['Fecha', 'Concepto', 'Categoría', 'Tipo', 'Monto']].head(15),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
            "Monto": st.column_config.NumberColumn("Monto", format="$ %.2f"),
            "Tipo": st.column_config.TextColumn("Tipo")
        },
        disabled=True
    )
else:
    st.warning("No hay egresos registrados con los filtros actuales.")

st.info(f"💡 El cálculo del Runway ahora incluye 'Inversiones' como la Notebook y el Kobo porque afectan tu liquidez inmediata.")