import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ----------------------------------------- #
# ----------IMPORTAR BASE DE DATOS--------- #
# ----------------------------------------- #

def cargar_datos():
    conn = sqlite3.connect('Data/gastos.db')
    df = pd.read_sql_query("SELECT * FROM gastos", conn)
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    conn.close()
    return df

df = cargar_datos()

# ----------------------------------------- #
# ----------------MÉTRICAS----------------- #
# ----------------------------------------- #

# --- Segmentación de Datos --- #

ingresos = df[df['Tipo'] == 'Ingreso'].copy()
egresos = df[df['Tipo'] == 'Egreso'].copy()
inversion = df[df['Tipo'] == 'Inversión'].copy()

ingresos_totales = ingresos["Monto"].sum()
egresos_totales = egresos["Monto"].sum()
inversion_total = inversion["Monto"].sum()

# --- Medidas de Tendencia (Egresos Mensuales) --- #

# Sumamos egresos por mes para tener totales mensuales reales
gastos_por_mes = egresos.resample('MS', on='Fecha')['Monto'].sum()
mediana_mensual = gastos_por_mes.median()
desviacion_mensual = gastos_por_mes.std()

# Variabilidad (Coeficiente de Variación)
variabilidad_pct = 0
if gastos_por_mes.mean() > 0:
    variabilidad_pct = (desviacion_mensual / gastos_por_mes.mean()) * 100


# --- TASA DE AHORRO --- #

# (Ingresos - Gastos) / Ingresos -> % que logras retener
tasa_ahorro = 0
if ingresos_totales > 0:
    tasa_ahorro = ((ingresos_totales - egresos_totales) / ingresos_totales) * 100


# --- Análisis gastos hormiga --- #

# Filtramos específicamente la subcategoría 'Hormiga' dentro de los egresos
gastos_hormiga_total = egresos[egresos['Sub_Categoria'] == 'Hormiga']['Monto'].sum()
porcentaje_hormiga = 0
if egresos_totales > 0:
    porcentaje_hormiga = (gastos_hormiga_total / egresos_totales) * 100


# --- RUNWAY --- #

ahorros_actuales = 2600000
runway_meses = ahorros_actuales / mediana_mensual if mediana_mensual > 0 else 0


# --- Análisis de sensibilidad (Escenarios) --- #

# Usamos multiplicadores sobre la mediana total para mayor estabilidad lógica
gasto_realista = mediana_mensual 
gasto_optimista = mediana_mensual * 0.80  # Ahorro del 20%
gasto_pesimista = mediana_mensual * 1.25  # Gasto extra del 25%

runway_real = ahorros_actuales / gasto_realista if gasto_realista > 0 else 0
runway_opti = ahorros_actuales / gasto_optimista if gasto_optimista > 0 else 0
runway_pess = ahorros_actuales / gasto_pesimista if gasto_pesimista > 0 else 0



# ----------------------------------------- #
# ------------VISUALIZACIÓN---------------- #
# ----------------------------------------- #

# Configuración de la página
st.set_page_config(page_title="Dashboard Finanzas Personales", layout="wide")

st.title("📊 Mi Tablero de Finanzas Personales")
st.markdown(f"**Estado de salud financiera basado en el historial de gastos.**")

# --- FILA 1: KPIs PRINCIPALES ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Ahorros Actuales", f"${ahorros_actuales:,.0f}", help="Dinero disponible en caja")
with col2:
    st.metric("Runway Realista", f"{runway_real:.1f} meses", delta=f"{runway_opti - runway_real:.1f} (Opt)", delta_color="normal")
with col3:
    st.metric("Tasa de Ahorro", f"{tasa_ahorro:.1f}%", delta=None)
with col4:
    st.metric("Gasto Hormiga", f"{porcentaje_hormiga:.1f}%", delta=f"-{gastos_hormiga_total:,.0f}$", delta_color="inverse")

st.markdown("---")

# --- FILA 2: ANÁLISIS DE RUNWAY Y ESCENARIOS ---
left_column, right_column = st.columns([1, 1])

with left_column:
    st.subheader("🏃 Análisis de Supervivencia (Runway)")
    
    # Gráfico de barras comparativo de escenarios
    fig_runway = go.Figure(data=[
        go.Bar(name='Optimista (-20% gasto)', x=['Escenarios'], y=[runway_opti], marker_color='#2ecc71'),
        go.Bar(name='Realista (Mediana)', x=['Escenarios'], y=[runway_real], marker_color='#3498db'),
        go.Bar(name='Pesimista (+25% gasto)', x=['Escenarios'], y=[runway_pess], marker_color='#e74c3c')
    ])
    fig_runway.update_layout(title="Meses de vida según escenario", barmode='group', height=350)
    st.plotly_chart(fig_runway, use_container_width=True)

with right_column:
    st.subheader("🧐 ¿A dónde va el dinero?")
    # Gráfico de Torta por Categoría
    cat_gastos = egresos.groupby('Categoria')['Monto'].sum().reset_index()
    fig_pie = px.pie(cat_gastos, values='Monto', names='Categoria', hole=0.4,
                     color_discrete_sequence=px.colors.qualitative.Pastel)
    fig_pie.update_layout(height=350)
    st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---")

# --- FILA 3: HISTÓRICO Y ESTABILIDAD ---
st.subheader("📈 Evolución Mensual de Gastos")
# Gráfico de línea con los gastos totales mensuales
fig_line = px.line(gastos_por_mes.reset_index(), x='Fecha', y='Monto', markers=True, 
                   title="Gasto Total Mensual vs Mediana")
fig_line.add_hline(y=mediana_mensual, line_dash="dash", line_color="green", 
                   annotation_text=f"Mediana: ${mediana_mensual:,.0f}")
st.plotly_chart(fig_line, use_container_width=True)

# --- DETALLES TÉCNICOS ---
with st.expander("🛠️ Ver detalles de estabilidad y datos crudos"):
    c1, c2, c3 = st.columns(3)
    c1.write(f"**Desviación Estándar:** ${desviacion_mensual:,.2f}")
    c2.write(f"**Variabilidad (CV):** {variabilidad_pct:.1f}%")
    c3.write(f"**Total Invertido:** ${inversion_total:,.0f}")
    
    if variabilidad_pct > 30:
        st.warning("⚠️ Tus gastos son muy volátiles. La mediana es más confiable que el promedio en tu caso.")
    
    st.dataframe(df.sort_values(by='Fecha', ascending=False), use_container_width=True)