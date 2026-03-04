import os
import sqlite3
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv('NOTION_TOKEN')
DATABASE_ID = os.getenv('DATABASE_ID')

def fetch_notion_data():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    rows = []
    has_more = True
    next_cursor = None

    # Bucle para manejar la paginación (trae más de 100 registros)
    while has_more:
        payload = {"start_cursor": next_cursor} if next_cursor else {}
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code != 200:
            print(f"Error en la API: {response.status_code}")
            break

        data = response.json()
        results = data.get("results", [])

        for page in results:
            props = page.get("properties", {})
            
            fecha_obj = props.get("Fecha", {}).get("date")
            concepto_list = props.get("Concepto", {}).get("title", [])
            periodicidad_obj = props.get("Periodicidad", {}).get("select")
            tipo_obj = props.get("Tipo", {}).get("select")
            categoria_obj = props.get("Categoría", {}).get("select")
            subcat_obj = props.get("Sub-Categoría", {}).get("select")
            monto_val = props.get("Monto", {}).get("number")

            rows.append({
                "Fecha": fecha_obj["start"] if fecha_obj else None,
                "Concepto": concepto_list[0].get("plain_text") if concepto_list else "",
                "Periodicidad": periodicidad_obj.get("name") if periodicidad_obj else "Único",
                "Tipo": tipo_obj.get("name") if tipo_obj else None,
                "Categoria": categoria_obj.get("name") if categoria_obj else "Sin Categoría",
                "Sub-Categoría": subcat_obj.get("name") if subcat_obj else None,
                "Monto": monto_val if monto_val is not None else 0
            })

        # Verificar si hay más páginas de datos
        has_more = data.get("has_more")
        next_cursor = data.get("next_cursor")
        
    return pd.DataFrame(rows)

# Ejecución y guardado
if not os.path.exists('Data'):
    os.makedirs('Data')

df = fetch_notion_data()

if not df.empty:
    conn = sqlite3.connect('Data/gastos.db')
    df.to_sql('gastos', conn, if_exists='replace', index=False)
    conn.close()
    print(f"Éxito: Se importaron {len(df)} registros totales.")
else:
    print("No se encontraron datos.")