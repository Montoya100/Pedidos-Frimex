import base64
import os
import requests
import streamlit as st
import streamlit.components.v1 as components
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
HEADERS_LOYVERSE = {
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
# 2. ESTADO GLOBAL EN MEMORIA
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
        } catch(e) {}
    })();
    </script>
    """
    components.html(sound_js, height=0, width=0)

# ==========================================
# 3. ESTILOS CSS PERSONALIZADOS
# ==========================================
st.markdown(f"""
    <style>
    /* Splash Screen */
    #splash-screen {{
        position: fixed;
        top: 0; left: 0; width: 100vw; height: 100vh;
        background-color: #0e1117;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        z-index: 999999;
        animation: fadeOut 0.8s ease-in-out 1.8s forwards;
    }}
    
    @keyframes fadeOut {{
        0% {{ opacity: 1; visibility: visible; }}
        100% {{ opacity: 0; visibility: hidden; }}
    }}

    .splash-logo-img {{
        max-width: 130px; max-height: 130px; object-fit: contain; margin-bottom: 12px;
    }}

    .splash-loader {{
        border: 3px solid #262730; border-top: 3px solid #ff4b4b; border-radius: 50%;
        width: 30px; height: 30px; animation: spin 1s linear infinite;
    }}

    @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}

    .stApp {{ background-color: #0e1117 !important; }}
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    
    .block-container {{
        padding-top: 0.4rem !important; padding-bottom: 0rem !important;
        padding-left: 0.4rem !important; padding-right: 0.4rem !important;
    }}

    /* ENCABEZADO ULTRA COMPACTO */
    .header-logo-container {{
        display: flex; justify-content: center; align-items: center;
        gap: 8px; margin-bottom: 4px; width: 100%; text-align: center;
    }}
    
    .header-logo-img {{ height: 30px !important; width: auto; object-fit: contain; }}
    .header-text-group {{ display: flex; flex-direction: column; align-items: center; justify-content: center; }}

    .header-title {{
        color: #ffffff; font-weight: 900; font-size: 15px !important;
        line-height: 1; letter-spacing: 0.5px; margin: 0; padding: 0; text-align: center; white-space: nowrap;
    }}

    /* MÉTRICAS */
    .metrics-row {{
        display: flex; justify-content: space-around; align-items: center;
        background-color: #1a1d24; border-radius: 6px; padding: 4px 8px;
        margin-bottom: 8px; border: 1px solid #2d3139;
    }}

    .metric-inline {{ display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 700; color: #ffffff; }}
    .metric-inline .val {{ font-size: 16px; font-weight: 900; color: #ff4b4b; }}

    /* BOTÓN REINICIAR */
    .btn-reiniciar-wrap button {{
        height: 32px !important; font-size: 12px !important; font-weight: 700 !important;
        background-color: #ffffff !important; color: #2c3e50 !important;
        border-radius: 6px !important; border: none !important; margin-bottom: 6px !important;
    }}

    /* TARJETA DE TEXTO (PRODUCTO) - ESTÁTICA Y NEUTRA */
    .card-box-img {{
        background-color: #ffffff;
        border-radius: 10px;
        height: 48px;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 0 10px;
        font-size: 15px;
        font-weight: 800;
        color: #111827;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        margin-bottom: 6px;
        border: 1px solid #e5e7eb;
    }}

    /* CONTENEDOR DE LA TARJETA NUMÉRICA Y SU BOTÓN OVERLAY */
    .num-card-wrapper {{
        position: relative;
        width: 100%;
        height: 48px;
        margin-bottom: 6px;
    }}

    .num-card-visual {{
        width: 100%;
        height: 48px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
        font-weight: 900;
        color: #ffffff;
        box-shadow: 0 3px 6px rgba(0,0,0,0.3);
    }}

    /* ROJO SI ESTÁ PENDIENTE */
    .num-card-visual.pending {{
        background-color: #dc2626 !important;
    }}

    /* VERDE SI ESTÁ COMPLETADO */
    .num-card-visual.done {{
        background-color: #047857 !important;
    }}

    /* EL BOTÓN DE STREAMLIT SE HACE TRANSPARENTE Y CUBRE LA TARJETA COMPLETA */
    div[data-testid="stElementContainer"]:has(button[key^="num_btn_"]) {{
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        width: 100% !important;
        height: 48px !important;
        margin: 0 !important;
        z-index: 10 !important;
    }}

    div[data-testid="stElementContainer"] button[key^="num_btn_"] {{
        width: 100% !important;
        height: 48px !important;
        background-color: transparent !important;
        color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        cursor: pointer !important;
    }}

    div[data-testid="stElementContainer"] button[key^="num_btn_"]:hover {{
        background-color: rgba(255, 255, 255, 0.1) !important;
    }}

    /* MÓVIL / VERTICAL */
    @media (max-width: 768px) {{
        div[data-testid="stHorizontalBlock"] {{
            flex-direction: column !important;
            gap: 0px !important;
        }}
        div[data-testid="column"] {{
            width: 100% !important;
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

    try:
        while True:
            response = requests.get(url, headers=HEADERS_LOYVERSE, params=params, timeout=5)
            if response.status_code != 200:
                break

            data = response.json()
            recibos = data.get("receipts", [])
            todos_los_recibos.extend(recibos)

            cursor = data.get("cursor")
            if not cursor:
                break
            params["cursor"] = cursor
    except Exception:
        pass

    return todos_los_recibos

# ==========================================
# 5. TABLERO DE PEDIDOS EN TIEMPO REAL
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

    # Notificación de nuevo pedido
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
            <div class="header-text-group">
                <h1 class="header-title">TABLA DE PRODUCCIÓN</h1>
                <span style="font-size:9px; color:#a0a0a0;">🔄 Sincronizado | {datetime.now().strftime('%H:%M:%S')}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Botón de Reiniciar
    st.markdown('<div class="btn-reiniciar-wrap">', unsafe_allow_html=True)
    st.button("Reiniciar", use_container_width=True, on_click=reiniciar_contador)
    st.markdown('</div>', unsafe_allow_html=True)

    # Cálculo de métricas
    piezas_pendientes = 0
    for prod, cant_total in conteo_productos.items():
        if prod in estado_global["completados"]:
            cant_marcada = estado_global["cantidades_al_completar"].get(prod, cant_total)
            piezas_pendientes += max(0, cant_total - cant_marcada)
        else:
            cant_marcada = estado_global["cantidades_al_completar"].get(prod, 0)
            piezas_pendientes += (cant_total - cant_marcada)

    # Métricas en una línea horizontal
    st.markdown(f"""
        <div class="metrics-row">
            <div class="metric-inline">
                <span>Tickets:</span>
                <span class="val">{len(recibos)}</span>
            </div>
            <div style="border-left: 1px solid #3d424d; height: 14px;"></div>
            <div class="metric-inline">
                <span>Pendientes:</span>
                <span class="val" style="color: {'#10b981' if piezas_pendientes == 0 else '#ff4b4b'};">{piezas_pendientes}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if conteo_productos:
        productos_ordenados = sorted(conteo_productos.items(), key=lambda x: x[1], reverse=True)

        # RENDERIZADO EN GRILLA DE 3 COLUMNAS
        for i in range(0, len(productos_ordenados), 3):
            grupo = productos_ordenados[i:i+3]
            cols = st.columns(3)

            for idx, (producto, cant_total) in enumerate(grupo):
                with cols[idx]:
                    es_completado = producto in estado_global["completados"]
                    cant_base = estado_global["cantidades_al_completar"].get(producto, 0)
                    cant_mostrar = cant_total if es_completado else (cant_total - cant_base)

                    # Clase del color directo de la tarjeta numeral
                    clase_num = "done" if es_completado else "pending"

                    col_txt, col_btn = st.columns([0.74, 0.26], gap="small")

                    with col_txt:
                        st.markdown(f"""
                            <div class="card-box-img">
                                {producto}
                            </div>
                        """, unsafe_allow_html=True)

                    with col_btn:
                        # Renderizamos la tarjeta numeral HTML directa + Botón transparente encima
                        st.markdown(f"""
                            <div class="num-card-wrapper">
                                <div class="num-card-visual {clase_num}">
                                    {cant_mostrar}
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        st.button(
                            f"{cant_mostrar}", 
                            key=f"num_btn_{producto}", 
                            on_click=alternar_estado, 
                            args=(producto, cant_total),
                            use_container_width=True
                        )

    else:
        st.info("No hay pedidos registrados en este periodo.")

renderizar_tablero()