import base64
import os
import requests
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timezone, timedelta

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
# 2. ESTADO GLOBAL EN MEMORIA CON RESPALDO
# ==========================================
@st.cache_resource
def obtener_estado_global():
    return {
        "completados": set(),
        "cantidades_al_completar": {},
        "hora_corte_utc": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0),
        "respaldo": None
    }

estado_global = obtener_estado_global()

def borrar_todo():
    estado_global["respaldo"] = {
        "completados": estado_global["completados"].copy(),
        "cantidades_al_completar": estado_global["cantidades_al_completar"].copy(),
        "hora_corte_utc": estado_global["hora_corte_utc"]
    }
    estado_global["hora_corte_utc"] = datetime.now(timezone.utc)
    estado_global["completados"].clear()
    estado_global["cantidades_al_completar"].clear()
    st.toast("🗑 Tablero limpiado. Puedes restaurarlo si fue un error.", icon="ℹ️")

def restaurar_estado():
    if estado_global["respaldo"]:
        estado_global["completados"] = estado_global["respaldo"]["completados"].copy()
        estado_global["cantidades_al_completar"] = estado_global["respaldo"]["cantidades_al_completar"].copy()
        estado_global["hora_corte_utc"] = estado_global["respaldo"]["hora_corte_utc"]
        estado_global["respaldo"] = None
        st.toast("↩️ Tablero restaurado con éxito.", icon="✅")
    else:
        st.toast("⚠️ No hay respaldo anterior para restaurar.", icon="⚠️")

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
        function sonar() {
            try {
                var AudioContext = window.AudioContext || window.webkitAudioContext;
                if (!AudioContext) return;
                var ctx = new AudioContext();
                if (ctx.state === 'suspended') {
                    ctx.resume();
                }
                
                var osc1 = ctx.createOscillator();
                var gain1 = ctx.createGain();
                osc1.type = 'sine';
                osc1.frequency.setValueAtTime(587.33, ctx.currentTime);
                gain1.gain.setValueAtTime(0.3, ctx.currentTime);
                gain1.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.25);
                osc1.connect(gain1);
                gain1.connect(ctx.destination);
                osc1.start(ctx.currentTime);
                osc1.stop(ctx.currentTime + 0.25);

                var osc2 = ctx.createOscillator();
                var gain2 = ctx.createGain();
                osc2.type = 'sine';
                osc2.frequency.setValueAtTime(880, ctx.currentTime + 0.15);
                gain2.gain.setValueAtTime(0.35, ctx.currentTime + 0.15);
                gain2.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.45);
                osc2.connect(gain2);
                gain2.connect(ctx.destination);
                osc2.start(ctx.currentTime + 0.15);
                osc2.stop(ctx.currentTime + 0.45);
            } catch(e) {}
        }
        sonar();
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
        max-width: 150px; max-height: 150px; object-fit: contain; margin-bottom: 12px;
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

    /* ENCABEZADO DESTACADO */
    .header-logo-container {{
        display: flex; justify-content: center; align-items: center;
        gap: 12px; margin-bottom: 6px; width: 100%; text-align: center;
    }}
    
    .header-logo-img {{ height: 45px !important; width: auto; object-fit: contain; }}
    .header-text-group {{ display: flex; flex-direction: column; align-items: center; justify-content: center; }}

    .header-title {{
        color: #ffffff; font-weight: 900; font-size: 22px !important;
        line-height: 1.1; letter-spacing: 0.8px; margin: 0; padding: 0; text-align: center; white-space: nowrap;
    }}

    /* BOTONES DE ACCIÓN (BORRAR Y RESTAURAR) */
    .btn-borrar button {{
        height: 36px !important; font-size: 13px !important; font-weight: 800 !important;
        background-color: #e55353 !important; color: #ffffff !important;
        border-radius: 6px !important; border: none !important;
    }}
    .btn-borrar button:hover {{ background-color: #c93b3b !important; }}

    .btn-restaurar button {{
        height: 36px !important; font-size: 13px !important; font-weight: 800 !important;
        background-color: #3b82f6 !important; color: #ffffff !important;
        border-radius: 6px !important; border: none !important;
    }}
    .btn-restaurar button:hover {{ background-color: #2563eb !important; }}

    /* MÉTRICAS */
    .metrics-row {{
        display: flex; justify-content: space-around; align-items: center;
        background-color: #1a1d24; border-radius: 6px; padding: 4px 8px;
        margin-bottom: 8px; border: 1px solid #2d3139;
    }}

    .metric-inline {{ display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 800; color: #ffffff; }}
    .metric-inline .val {{ font-size: 16px; font-weight: 900; color: #e55353; }}

    /* BANNER DE FELICITACIONES */
    .banner-felicidades {{
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: #ffffff;
        padding: 10px 14px;
        border-radius: 8px;
        text-align: center;
        font-size: 15px;
        font-weight: 900;
        margin-bottom: 10px;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
        animation: pulseGlow 2s infinite alternate;
    }}

    @keyframes pulseGlow {{
        0% {{ transform: scale(0.99); box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4); }}
        100% {{ transform: scale(1.01); box-shadow: 0 6px 18px rgba(16, 185, 129, 0.7); }}
    }}

    /* TARJETA DE TEXTO DEL PRODUCTO (AJUSTADA) */
    .card-box-img {{
        border-radius: 12px;
        height: 110px !important;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 0 8px;
        font-size: 15px;
        font-weight: 800 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        white-space: normal;
        word-wrap: break-word;
        line-height: 1.25;
        margin-bottom: 8px;
        transition: all 0.3s ease;
    }}

    /* TARJETA PENDIENTE (ROJO CÁLIDO / SUAVE) */
    .card-pendiente {{
        background-color: #e55353 !important;
        color: #ffffff !important;
        border: 1px solid #c93b3b !important;
    }}

    /* TARJETA COMPLETADA (VERDE TOTAL) */
    .card-completado {{
        background-color: #10b981 !important;
        color: #ffffff !important;
        border: 1px solid #059669 !important;
    }}

    /* ESTADO TEMPORAL AZUL DESTACADO (NUEVO PRODUCTO / 2 MINUTOS) */
    .card-nueva-orden {{
        background-color: #2563eb !important;
        color: #ffffff !important;
        border: 2px solid #60a5fa !important;
        animation: destelloUpdate 1.5s infinite alternate !important;
    }}

    @keyframes destelloUpdate {{
        0% {{ box-shadow: 0 0 6px #3b82f6; transform: scale(0.99); }}
        100% {{ box-shadow: 0 0 18px #60a5fa; transform: scale(1.01); }}
    }}

    /* CONTENEDOR Y BOTÓN DEL NÚMERO GIGANTESCO */
    div[data-testid="stElementContainer"]:has(button[key^="num_btn_"]) {{
        height: 110px !important;
    }}

    div[data-testid="stElementContainer"]:has(button[key^="num_btn_"]) button {{
        height: 110px !important;
        min-height: 110px !important;
        max-height: 110px !important;
        border-radius: 12px !important;
        border: none !important;
        font-size: 95px !important; /* NÚMERO GIGANTE ULTRA VISIBLE */
        font-weight: 900 !important; /* NEGRITA ABSOLUTA */
        line-height: 110px !important;
        padding: 0px !important;
        color: #ffffff !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.4) !important;
        margin-bottom: 8px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }}

    div[data-testid="stElementContainer"]:has(button[key^="num_btn_"]) button p {{
        font-size: 95px !important;
        font-weight: 900 !important;
        line-height: 1 !important;
        margin: 0 !important;
        padding: 0 !important;
    }}

    /* COLORES DE ESTADO PARA EL BOTÓN NUMÉRICO */
    .btn-num-pendiente button {{
        background-color: #c93b3b !important;
        color: #ffffff !important;
    }}

    .btn-num-completado button {{
        background-color: #059669 !important;
        color: #ffffff !important;
    }}

    .btn-num-reciente button {{
        background-color: #1d4ed8 !important;
        color: #ffffff !important;
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

    # Control del tiempo de actualización para resplandor azul (2 minutos = 120 segundos)
    if "tiempos_actualizacion" not in st.session_state:
        st.session_state.tiempos_actualizacion = {}

    if "ultimo_conteo" not in st.session_state:
        st.session_state.ultimo_conteo = conteo_productos.copy()
    else:
        nuevo_pedido_detectado = False
        ahora = datetime.now()
        for prod, cant in conteo_productos.items():
            cant_anterior = st.session_state.ultimo_conteo.get(prod, 0)
            if cant > cant_anterior:
                nuevo_pedido_detectado = True
                st.session_state.tiempos_actualizacion[prod] = ahora

        if nuevo_pedido_detectado:
            reproducir_sonido_notificacion()
            st.toast("🔔 ¡Nuevo pedido recibido!", icon="🔔")

        st.session_state.ultimo_conteo = conteo_productos.copy()

    # Encabezado con Logo y Título Prominentes
    st.markdown(f"""
        <div class="header-logo-container">
            <img src="{LOGO_URL}" class="header-logo-img" alt="Logo">
            <div class="header-text-group">
                <h1 class="header-title">TABLA DE PRODUCCIÓN</h1>
                <span style="font-size:10px; color:#a0a0a0;">🔄 Sincronizado | {datetime.now().strftime('%H:%M:%S')}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Botones de Acción
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        st.markdown('<div class="btn-borrar">', unsafe_allow_html=True)
        st.button("🗑️ Borrar todo", use_container_width=True, on_click=borrar_todo)
        st.markdown('</div>', unsafe_allow_html=True)
    with col_b2:
        st.markdown('<div class="btn-restaurar">', unsafe_allow_html=True)
        st.button("↩️ Restaurar", use_container_width=True, on_click=restaurar_estado)
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
                <span class="val" style="color: {'#10b981' if piezas_pendientes == 0 else '#e55353'};">{piezas_pendientes}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Banner de Felicitación si todo está listo
    if conteo_productos and piezas_pendientes == 0:
        st.markdown("""
            <div class="banner-felicidades">
                🎉 ¡Felicidades! Hacemos un gran equipo, logramos terminar todo.
            </div>
        """, unsafe_allow_html=True)

    if conteo_productos:
        productos_ordenados = sorted(conteo_productos.items(), key=lambda x: x[1], reverse=True)
        ahora_actual = datetime.now()

        # RENDERIZADO EN GRILLA DE 3 COLUMNAS
        for i in range(0, len(productos_ordenados), 3):
            grupo = productos_ordenados[i:i+3]
            cols = st.columns(3)

            for idx, (producto, cant_total) in enumerate(grupo):
                with cols[idx]:
                    es_completado = producto in estado_global["completados"]
                    cant_base = estado_global["cantidades_al_completar"].get(producto, 0)
                    cant_mostrar = cant_total if es_completado else (cant_total - cant_base)

                    # Validar si han pasado menos de 2 minutos (120 s) desde la última actualización
                    ultima_upd = st.session_state.tiempos_actualizacion.get(producto)
                    es_reciente = False
                    if ultima_upd and (ahora_actual - ultima_upd).total_seconds() < 120 and not es_completado:
                        es_reciente = True

                    # Selección de la clase de color principal y del botón
                    if es_reciente:
                        clase_estado = "card-nueva-orden"
                        clase_btn = "btn-num-reciente"
                    elif es_completado:
                        clase_estado = "card-completado"
                        clase_btn = "btn-num-completado"
                    else:
                        clase_estado = "card-pendiente"
                        clase_btn = "btn-num-pendiente"

                    # CONVERSIÓN DEL NÚMERO 1 A SÍMBOLO DE INFINITO (∞)
                    valor_mostrar = "∞" if cant_mostrar == 1 else str(cant_mostrar)
                    tag_update = "✨ " if es_reciente else ""

                    # REPROPORCIONADO: 40% Nombre del producto / 60% Número Gigante
                    col_txt, col_btn = st.columns([0.40, 0.60], gap="small")

                    with col_txt:
                        st.markdown(f"""
                            <div class="card-box-img {clase_estado}">
                                {tag_update}<b>{producto}</b>
                            </div>
                        """, unsafe_allow_html=True)

                    with col_btn:
                        st.markdown(f'<div class="{clase_btn}">', unsafe_allow_html=True)
                        st.button(
                            valor_mostrar, 
                            key=f"num_btn_{producto}", 
                            on_click=alternar_estado, 
                            args=(producto, cant_total),
                            use_container_width=True
                        )
                        st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.info("No hay pedidos registrados en este periodo.")

renderizar_tablero()