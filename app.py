import pandas as pd
import requests
import streamlit as st
from datetime import datetime, timezone

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="Pedidos Frimex", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

LOYVERSE_TOKEN = "13d9288fbc264fb88a8112094407486a"

HEADERS = {
    "Authorization": f"Bearer {LOYVERSE_TOKEN}",
    "Content-Type": "application/json",
}

# ==========================================
# 2. ESTILOS CSS ULTRA COMPACTOS (UN SOLO ELEMENTO POR PRODUCTO)
# ==========================================
st.markdown("""
    <style>
    /* Ocultar elementos sobrantes y padding de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 24px !important;
        font-weight: bold;
    }

    /* Estilo general para todos los botones de producto */
    div[data-testid="stColumn"] button {
        width: 100% !important;
        border-radius: 6px !important;
        padding: 6px 12px !important;
        margin-bottom: 4px !important;
        height: 50px !important;
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
        transition: all 0.15s ease-in-out !important;
    }

    /* Formato del texto del producto dentro del botón */
    div[data-testid="stColumn"] button p {
        font-size: 16px !important;
        font-weight: 600 !important;
        text-align: left !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        margin: 0 !important;
        padding-right: 10px !important;
    }

    /* ESTADO PENDIENTE (Fondo Blanco, Borde e indicador Rojo) */
    div[data-testid="stColumn"] button[kind="secondary"] {
        background-color: #ffffff !important;
        border: 2px solid #e0e0e0 !important;
        border-left: 6px solid #ff4b4b !important;
        color: #2c3e50 !important;
    }
    div[data-testid="stColumn"] button[kind="secondary"]:hover {
        border-color: #ff4b4b !important;
        background-color: #fff5f5 !important;
    }

    /* ESTADO COMPLETADO (Verde Completo) */
    div[data-testid="stColumn"] button[kind="primary"] {
        background-color: #d1fae5 !important;
        border: 2px solid #a7f3d0 !important;
        border-left: 6px solid #10b981 !important;
        color: #065f46 !important;
    }
    div[data-testid="stColumn"] button[kind="primary"]:hover {
        background-color: #a7f3d0 !important;
    }

    /* Badge/Recuadro lateral reutilizable para mostrar la cantidad */
    .qty-badge {
        font-size: 20px;
        font-weight: 800;
        color: #ffffff;
        padding: 4px 10px;
        border-radius: 5px;
        min-width: 38px;
        text-align: center;
        display: inline-block;
    }
    .badge-pending {
        background-color: #ff4b4b;
    }
    .badge-completed {
        background-color: #10b981;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. CONTROL DE ESTADO
# ==========================================
if "hora_corte_utc" not in st.session_state:
    st.session_state.hora_corte_utc = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

if "completados" not in st.session_state:
    st.session_state.completados = set()

def reiniciar_contador():
    st.session_state.hora_corte_utc = datetime.now(timezone.utc)
    st.session_state.completados.clear()

def alternar_estado(producto):
    if producto in st.session_state.completados:
        st.session_state.completados.remove(producto)
    else:
        st.session_state.completados.add(producto)

# ==========================================
# 4. CONSULTA A LA API DE LOYVERSE
# ==========================================
def obtener_recibos_hoy():
    created_at_min = st.session_state.hora_corte_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    url = "https://api.loyverse.com/v1.0/receipts"
    params = {"created_at_min": created_at_min, "limit": 250}
    todos_los_recibos = []

    while True:
        try:
            response = requests.get(url, headers=HEADERS, params=params, timeout=5)
            if response.status_code != 200:
                return []

            data = response.json()
            recibos = data.get("receipts", [])
            todos_los_recibos.extend(recibos)

            cursor = data.get("cursor")
            if not cursor:
                break
            params["cursor"] = cursor

        except Exception:
            return []

    return todos_los_recibos

# ==========================================
# 5. FRAGMENTO AUTO-REGENERABLE (CADA 30s)
# ==========================================
@st.fragment(run_every=30)
def renderizar_tablero():
    recibos = obtener_recibos_hoy()

    conteo_productos = {}

    if recibos:
        for recibo in recibos:
            for item in recibo.get("line_items", []):
                nombre = item.get("item_name", "Producto")
                cantidad = item.get("quantity", 0)
                variante = item.get("variant_name")
                
                if variante and variante != "Default":
                    nombre_completo = f"{nombre} ({variante})"
                else:
                    nombre_completo = nombre

                cant_num = int(cantidad) if float(cantidad).is_integer() else cantidad
                conteo_productos[nombre_completo] = conteo_productos.get(nombre_completo, 0) + cant_num

    # Encabezado superior compacto
    col_tit, col_btn, col_m2, col_m3 = st.columns([1.8, 0.8, 1, 1])

    with col_tit:
        st.title("⚡ TOTAL A PREPARAR")
        st.caption(f"🔄 Actualización: {datetime.now().strftime('%H:%M:%S')} (Cada 30s)")

    with col_btn:
        st.write("") 
        st.button("Reiniciar", use_container_width=True, on_click=reiniciar_contador, help="Borra la pantalla y empieza a contar desde este instante")

    piezas_pendientes = sum(cant for prod, cant in conteo_productos.items() if prod not in st.session_state.completados)

    col_m2.metric("Tickets", len(recibos))
    col_m3.metric("Pendientes", piezas_pendientes)

    st.markdown("---")

    # Renderizado ultra eficiente en 3 columnas
    if conteo_productos:
        productos_ordenados = sorted(conteo_productos.items(), key=lambda x: x[1], reverse=True)

        col_a, col_b, col_c = st.columns(3)
        columnas = [col_a, col_b, col_c]

        for idx, (producto, cantidad) in enumerate(productos_ordenados):
            col_destino = columnas[idx % 3]
            es_completado = producto in st.session_state.completados
            
            with col_destino:
                # Usar dos elementos en la misma fila: Botón + Badge en sub-columnas integradas
                col_btn_prod, col_qty = st.columns([0.78, 0.22])
                
                with col_btn_prod:
                    st.button(
                        label=producto,
                        key=f"btn_{producto}",
                        type="primary" if es_completado else "secondary",
                        use_container_width=True,
                        on_click=alternar_estado,
                        args=(producto,)
                    )
                
                with col_qty:
                    badge_style = "badge-completed" if es_completado else "badge-pending"
                    st.markdown(
                        f'<div style="margin-top:2px;"><span class="qty-badge {badge_style}">{cantidad}</span></div>', 
                        unsafe_allow_html=True
                    )

    else:
        st.info("No hay pedidos registrados en este periodo.")

# Llamada inicial al fragmento
renderizar_tablero()
