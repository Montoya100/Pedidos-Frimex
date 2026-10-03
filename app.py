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
# 3. ESTILOS CSS ESTÁTICOS (SIN PARPADEO)
# ==========================================
st.markdown(f"""
    <style>
    /* ELIMINAR EL PARPADEO / OPACIDAD DURANTE EL REFRESCADO */
    div[data-testid="stAppViewContainer"],
    div[data-testid="stMain"],
    section[data-testid="stSidebar"],
    .element-container,
    div[data-testid="stFragment"] {{
        opacity: 1 !important;
        transition: none !important;
        animation: none !important;
    }}

    .stApp {{ background-color: #0e1117 !important; }}
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    
    .block-container {{
        padding-top: 0.4rem !important; padding-bottom: 0rem !important;
        padding-left: 0.4rem !important; padding-right: 0.4rem !important;
    }}

    /* ENCABEZADO DESTACADO Y COMPACTO */
    .header-logo-container {{
        display: flex; justify-content: center; align-items: center;
        gap: 12px; margin-bottom: 4px; width: 100%; text-align: center;
    }}
    
    .header-logo-img {{ height: 42px !important; width: auto; object-fit: contain; }}
    .header-text-group {{ display: flex; flex-direction: column; align-items: center; justify-content: center; }}

    .header-title {{
        color: #ffffff; font-weight: 900; font-size: 22px !important;
        line-height: 1.1; letter-spacing: 0.8px; margin: 0; padding: 0; text-align: center; white-space: nowrap;
    }}

    /* MÉTRICAS EN LÍNEA */
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
    }}

    /* SEPARADOR DE SECCIÓN COMPLETADOS */
    .divider-completados {{
        display: flex;
        align-items: center;
        text-align: center;
        color: #10b981;
        font-size: 12px;
        font-weight: 900;
        letter-spacing: 1.5px;
        margin: 12px 0 8px 0;
    }}

    .divider-completados::before, .divider-completados::after {{
        content: '';
        flex: 1;
        border-bottom: 2px dashed #10b981;
        opacity: 0.4;
    }}

    .divider-completados span {{
        padding: 0 10px;
    }}

    /* TARJETA DE TEXTO DEL PRODUCTO */
    .card-box-img {{
        border-radius: 10px;
        height: 100px !important;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 0 10px;
        font-size: 30px !important;
        font-weight: 900 !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        white-space: normal;
        word-wrap: break-word;
        line-height: 1.15;
        margin-bottom: 6px;
    }}

    /* CAJA DEL NÚMERO MASIVO GIGANTE */
    .num-box-masivo {{
        border-radius: 10px;
        height: 100px !important;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 68px !important;
        font-weight: 900 !important;
        line-height: 1 !important;
        box-shadow: 0 3px 6px rgba(0,0,0,0.3);
        margin-bottom: 6px;
        user-select: none;
    }}

    .num-box-pendiente {{ background-color: #c93b3b !important; color: #ffffff !important; }}
    .num-box-completado {{ background-color: #059669 !important; color: #ffffff !important; opacity: 0.75; }}
    .num-box-reciente {{ background-color: #1d4ed8 !important; }}

    /* TARJETA PENDIENTE (ROJO) */
    .card-pendiente {{
        background-color: #e55353 !important;
        color: #ffffff !important;
        border: 1px solid #c93b3b !important;
    }}

    /* TARJETA COMPLETADA (VERDE) */
    .card-completado {{
        background-color: #10b981 !important;
        color: #ffffff !important;
        border: 1px solid #059669 !important;
        opacity: 0.75;
    }}

    /* ESTADO TEMPORAL AZUL (NUEVO PRODUCTO) */
    .card-nueva-orden {{
        background-color: #2563eb !important;
        color: #ffffff !important;
        border: 2px solid #60a5fa !important;
    }}

    /* BOTÓN TRANSPARENTE SUPERPUESTO */
    div[data-testid="stElementContainer"]:has(button[key^="num_btn_"]) {{
        height: 100px !important;
        margin-top: -106px !important;
    }}

    div[data-testid="stElementContainer"]:has(button[key^="num_btn_"]) button {{
        height: 100px !important;
        min-height: 100px !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        display: flex !important;
        align-items: flex-end !important;
        justify-content: center !important;
        padding-bottom: 6px !important;
    }}

    /* ETIQUETA EN BOTÓN TRANSPARENTE */
    div[data-testid="stElementContainer"]:has(button[key^="num_btn_"]) button * {{
        font-size: 11px !important;
        font-weight: 900 !important;
        letter-spacing: 1.2px !important;
        text-transform: uppercase !important;
        color: #ffffff !important;
        opacity: 0.95 !important;
    }}

    /* ESTILO BOTÓN DE CONFIGURACIÓN / DRAWER POP-OVER */
    div[data-testid="stPopover"] button {{
        height: 32px !important;
        font-size: 12px !important;
        font-weight: 800 !important;
        background-color: #262730 !important;
        color: #cccccc !important;
        border: 1px solid #3d424d !important;
        border-radius: 6px !important;
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

    # ENCABEZADO CON DRAWER / POPOVER DE CONFIGURACIÓN INTEGRADO EN LA MISMA LÍNEA
    col_hdr_left, col_hdr_center, col_hdr_right = st.columns([0.15, 0.70, 0.15])
    
    with col_hdr_center:
        st.markdown(f"""
            <div class="header-logo-container">
                <img src="{LOGO_URL}" class="header-logo-img" alt="Logo">
                <div class="header-text-group">
                    <h1 class="header-title">TABLA DE PRODUCCIÓN</h1>
                    <span style="font-size:10px; color:#a0a0a0;">🔄 Sincronizado | {datetime.now().strftime('%H:%M:%S')}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col_hdr_right:
        # Menú desplegable oculto (Popover / Drawer) para ganar el espacio superior
        with st.popover("⚙️ Opciones", use_container_width=True):
            st.markdown("### Acciones de Tablero")
            if st.button("🗑️ Borrar todo", use_container_width=True):
                borrar_todo()
            if st.button("↩️ Restaurar", use_container_width=True):
                restaurar_estado()

    # Cálculo de métricas
    piezas_pendientes = 0
    for prod, cant_total in conteo_productos.items():
        if prod in estado_global["completados"]:
            cant_marcada = estado_global["cantidades_al_completar"].get(prod, cant_total)
            piezas_pendientes += max(0, cant_total - cant_marcada)
        else:
            cant_marcada = estado_global["cantidades_al_completar"].get(prod, 0)
            piezas_pendientes += (cant_total - cant_marcada)

    # Métricas
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

    if conteo_productos and piezas_pendientes == 0:
        st.markdown("""
            <div class="banner-felicidades">
                🎉 ¡Felicidades! Hacemos un gran equipo, logramos terminar todo.
            </div>
        """, unsafe_allow_html=True)

    if conteo_productos:
        activos = []
        completados = []

        for prod, cant_total in conteo_productos.items():
            if prod in estado_global["completados"]:
                completados.append((prod, cant_total))
            else:
                activos.append((prod, cant_total))

        activos.sort(key=lambda x: x[1], reverse=True)
        completados.sort(key=lambda x: x[1], reverse=True)

        ahora_actual = datetime.now()

        def renderizar_lista_productos(lista):
            for i in range(0, len(lista), 3):
                grupo = lista[i:i+3]
                cols = st.columns(3)

                for idx, (producto, cant_total) in enumerate(grupo):
                    with cols[idx]:
                        es_completado = producto in estado_global["completados"]
                        cant_base = estado_global["cantidades_al_completar"].get(producto, 0)
                        cant_mostrar = cant_total if es_completado else (cant_total - cant_base)

                        ultima_upd = st.session_state.tiempos_actualizacion.get(producto)
                        es_reciente = False
                        if ultima_upd and (ahora_actual - ultima_upd).total_seconds() < 120 and not es_completado:
                            es_reciente = True

                        if es_reciente:
                            clase_estado = "card-nueva-orden"
                            clase_num_box = "num-box-reciente"
                            texto_estado = "NUEVO"
                        elif es_completado:
                            clase_estado = "card-completado"
                            clase_num_box = "num-box-completado"
                            texto_estado = "TERMINADO"
                        else:
                            clase_estado = "card-pendiente"
                            clase_num_box = "num-box-pendiente"
                            texto_estado = "PENDIENTE"

                        valor_mostrar = "∞" if cant_mostrar == 1 else str(cant_mostrar)
                        tag_update = "✨ " if es_reciente else ""

                        col_txt, col_btn = st.columns([0.70, 0.30], gap="small")

                        with col_txt:
                            st.markdown(f"""
                                <div class="card-box-img {clase_estado}">
                                    {tag_update}{producto}
                                </div>
                            """, unsafe_allow_html=True)

                        with col_btn:
                            st.markdown(f"""
                                <div class="num-box-masivo {clase_num_box}">
                                    {valor_mostrar}
                                </div>
                            """, unsafe_allow_html=True)
                            
                            st.button(
                                texto_estado, 
                                key=f"num_btn_{producto}", 
                                on_click=alternar_estado, 
                                args=(producto, cant_total),
                                use_container_width=True
                            )

        if activos:
            renderizar_lista_productos(activos)

        if completados:
            st.markdown("""
                <div class="divider-completados">
                    <span>PRODUCTOS TERMINADOS</span>
                </div>
            """, unsafe_allow_html=True)
            renderizar_lista_productos(completados)

    else:
        st.info("No hay pedidos registrados en este periodo.")

renderizar_tablero()