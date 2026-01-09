import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Cartera de Acciones", layout="wide")
st.title("📊 Mi Cartera de Acciones")

CSV_FILE = "cartera.csv"

# Función para cargar y guardar
def cargar_cartera():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    else:
        return pd.DataFrame(columns=["Empresa", "Símbolo", "Cantidad", "Precio Compra"])

def guardar_cartera(df):
    df.to_csv(CSV_FILE, index=False)

# Inicializar cartera
if "cartera" not in st.session_state:
    st.session_state.cartera = cargar_cartera()

cartera = st.session_state.cartera

# Sidebar: Agregar acción
st.sidebar.header("➕ Agregar una acción")
with st.sidebar.form("form_entrada"):
    empresa = st.text_input("Nombre de la empresa")
    simbolo = st.text_input("Símbolo de la acción (ej. AAPL)").upper()
    cantidad = st.number_input("Cantidad de acciones", min_value=0.0, format="%.2f")
    precio_compra = st.number_input("Precio de compra (USD)", min_value=0.0, format="%.2f")
    agregar = st.form_submit_button("Agregar")

if agregar and simbolo and cantidad > 0 and precio_compra > 0:
    nueva = pd.DataFrame([[empresa, simbolo, cantidad, precio_compra]],
                         columns=["Empresa", "Símbolo", "Cantidad", "Precio Compra"])
    st.session_state.cartera = pd.concat([cartera, nueva], ignore_index=True)
    guardar_cartera(st.session_state.cartera)
    st.success(f"✅ Acción {simbolo} agregada")

# Sidebar: Editar o eliminar
st.sidebar.header("✏️ Editar / ❌ Eliminar acción")
if not cartera.empty:
    seleccion = st.sidebar.selectbox("Selecciona una acción", cartera["Símbolo"] + " - " + cartera["Empresa"])
    idx = cartera.index[cartera["Símbolo"] + " - " + cartera["Empresa"] == seleccion][0]
    
    accion = st.sidebar.radio("¿Qué deseas hacer?", ["Editar", "Eliminar"])
    
    if accion == "Editar":
        with st.sidebar.form("form_editar"):
            nueva_empresa = st.text_input("Nuevo nombre", value=cartera.at[idx, "Empresa"])
            nueva_cantidad = st.number_input("Nueva cantidad", value=cartera.at[idx, "Cantidad"], format="%.2f")
            nuevo_precio = st.number_input("Nuevo precio compra", value=cartera.at[idx, "Precio Compra"], format="%.2f")
            guardar_cambios = st.form_submit_button("Guardar cambios")
        if guardar_cambios:
            st.session_state.cartera.at[idx, "Empresa"] = nueva_empresa
            st.session_state.cartera.at[idx, "Cantidad"] = nueva_cantidad
            st.session_state.cartera.at[idx, "Precio Compra"] = nuevo_precio
            guardar_cartera(st.session_state.cartera)
            st.success("✅ Acción actualizada")
    elif accion == "Eliminar":
        if st.sidebar.button("Eliminar esta acción"):
            st.session_state.cartera = cartera.drop(idx).reset_index(drop=True)
            guardar_cartera(st.session_state.cartera)
            st.success("🗑️ Acción eliminada")

# Recalcular con precios actuales
cartera = st.session_state.cartera

if not cartera.empty:
    precios_actuales = []
    for sym in cartera["Símbolo"]:
        try:
            precio = yf.Ticker(sym).history(period="1d")["Close"].iloc[-1]
        except:
            precio = 0
        precios_actuales.append(precio)

    cartera["Precio Actual"] = precios_actuales
    cartera["Total Inversión"] = cartera["Cantidad"] * cartera["Precio Compra"]
    cartera["Valor Actual"] = cartera["Cantidad"] * cartera["Precio Actual"]
    cartera["Diferencia $"] = cartera["Valor Actual"] - cartera["Total Inversión"]
    cartera["Diferencia %"] = (cartera["Diferencia $"] / cartera["Total Inversión"]) * 100

    st.subheader("📋 Resumen de tu cartera")
    st.dataframe(cartera.style.format({
        "Precio Compra": "${:.2f}",
        "Precio Actual": "${:.2f}",
        "Total Inversión": "${:.2f}",
        "Valor Actual": "${:.2f}",
        "Diferencia $": "${:.2f}",
        "Diferencia %": "{:.2f}%"
    }).applymap(lambda x: "color: green" if isinstance(x, float) and x > 0 else "color: red"))

    st.subheader("📈 Rendimiento de tus acciones")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=cartera["Símbolo"],
        y=cartera["Diferencia $"],
        marker_color=cartera["Diferencia $"].apply(lambda x: 'green' if x >= 0 else 'red')
    ))
    fig.update_layout(title="Ganancia/Pérdida por Acción", xaxis_title="Acción", yaxis_title="USD")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Agrega acciones desde el panel izquierdo.")

