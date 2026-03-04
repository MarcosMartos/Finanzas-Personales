import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

st.title("📊 Mi Dashboard de Gastos")

# Cargar datos desde SQLite
conn = sqlite3.connect('Data/gastos.db')
df = pd.read_sql("SELECT * FROM gastos", conn)
conn.close()

# Métricas rápidas
total_gastado = df['Monto'].sum()
st.metric("Total Gastado", f"${total_gastado:,.2f}")

# Gráfico de pastel por categoría
fig = px.pie(df, values='Monto', names='Categoria', title='Gastos por Categoría')
st.plotly_chart(fig)

st.badge("Perfectirijillo", icon=":material/check:", color="green")

# Tabla de datos
st.dataframe(df)