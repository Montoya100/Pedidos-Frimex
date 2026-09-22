import base64
import os
import requests
import streamlit as st
from datetime import datetime, timezone

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="MOSTACHO BOTANAS", 
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

LOYVERSE_TOKEN = "13d9288fbc264fb88a8112094407486a"

HEADERS = {
    "Authorization": f"Bearer {LOYVERSE_TOKEN}",
    "Content-Type": "application/json",
}

# ==========================================
# CARGAR LOGO LOCAL O FALLBACK
# ==========================================
def obtener_base64_imagen(ruta_imagen):
    if os.path.exists(ruta_imagen):
        with open(ruta_imagen, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
            return f"data:image/png;base64,{encoded_string}"
    return "https://via.placeholder.com/150/ff4b4b/ffffff?text=LOGO"

LOGO_URL = obtener_base64_imagen("logo.png")

# ==========================================
# 2. ESTADO GLOBAL COMPARTIDO
# ==========================================
@st.cache_resource
def obtener_estado_global():
    return {
        "completados": set(),
        "cantidades_al_completar": {},
        "hora_corte_utc": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    }

estado_global = obtener_estado_global()

def reiniciar_contador():
    estado_global["hora_corte_utc"] = datetime.now(timezone.utc)
    estado_global["completados"].clear()
    estado_global["cantidades_al_completar"].clear()

def alternar_estado(producto, cantidad_actual):
    if producto in estado_global["completados"]:
        estado_global["completados"].remove(producto)
        estado_global["cantidades_al_completar"].pop(producto, None)
    else:
        estado_global["completados"].add(producto)
        estado_global["cantidades_al_completar"][producto] = cantidad_actual

def reproducir_sonido_notificacion():
    sound_js = """
    <script>
    (function() {
        try {
            var AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;
            var ctx = new AudioContext();
            
            var osc1 = ctx.createOscillator();
            var gain1 = ctx.createGain();
            osc1.type = 'sine';
            osc1.frequency.setValueAtTime(587.33, ctx.currentTime);
            gain1.gain.setValueAtTime(0.15, ctx.currentTime);
            gain1.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.2);
            osc1.connect(gain1);
            gain1.connect(ctx.destination);
            osc1.start(ctx.currentTime);
            osc1.stop(ctx.currentTime + 0.2);

            var osc2 = ctx.createOscillator();
            var gain2 = ctx.createGain();
            osc2.type = 'sine';
            osc2.frequency.setValueAtTime(880, ctx.currentTime + 0.12);
            gain2.gain.setValueAtTime(0.2, ctx.currentTime + 0.12);
            gain2.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
            osc2.connect(gain2);
            gain2.connect(ctx.destination);
            osc2.start(ctx.currentTime + 0.12);
            osc2.stop(ctx.currentTime + 0.4);
        } catch(e) {
            console.log(e);
        }
    })();
    </script>
    """
    st.components.v1.html(sound_js, height=0, width=0)

# ==========================================
# 3. ESTILOS CSS REVISADOS Y ALINEACIÓN PURE
# ==========================================
st.markdown(f"""
    <style>
    /* Splash Screen */
    #splash-screen {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-color: #0e1117;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        z-index: 999999;
        animation: fadeOut 0.8s ease-in-out 1.8s forwards;
    }}
    
    @keyframes fadeOut {{
        0% {{ opacity: 1; visibility: visible; }}
        100% {{ opacity: 0; visibility: hidden; }}
    }}

    .splash-logo-img {{
        max-width: 180px;
        max-height: 180px;
        object-fit: contain;
        margin-bottom: 20px;
    }}

    .splash-loader {{
        border: 4px solid #262730;
        border-top: 4px solid #ff4b4b;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
    }}

    @keyframes spin {{
        0% {{ transform: rotate(0deg); }}
        100% {{ transform: rotate(360deg); }}
    }}

    .stApp {{
        background-color: #0e1117 !important;
    }}

    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    
    .block-container {{
        padding-top: 0.8rem !important;
        padding-bottom: 0rem !important;
        padding-left: 0.6rem !important;
        padding-right: 0.6rem !important;
    }}

    /* ENCABEZADO CENTRADO PERFECTO EN MÓVIL Y ESCRITORIO */
    .header-logo-container {{
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 12px;
        margin-bottom: 12px;
        width: 100%;
        text-align: center;
    }}
    
    .header-logo-img {{
        height: 52px !important;
        width: auto;
        object-fit: contain;
    }}

    .header-text-group {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }}

    .header-title {{
        color: #ffffff;
        font-weight: 900;
        font-size: 22px;
        line-height: 1.1;
        letter-spacing: 1px;
        margin: 0;
        padding: 0;
        text-align: center;
    }}

    /* MÉTRICAS COMPLETAMENTE CENTRADAS */
    [data-testid="stMetric"] {{
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
    }}

    [data-testid="stMetricValue"] {{
        font-size: 28px !important;
        font-weight: 800 !important;
        color: #ffffff !important;
        text-align: center !important;
        width: 100% !important;
    }}

    [data-testid="stMetricLabel"] {{
        font-size: 16px !important;
        font-weight: 600 !important;
        color: #e0e0e0 !important;
        text-align: center !important;
        width: 100% !important;
    }}

    /* BOTÓN REINICIAR */
    .btn-reiniciar-wrap button {{
        height: 42px !important;
        font-size: 14px !important;
        font-weight: 700 !important;
        background-color: #ffffff !important;
        color: #2c3e50 !important;
        border-radius: 8px !important;
        border: none !important;
    }}

    /* BOTÓN-TARJETA INTEGRADO (UNA SOLA FILA ESTRICTA SIN BOTONES EXTRA) */
    .item-card-btn {{
        width: 100% !important;
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin: 0 0 10px 0 !important;
        cursor: pointer !important;
    }}

    .item-card-btn button {{
        width: 100% !important;
        padding: 0 !important;
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
    }}

    .item-card-flex {{
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        width: 100% !important;
        height: 54px !important;
    }}

    .item-name-box {{
        flex: 1 1 78% !important;
        height: 54px !important;
        background-color: #ffffff;
        color: #2c3e50;
        border-top-left-radius: 8px;
        border-bottom-left-radius: 8px;
        border-left: 6px solid #ff4b4b;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
        font-weight: 700;
        padding: 0 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.15);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}

    .item-name-box.completed {{
        background-color: #d1fae5;
        color: #065f46;
        border-left: 6px solid #10b981;
    }}

    .item-qty-box {{
        flex: 0 0 22% !important;
        height: 54px !important;
        background-color: #ff4b4b;
        color: #ffffff;
        border-top-right-radius: 8px;
        border-bottom-right-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
        font-weight: 900;
        box-shadow: 0 2px 4px rgba(0,0,0,0.15);
        margin-left: 4px;
    }}

    .item-qty-box.completed {{
        background-color: #10b981;
    }}

    @media (max-width: 768px) {{
        .grid-3-cols > div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
            width: 100% !important;
            flex: 1 1 100% !important;
        }}
        .header-title {{
            font-size: 20px;
        }}
        .header-logo-img {{
            height: 46px !important;
        }}
    }}
    </style>

    <!-- Splash Screen -->
    <div id="splash-screen">
        <img src="{LOGO_URL}" class="splash-logo-img" alt="Logo">
        <div class="splash-loader"></div>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 4. CONSULTA A LA API DE LOYVERSE
# ==========================================
def obtener_recibos_hoy():
    created_at_min = estado_global["hora_corte_utc"].strftime("%Y-%m-%dT%H:%M:%SZ")
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
# 5. FRAGMENTO AUTO-REGENERABLE (CADA 10s)
# ==========================================
@st.fragment(run_every=10)
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

    for prod, cant_total in conteo_productos.items():
        if prod in estado_global["completados"]:
            cant_marcada = estado_global["cantidades_al_completar"].get(prod, cant_total)
            if cant_total > cant_marcada:
                estado_global["completados"].remove(prod)
                estado_global["cantidades_al_completar"].pop(prod, None)

    if "ultimo_conteo" not in st.session_state:
        st.session_state.ultimo_conteo = conteo_productos.copy()
    else:
        nuevo_pedido_detectado = False
        for prod, cant in conteo_productos.items():
            cant_anterior = st.session_state.ultimo_conteo.get(prod, 0)
            if cant > cant_anterior:
                nuevo_pedido_detectado = True
                break

        if nuevo_pedido_detectado:
            reproducir_sonido_notificacion()
            st.toast("🔔 ¡Nuevo pedido recibido!", icon="🔔")

        st.session_state.ultimo_conteo = conteo_productos.copy()

    # Encabezado Alinear y Centrar
    st.markdown(f"""
        <div class="header-logo-container">
            <img src="{LOGO_URL}" class="header-logo-img" alt="Logo">
            <div class="header-text-group">
                <h1 class="header-title">TABLA DE<br>PRODUCCIÓN</h1>
                <span style="font-size:11px; color:#a0a0a0; margin-top:2px;">🔄 Sincronizado cada 10s | Última: {datetime.now().strftime('%H:%M:%S')}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="btn-reiniciar-wrap">', unsafe_allow_html=True)
    st.button("Reiniciar", use_container_width=True, on_click=reiniciar_contador)
    st.markdown('</div>', unsafe_allow_html=True)

    piezas_pendientes = 0
    for prod, cant_total in conteo_productos.items():
        if prod in estado_global["completados"]:
            cant_marcada = estado_global["cantidades_al_completar"].get(prod, cant_total)
            piezas_pendientes += max(0, cant_total - cant_marcada)
        else:
            cant_marcada = estado_global["cantidades_al_completar"].get(prod, 0)
            piezas_pendientes += (cant_total - cant_marcada)

    m1, m2 = st.columns(2)
    m1.metric("Tickets", len(recibos))
    m2.metric("Pendientes", piezas_pendientes)

    st.markdown("<br>", unsafe_allow_html=True)

    if conteo_productos:
        productos_ordenados = sorted(conteo_productos.items(), key=lambda x: x[1], reverse=True)

        st.markdown('<div class="grid-3-cols">', unsafe_allow_html=True)
        col_a, col_b, col_c = st.columns(3)
        columnas = [col_a, col_b, col_c]

        for idx, (producto, cant_total) in enumerate(productos_ordenados):
            col_destino = columnas[idx % 3]
            es_completado = producto in estado_global["completados"]
            
            cant_base = estado_global["cantidades_al_completar"].get(producto, 0)
            cant_mostrar = cant_total if es_completado else (cant_total - cant_base)

            status_class = "completed" if es_completado else ""

            html_card = f"""
                <div class="item-card-flex">
                    <div class="item-name-box {status_class}">{producto}</div>
                    <div class="item-qty-box {status_class}">{cant_mostrar}</div>
                </div>
            """

            with col_destino:
                st.button(
                    label=html_card,
                    key=f"btn_{producto}",
                    use_container_width=True,
                    on_click=alternar_estado,
                    args=(producto, cant_total)
                )

        st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.info("No hay pedidos registrados en este periodo.")

renderizar_tablero()