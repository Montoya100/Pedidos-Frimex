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
# 3. ESTILOS CSS REFINADOS PARA MÓVIL
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
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }}

    .header-logo-container {{
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 4px;
    }}
    
    .header-logo-img {{
        height: 52px !important;
        width: auto;
        object-fit: contain;
    }}

    .header-title {{
        color: #ffffff;
        font-weight: 900;
        font-size: 24px;
        line-height: 1.1;
        letter-spacing: 1px;
        margin: 0;
        padding: 0;
    }}

    /* Métricas principales */
    [data-testid="stMetricValue"] {{
        font-size: 28px !important;
        font-weight: 800 !important;
        color: #ffffff !important;
    }}

    [data-testid="stMetricLabel"] {{
        font-size: 16px !important;
        font-weight: 600 !important;
        color: #e0e0e0 !important;
    }}

    .btn-reiniciar button {{
        height: 42px !important;
        font-size: 14px !important;
        font-weight: 700 !important;
        background-color: #ffffff !important;
        color: #2c3e50 !important;
        border-radius: 8px !important;
        border: none !important;
    }}

    /* ESTRUCTURA RIGIDA EN FILA PARA CADA PRODUCTO */
    div[data-testid="stElementContainer"]:has(.prod-container-marker) {{
        margin-bottom: -10px !important;
    }}

    /* Fuerza a que el contenedor sea siempre Flex Row sin importar la pantalla */
    div[data-testid="stHorizontalBlock"]:has(.prod-container-marker) {{
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 10px !important;
        align-items: center !important;
        margin-bottom: 10px !important;
    }}

    /* Fija el tamaño exacto: 78% para la caja del producto y 22% para la cantidad */
    div[data-testid="stHorizontalBlock"]:has(.prod-container-marker) > div[data-testid="column"]:nth-child(1) {{
        width: 78% !important;
        flex: 0 0 78% !important;
        max-width: 78% !important;
    }}

    div[data-testid="stHorizontalBlock"]:has(.prod-container-marker) > div[data-testid="column"]:nth-child(2) {{
        width: 22% !important;
        flex: 0 0 22% !important;
        max-width: 22% !important;
    }}

    /* Botón blanco / verde de producto */
    div[data-testid="stHorizontalBlock"]:has(.prod-container-marker) button {{
        width: 100% !important;
        border-radius: 8px !important;
        padding: 4px 10px !important;
        margin: 0px !important;
        height: 52px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.15) !important;
    }}

    div[data-testid="stHorizontalBlock"]:has(.prod-container-marker) button p {{
        font-size: 15px !important;
        font-weight: 700 !important;
        text-align: center !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        margin: 0 !important;
    }}

    /* Pendiente */
    div[data-testid="stHorizontalBlock"]:has(.prod-container-marker) button[kind="secondary"] {{
        background-color: #ffffff !important;
        border: none !important;
        border-left: 6px solid #ff4b4b !important;
        color: #2c3e50 !important;
    }}

    /* Completado */
    div[data-testid="stHorizontalBlock"]:has(.prod-container-marker) button[kind="primary"] {{
        background-color: #d1fae5 !important;
        border: none !important;
        border-left: 6px solid #10b981 !important;
        color: #065f46 !important;
    }}

    /* Caja de número a la derecha */
    .qty-badge {{
        font-size: 22px;
        font-weight: 900;
        color: #ffffff;
        height: 52px;
        line-height: 52px;
        border-radius: 8px;
        width: 100%;
        text-align: center;
        display: block;
        box-shadow: 0 2px 4px rgba(0,0,0,0.15);
    }}
    .badge-pending {{ background-color: #ff4b4b; }}
    .badge-completed {{ background-color: #10b981; }}

    @media (max-width: 768px) {{
        .header-logo-img {{
            height: 48px !important;
        }}
        .header-title {{
            font-size: 20px;
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

    # Encabezado
    st.markdown(f"""
        <div class="header-logo-container">
            <img src="{LOGO_URL}" class="header-logo-img" alt="Logo">
            <div>
                <h1 class="header-title">TABLA DE<br>PRODUCCIÓN</h1>
                <span style="font-size:11px; color:#a0a0a0;">🔄 Sincronizado cada 10s | Última: {datetime.now().strftime('%H:%M:%S')}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="btn-reiniciar" style="margin-top:10px; margin-bottom:15px;">', unsafe_allow_html=True)
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

        for producto, cant_total in productos_ordenados:
            es_completado = producto in estado_global["completados"]
            
            cant_base = estado_global["cantidades_al_completar"].get(producto, 0)
            cant_mostrar = cant_total if es_completado else (cant_total - cant_base)

            # Marcador HTML para que el CSS aplique de forma estricta por fila horizontal
            st.markdown('<div class="prod-container-marker"></div>', unsafe_allow_html=True)
            col_btn_prod, col_qty = st.columns([0.78, 0.22])
            
            with col_btn_prod:
                st.button(
                    label=producto,
                    key=f"btn_{producto}",
                    type="primary" if es_completado else "secondary",
                    use_container_width=True,
                    on_click=alternar_estado,
                    args=(producto, cant_total)
                )
            
            with col_qty:
                badge_style = "badge-completed" if es_completado else "badge-pending"
                st.markdown(
                    f'<span class="qty-badge {badge_style}">{cant_mostrar}</span>', 
                    unsafe_allow_html=True
                )

    else:
        st.info("No hay pedidos registrados en este periodo.")

renderizar_tablero()