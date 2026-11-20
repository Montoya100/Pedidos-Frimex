import base64
import os
import requests
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timezone, timedelta
import zoneinfo

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y FAVICON
# ==========================================
st.set_page_config(
    page_title="MOSTACHO BOTANAS - ONE UI", 
    page_icon="logo.png" if os.path.exists("logo.png") else "⚡",
    layout="wide",
    initial_sidebar_state="expanded"
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
# INYECCIÓN DE METADATOS PARA COMPARTIR ENLACE (THUMBNAIL/OG)
# ==========================================
st.markdown(f"""
    <head>
        <meta property="og:title" content="MOSTACHO BOTANAS - TABLA DE PRODUCCIÓN">
        <meta property="og:description" content="Sistema de control y producción en tiempo real.">
        <meta property="og:image" content="{LOGO_URL}">
    </head>
""", unsafe_allow_html=True)

# ==========================================
# 2. ESTADO GLOBAL COMPARTIDO Y PERSISTENTE
# ==========================================
@st.cache_resource
def obtener_estado_global():
    return {
        "completados": set(),
        "cantidades_al_completar": {},
        "notas_tablero": ["", "", ""],
        "productos_manuales_global": {},  
        "colaboradores": ["COLABORADOR 1", "COLABORADOR 2", "COLABORADOR 3", "COLABORADOR 4", "COLABORADOR 5", "COLABORADOR 6"],
        "asignaciones_productos": {}, # {producto: nombre_colaborador}
        "hora_corte_utc": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0),
        "respaldo": None,
        "descartar_celebracion": False
    }

estado_global = obtener_estado_global()

def borrar_todo():
    estado_global["respaldo"] = {
        "completados": estado_global["completados"].copy(),
        "cantidades_al_completar": estado_global["cantidades_al_completar"].copy(),
        "productos_manuales_global": {k: v.copy() for k, v in estado_global["productos_manuales_global"].items()},
        "notas_tablero": estado_global["notas_tablero"].copy(),
        "colaboradores": estado_global["colaboradores"].copy(),
        "asignaciones_productos": estado_global["asignaciones_productos"].copy(),
        "hora_corte_utc": estado_global["hora_corte_utc"]
    }
    estado_global["hora_corte_utc"] = datetime.now(timezone.utc)
    estado_global["completados"].clear()
    estado_global["cantidades_al_completar"].clear()
    estado_global["productos_manuales_global"].clear()
    estado_global["asignaciones_productos"].clear()
    estado_global["notas_tablero"] = ["", "", ""]
    estado_global["descartar_celebracion"] = False
    st.toast("Tablero limpiado y barrera de corte establecida")

def restaurar_estado():
    if estado_global["respaldo"]:
        estado_global["completados"] = estado_global["respaldo"]["completados"].copy()
        estado_global["cantidades_al_completar"] = estado_global["respaldo"]["cantidades_al_completar"].copy()
        estado_global["productos_manuales_global"] = {k: v.copy() for k, v in estado_global["respaldo"]["productos_manuales_global"].items()}
        estado_global["notas_tablero"] = estado_global["respaldo"]["notas_tablero"].copy()
        estado_global["colaboradores"] = estado_global["respaldo"]["colaboradores"].copy()
        estado_global["asignaciones_productos"] = estado_global["respaldo"]["asignaciones_productos"].copy()
        estado_global["hora_corte_utc"] = estado_global["respaldo"]["hora_corte_utc"]
        estado_global["respaldo"] = None
        estado_global["descartar_celebracion"] = False
        st.toast("Tablero restaurado correctamente")
    else:
        st.toast("Sin respaldo previo disponible")

def alternar_estado(producto, cantidad_actual):
    if producto in estado_global["completados"]:
        estado_global["completados"].remove(producto)
        estado_global["cantidades_al_completar"].pop(producto, None)
    else:
        estado_global["completados"].add(producto)
        estado_global["cantidades_al_completar"][producto] = cantidad_actual

    estado_global["descartar_celebracion"] = False

def asignar_colaborador(producto, colaborador):
    if colaborador and colaborador != "NINGUNO":
        estado_global["asignaciones_productos"][producto] = colaborador
        st.toast(f"Asignado a {colaborador}")
    else:
        estado_global["asignaciones_productos"].pop(producto, None)
        st.toast("Asignación retirada")

# ==========================================
# SONIDOS DE NOTIFICACIÓN
# ==========================================
def reproducir_sonido_notificacion():
    sound_js = """
    <script>
    (function() {
        function sonar() {
            try {
                var AudioContext = window.AudioContext || window.webkitAudioContext;
                if (!AudioContext) return;
                var ctx = new AudioContext();
                if (ctx.state === 'suspended') { ctx.resume(); }
                
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

def reproducir_sonido_nota():
    sound_js = """
    <script>
    (function() {
        function sonarNota() {
            try {
                var AudioContext = window.AudioContext || window.webkitAudioContext;
                if (!AudioContext) return;
                var ctx = new AudioContext();
                if (ctx.state === 'suspended') { ctx.resume(); }

                var frecuencias = [440, 659.25, 987.77];
                frecuencias.forEach(function(freq, i) {
                    var osc = ctx.createOscillator();
                    var gain = ctx.createGain();
                    osc.type = 'square';
                    osc.frequency.setValueAtTime(freq, ctx.currentTime + (i * 0.1));
                    
                    gain.gain.setValueAtTime(0.2, ctx.currentTime + (i * 0.1));
                    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + (i * 0.1) + 0.2);
                    
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    osc.start(ctx.currentTime + (i * 0.1));
                    osc.stop(ctx.currentTime + (i * 0.1) + 0.2);
                });
            } catch(e) {}
        }
        sonarNota();
    })();
    </script>
    """
    components.html(sound_js, height=0, width=0)

def reproducir_sonido_celebracion():
    sound_js = """
    <script>
    (function() {
        function celebrar() {
            try {
                var AudioContext = window.AudioContext || window.webkitAudioContext;
                if (!AudioContext) return;
                var ctx = new AudioContext();
                if (ctx.state === 'suspended') { ctx.resume(); }

                var notas = [523.25, 659.25, 783.99, 1046.50];
                var tiempoInicio = ctx.currentTime;

                notas.forEach(function(freq, index) {
                    var osc = ctx.createOscillator();
                    var gain = ctx.createGain();
                    osc.type = 'triangle';
                    osc.frequency.setValueAtTime(freq, tiempoInicio + (index * 0.12));
                    
                    gain.gain.setValueAtTime(0.4, tiempoInicio + (index * 0.12));
                    gain.gain.exponentialRampToValueAtTime(0.001, tiempoInicio + (index * 0.12) + 0.35);
                    
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    osc.start(tiempoInicio + (index * 0.12));
                    osc.stop(tiempoInicio + (index * 0.12) + 0.35);
                });
            } catch(e) {}
        }
        celebrar();
    })();
    </script>
    """
    components.html(sound_js, height=0, width=0)

# ==========================================
# 3. ESTILOS CSS
# ==========================================
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@700;800;900&family=JetBrains+Mono:wght@800;900&display=swap');

    div[data-testid="stAppViewContainer"],
    div[data-testid="stMain"],
    section[data-testid="stSidebar"],
    .element-container,
    div[data-testid="stFragment"] {{
        opacity: 1 !important;
        transition: none !important;
        animation: none !important;
    }}

    .stApp {{ background-color: #0b0f19 !important; font-family: 'Plus Jakarta Sans', sans-serif !important; color-scheme: dark !important; }}
    
    #MainMenu, footer, header, 
    div[data-testid="stToolbar"], 
    div[data-testid="stDecoration"], 
    div[data-testid="stStatusWidget"],
    .stAppDeployButton {{
        visibility: hidden !important;
        display: none !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }}
    
    .block-container {{
        padding-top: 0.1rem !important; 
        padding-bottom: 2.5rem !important;
        padding-left: 0.3rem !important; 
        padding-right: 0.3rem !important;
        max-width: 100% !important;
    }}

    @keyframes deslizarDegradado {{
        0% {{ opacity: 0; transform: translateY(-5px); background-position: 200% 0; }}
        100% {{ opacity: 1; transform: translateY(0); background-position: 0 0; }}
    }}

    .banner-notas-container {{
        background: linear-gradient(135deg, #182232 0%, #111827 50%, #0077ed 200%);
        background-size: 200% 100%;
        animation: deslizarDegradado 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        border: 1px solid rgba(0, 119, 237, 0.3);
        border-radius: 14px;
        padding: 8px 14px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
        display: flex;
        align-items: center;
        width: 100% !important;
        box-sizing: border-box;
        gap: 10px;
        min-height: 44px;
        margin-bottom: 4px;
    }}

    .banner-notas-tag {{
        background: #0077ed;
        color: #ffffff;
        font-weight: 900;
        font-size: 10px !important;
        letter-spacing: 1.2px;
        padding: 4px 10px;
        border-radius: 10px;
        text-transform: uppercase;
        white-space: nowrap;
    }}

    .banner-notas-text {{
        color: #ffffff;
        font-size: 18px !important;
        font-weight: 900 !important;
        line-height: 1.2;
        letter-spacing: 0.6px;
        text-transform: uppercase !important;
        flex: 1 !important;
        width: 100% !important;
        word-break: break-word;
    }}

    .full-screen-celebracion {{
        background: linear-gradient(180deg, #1e1b18 0%, #0b0f19 100%);
        border: 1px solid rgba(255, 149, 0, 0.3);
        border-radius: 20px;
        box-shadow: 0 0 30px rgba(255, 149, 0, 0.25);
        padding: 24px 16px 16px 16px;
        text-align: center;
        margin: 6px 0 12px 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }}

    .header-logo-container {{
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 4px; width: 100%; padding: 0 2px; flex-wrap: nowrap; gap: 6px;
    }}
    
    .header-left-group {{ display: flex; align-items: center; gap: 10px; flex-wrap: nowrap; }}
    .header-logo-img {{ height: 38px !important; width: auto; object-fit: contain; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.4)); display: block !important; }}

    .header-title {{
        color: #ffffff !important; 
        font-weight: 900 !important; 
        font-size: 19px !important;
        line-height: 1.1; 
        letter-spacing: 0.8px; 
        margin: 0; 
        padding: 0; 
        white-space: nowrap;
        text-transform: uppercase;
        text-shadow: 0 2px 10px rgba(255, 255, 255, 0.25);
    }}

    .sub-brand-line {{ display: flex; align-items: center; gap: 6px; font-size: 9px; color: #9ca3af; font-weight: 700; letter-spacing: 0.8px; }}
    .sync-text-inline {{ color: #38bdf8; font-weight: 700; }}
    .clocks-group {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}

    .header-clock {{
        background: #151c2c; border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 4px 10px;
        color: #ffffff !important; font-size: 14px !important; font-weight: 800 !important;
        letter-spacing: 0.8px; display: flex; align-items: center; gap: 6px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3); white-space: nowrap;
    }}

    .status-dot {{
        height: 7px; width: 7px; background-color: #34c759; border-radius: 50%; display: inline-block;
        box-shadow: 0 0 6px #34c759; animation: pulseDot 2s infinite;
    }}

    @keyframes pulseDot {{ 0% {{ opacity: 0.4; }} 50% {{ opacity: 1; }} 100% {{ opacity: 0.4; }} }}

    @keyframes pulseGlow {{
        0% {{ box-shadow: 0 0 5px rgba(0, 119, 237, 0.4); border-color: #0077ed; }}
        50% {{ box-shadow: 0 0 15px rgba(0, 119, 237, 0.8); border-color: #3b82f6; }}
        100% {{ box-shadow: 0 0 5px rgba(0, 119, 237, 0.4); border-color: #0077ed; }}
    }}

    .anim-pulso-nuevo {{ animation: pulseGlow 1.2s infinite ease-in-out !important; }}

    .txt-incremento {{
        display: inline-block; background-color: rgba(0, 119, 237, 0.25); color: #60a5fa;
        font-size: 13px !important; font-weight: 800 !important; padding: 1px 6px;
        border-radius: 6px; margin-left: 4px; border: 1px solid rgba(0, 119, 237, 0.4); vertical-align: middle;
    }}

    .metrics-row {{
        display: flex; justify-content: space-around; align-items: center;
        background: #111827; border-radius: 14px; padding: 8px 12px 10px 12px;
        margin-bottom: 8px; border: 1px solid rgba(255,255,255,0.06); position: relative; overflow: hidden;
        box-shadow: 0 3px 10px rgba(0,0,0,0.3);
    }}

    .progress-bar-bg {{ position: absolute; bottom: 0; left: 0; right: 0; height: 3px; background: #1f2937; }}
    .progress-bar-fill {{
        height: 100%; background: linear-gradient(90deg, #ff9500 0%, #ffcc00 100%);
        box-shadow: 0 0 6px rgba(255, 149, 0, 0.6); transition: width 0.5s ease-in-out;
        border-radius: 0 2px 2px 0;
    }}

    .metric-inline {{
        display: flex; align-items: center; gap: 6px; font-size: 11px !important;
        font-weight: 700 !important; color: #9ca3af; letter-spacing: 0.4px; text-transform: uppercase;
    }}

    .metric-inline .val {{ font-size: 14px !important; font-weight: 800 !important; color: #f87171; }}
    .pct-avance {{ font-size: 10px !important; font-weight: 800 !important; color: #9ca3af !important; letter-spacing: 0.6px; text-transform: uppercase; }}

    .divider-completados {{
        display: flex; align-items: center; text-align: center; color: #34c759;
        font-size: 9px; font-weight: 800; letter-spacing: 1.5px; margin: 12px 0 8px 0;
    }}

    .divider-completados::before, .divider-completados::after {{ content: ''; flex: 1; border-bottom: 1px solid #34c759; opacity: 0.25; }}
    .divider-completados span {{ padding: 0 8px; background-color: #0b0f19; }}

    .footer-sutil {{
        position: fixed; bottom: 0; left: 0; right: 0; background: #070a10; border-top: 1px solid rgba(255,255,255,0.06); padding: 3px 10px; text-align: center; font-size: 9px !important; font-weight: 800 !important; color: #6b7280 !important; z-index: 999;
    }}

    .footer-sutil span {{ color: #34c759 !important; font-weight: 900 !important; }}

    .card-master-container {{
        border-radius: 14px;
        padding: 10px 12px;
        margin-bottom: 4px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.35);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 76px;
        backdrop-filter: blur(10px);
    }}

    .card-content-top {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
    }}

    .card-master-pendiente {{ background: #dc2626 !important; border: 1px solid rgba(239, 68, 68, 0.4) !important; color: #ffffff !important; }}
    .card-master-asignado {{ background: #ea580c !important; border: 1px solid rgba(251, 146, 60, 0.8) !important; color: #ffffff !important; box-shadow: 0 0 16px rgba(234, 88, 12, 0.5) !important; }}
    .card-master-urgente {{ background: #b91c1c !important; border: 2px solid #fbbf24 !important; color: #ffffff !important; box-shadow: 0 0 16px rgba(251, 191, 36, 0.4) !important; }}
    
    .card-master-completado {{ background: #047857 !important; border: 1px solid rgba(16, 185, 129, 0.4) !important; color: #ffffff !important; opacity: 0.75; }}
    .card-master-completado .card-master-title,
    .card-master-completado .card-master-num {{
        text-decoration: line-through !important;
        text-decoration-thickness: 2px !important;
        text-decoration-color: rgba(255, 255, 255, 0.8) !important;
    }}

    .card-master-reciente {{ background: #1d4ed8 !important; border: 1px solid rgba(96, 165, 250, 0.4) !important; color: #ffffff !important; }}

    .card-master-title {{
        font-size: 15px !important;
        font-weight: 800 !important;
        text-transform: uppercase !important;
        line-height: 1.15 !important;
        flex: 1;
        padding-right: 6px;
    }}

    .card-master-num {{
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 38px !important;
        font-weight: 900 !important;
        line-height: 1 !important;
        text-align: center;
        min-width: 56px;
    }}

    .colab-asignado-txt {{
        font-size: 12px !important;
        font-weight: 900 !important;
        color: #ffffff !important;
        margin-top: 5px;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        border-top: 1px solid rgba(255, 255, 255, 0.25);
        padding-top: 4px;
    }}

    /* BOTONERAS DE ACCIÓN EN TARJETAS */
    div[data-testid="stHorizontalBlock"]:has(button[key^="tarjeta_btn_"]) {{
        gap: 4px !important;
        margin-bottom: 6px !important;
    }}

    div[data-testid="stElementContainer"]:has(button[key^="tarjeta_btn_"]) button,
    div[data-testid="stButton"] button {{
        background-color: #151c2c !important;
        background: #151c2c !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 10px !important;
        font-weight: 800 !important;
        font-size: 10px !important;
        letter-spacing: 0.8px !important;
        text-transform: uppercase !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.25) !important;
        height: 34px !important;
        min-height: 34px !important;
    }}

    div[data-testid="stElementContainer"]:has(button[key^="tarjeta_btn_"]) button:hover,
    div[data-testid="stButton"] button:hover {{
        background-color: #1e293b !important;
        background: #1e293b !important;
        color: #60a5fa !important;
        border-color: #3b82f6 !important;
    }}

    button:focus {{
        outline: 3px solid #38bdf8 !important;
        outline-offset: 2px !important;
    }}

    @media (max-width: 768px) {{
        .block-container {{ padding-left: 2px !important; padding-right: 2px !important; }}
        div[data-testid="column"] {{ width: 100% !important; flex: 1 1 100% !important; margin-bottom: 2px !important; }}
        .header-logo-container {{ flex-direction: row !important; justify-content: space-between !important; align-items: center !important; padding: 0 2px !important; }}
        .header-logo-img {{ height: 34px !important; display: block !important; }}
        .header-title {{ font-size: 14px !important; }}
        .card-master-title {{ font-size: 14px !important; }}
        .card-master-num {{ font-size: 34px !important; }}
        .card-master-container {{ min-height: 64px !important; padding: 8px 10px !important; border-radius: 12px !important; }}
    }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# SCRIPT JS: WAKE LOCK + LIMPIEZA UI
# ==========================================
ocultar_marca_js = """
<script>
async function iniciarUtilidades() {
    if ('wakeLock' in navigator) {
        try {
            let wakeLock = await navigator.wakeLock.request('screen');
            document.addEventListener('visibilitychange', async () => {
                if (wakeLock !== null && document.visibilityState === 'visible') {
                    wakeLock = await navigator.wakeLock.request('screen');
                }
            });
        } catch (err) {}
    }

    document.documentElement.style.colorScheme = 'dark';

    function limpiarUI() {
        const elementosAEliminar = document.querySelectorAll('footer, #MainMenu, header, [data-testid="stDecoration"], [data-testid="stStatusWidget"], .stAppDeployButton');
        elementosAEliminar.forEach(el => el.remove());
        
        document.querySelectorAll('*').forEach(el => {
            const txt = el.innerText || "";
            if (txt.includes("Made with Streamlit") || txt.includes("Streamlit")) {
                if (el.tagName === 'FOOTER' || el.tagName === 'DIV' && el.style.position === 'fixed') {
                    el.remove();
                }
            }
        });
    }
    
    setInterval(limpiarUI, 1000);
    limpiarUI();
}
iniciarUtilidades();
</script>
"""
components.html(ocultar_marca_js, height=0, width=0)

# ==========================================
# 4. CONSULTA A LA API DE LOYVERSE
# ==========================================
@st.cache_data(ttl=10, show_spinner=False)
def obtener_recibos_hoy_cached(created_at_min_str):
    url = "https://api.loyverse.com/v1.0/receipts"
    params = {"created_at_min": created_at_min_str, "limit": 250}
    todos_los_recibos = []

    try:
        while True:
            response = requests.get(url, headers=HEADERS_LOYVERSE, params=params, timeout=4)
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

def obtener_recibos_hoy():
    created_at_min = estado_global["hora_corte_utc"].strftime("%Y-%m-%dT%H:%M:%SZ")
    return obtener_recibos_hoy_cached(created_at_min)

# ==========================================
# 5. TABLERO DE PEDIDOS EN TIEMPO REAL
# ==========================================
def renderizar_tablero():
    recibos = obtener_recibos_hoy()
    conteo_productos = {}
    infinitos_activos = set()
    urgentes_activos = set()
    ultima_hora_loyverse_utc = None

    if recibos:
        for recibo in recibos:
            created_at_str = recibo.get("receipt_date") or recibo.get("created_at")
            if created_at_str:
                try:
                    dt_recibo = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    if ultima_hora_loyverse_utc is None or dt_recibo > ultima_hora_loyverse_utc:
                        ultima_hora_loyverse_utc = dt_recibo
                except Exception:
                    pass

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

    # FUSIONAR PRODUCTOS MANUALES
    for prod_manual, datos in estado_global["productos_manuales_global"].items():
        if isinstance(datos, dict):
            cant_manual = datos.get("cantidad", 1)
            es_infinito = datos.get("infinito", False)
            es_urgente = datos.get("urgente", False)
        else:
            cant_manual = datos
            es_infinito = False
            es_urgente = False

        if es_infinito:
            conteo_productos[prod_manual] = 1  
            infinitos_activos.add(prod_manual)
        else:
            conteo_productos[prod_manual] = conteo_productos.get(prod_manual, 0) + cant_manual

        if es_urgente:
            urgentes_activos.add(prod_manual)

    tz_mexico = zoneinfo.ZoneInfo("America/Mexico_City")
    if ultima_hora_loyverse_utc:
        hora_sync_loyverse = ultima_hora_loyverse_utc.astimezone(tz_mexico).strftime("%H:%M:%S")
    else:
        hora_sync_loyverse = "SIN RECIBOS"

    for prod, cant_total in conteo_productos.items():
        if prod in estado_global["completados"] and prod not in infinitos_activos:
            cant_marcada = estado_global["cantidades_al_completar"].get(prod, cant_total)
            if cant_total > cant_marcada:
                estado_global["completados"].remove(prod)
                estado_global["cantidades_al_completar"].pop(prod, None)

    if "tiempos_actualizacion" not in st.session_state:
        st.session_state.tiempos_actualizacion = {}

    if "popups_nuevos" not in st.session_state:
        st.session_state.popups_nuevos = {}

    if "reproducido_modal_audio" not in st.session_state:
        st.session_state.reproducido_modal_audio = False

    if "indice_nota_carrusel" not in st.session_state:
        st.session_state.indice_nota_carrusel = 0

    if "desglosar_notas" not in st.session_state:
        st.session_state.desglosar_notas = False

    if "num_campos_colab" not in st.session_state:
        st.session_state.num_campos_colab = max(6, len(estado_global["colaboradores"]))

    ahora_utc = datetime.now(timezone.utc)
    ahora_mexico = datetime.now(tz_mexico)
    hora_mexico_12h = ahora_mexico.strftime("%I:%M:%S %p")

    # CÁLCULO DE PENDIENTES
    piezas_totales = sum([1 if p in infinitos_activos else c for p, c in conteo_productos.items()])
    piezas_pendientes = 0
    
    for prod, cant_total in conteo_productos.items():
        if prod in infinitos_activos:
            if prod not in estado_global["completados"]:
                piezas_pendientes += 1
        else:
            if prod in estado_global["completados"]:
                cant_marcada = estado_global["cantidades_al_completar"].get(prod, cant_total)
                piezas_pendientes += max(0, cant_total - cant_marcada)
            else:
                cant_marcada = estado_global["cantidades_al_completar"].get(prod, 0)
                piezas_pendientes += (cant_total - cant_marcada)

    if "ultimo_conteo" not in st.session_state:
        st.session_state.ultimo_conteo = conteo_productos.copy()
    else:
        nuevo_pedido_detectado = False
        for prod, cant in conteo_productos.items():
            if prod in infinitos_activos:
                continue
            cant_anterior = st.session_state.ultimo_conteo.get(prod, 0)
            if cant > cant_anterior:
                diferencia = cant - cant_anterior
                nuevo_pedido_detectado = True
                st.session_state.tiempos_actualizacion[prod] = ahora_utc
                st.session_state.popups_nuevos[prod] = {
                    "incremento": diferencia,
                    "hora": ahora_utc
                }

        if nuevo_pedido_detectado:
            reproducir_sonido_notificacion()
            estado_global["descartar_celebracion"] = False
            st.session_state.reproducido_modal_audio = False

        st.session_state.ultimo_conteo = conteo_productos.copy()

    # ==========================================
    # BARRA LATERAL (DRAWER) PARA CONFIGURACIÓN
    # ==========================================
    with st.sidebar:
        st.markdown("### PANEL DE AJUSTES Y CONFIGURACIÓN")
        st.markdown("---")
        
        st.markdown("#### Notas del Tablero")
        with st.form("form_notas_tablero", clear_on_submit=False):
            n1 = st.text_input("Nota 1", value=estado_global["notas_tablero"][0], placeholder="EJ. ETIQUETAR CHURRITOS")
            n2 = st.text_input("Nota 2", value=estado_global["notas_tablero"][1], placeholder="EJ. PRIORIDAD FRIMEX")
            n3 = st.text_input("Nota 3", value=estado_global["notas_tablero"][2], placeholder="EJ. LIMPIAR ÁREA")
            
            col_n1, col_n2 = st.columns(2)
            with col_n1:
                btn_guardar_notas = st.form_submit_button("Guardar", use_container_width=True)
            with col_n2:
                btn_limpiar_notas = st.form_submit_button("Limpiar", use_container_width=True)

            if btn_guardar_notas:
                nuevas_notas = [n1.strip().upper(), n2.strip().upper(), n3.strip().upper()]
                estado_global["notas_tablero"] = nuevas_notas
                st.session_state.indice_nota_carrusel = 0
                reproducir_sonido_nota()
                st.toast("Notas actualizadas")
                st.rerun()

            if btn_limpiar_notas:
                estado_global["notas_tablero"] = ["", "", ""]
                st.session_state.indice_nota_carrusel = 0
                reproducir_sonido_nota()
                st.toast("Notas eliminadas")
                st.rerun()

        st.markdown("---")
        st.markdown("#### Colaboradores")
        with st.form("form_colaboradores", clear_on_submit=False):
            colab_inputs = []
            for idx_c in range(st.session_state.num_campos_colab):
                nombre_actual = estado_global["colaboradores"][idx_c] if idx_c < len(estado_global["colaboradores"]) else ""
                c_in = st.text_input(f"Colaborador {idx_c + 1}", value=nombre_actual, key=f"input_colab_{idx_c}")
                colab_inputs.append(c_in)
            
            col_cf1, col_cf2 = st.columns(2)
            with col_cf1:
                btn_guardar_colabs = st.form_submit_button("Guardar", use_container_width=True)
            with col_cf2:
                btn_mas_colab = st.form_submit_button("Agregar más", use_container_width=True)

            if btn_mas_colab:
                st.session_state.num_campos_colab += 2
                st.rerun()

            if btn_guardar_colabs:
                estado_global["colaboradores"] = [c.strip().upper() for c in colab_inputs if c.strip()]
                st.toast("Colaboradores actualizados")
                st.rerun()

        st.markdown("---")
        st.markdown("#### Agregar Productos Manuales")
        with st.form("form_agregar_manual", clear_on_submit=True):
            nombre_manual = st.text_input("Nombre del producto")
            col_chk1, col_chk2 = st.columns(2)
            with col_chk1:
                es_infinito_nuevo = st.checkbox("Infinito (Inf)")
            with col_chk2:
                es_urgente_nuevo = st.checkbox("Urgente")
            cantidad_manual = st.number_input("Cantidad", min_value=1, value=1, step=1)
            submit_manual = st.form_submit_button("Agregar producto")
            
            if submit_manual and nombre_manual.strip():
                prod_key = nombre_manual.strip().upper()
                estado_global["productos_manuales_global"][prod_key] = {
                    "cantidad": int(cantidad_manual),
                    "infinito": es_infinito_nuevo,
                    "urgente": es_urgente_nuevo
                }
                st.toast(f"Agregado: {prod_key}")
                st.rerun()

        if estado_global["productos_manuales_global"]:
            st.markdown("---")
            st.markdown("#### Modificar Manuales")
            for p_nombre, p_datos in list(estado_global["productos_manuales_global"].items()):
                p_cant = p_datos.get("cantidad", 1) if isinstance(p_datos, dict) else p_datos
                p_inf = p_datos.get("infinito", False) if isinstance(p_datos, dict) else False
                p_urg = p_datos.get("urgente", False) if isinstance(p_datos, dict) else False
                
                st.markdown(f"**{p_nombre}** ({'Urgente | ' if p_urg else ''}{'Inf' if p_inf else p_cant})")
                
                with st.expander(f"Editar {p_nombre}"):
                    with st.form(key=f"form_edit_{p_nombre}"):
                        nuevo_urg_val = st.checkbox("Urgente", value=p_urg, key=f"urg_{p_nombre}")
                        nuevo_inf_val = st.checkbox("Infinito (Inf)", value=p_inf, key=f"inf_{p_nombre}")
                        nueva_cant_val = st.number_input("Cantidad", min_value=1, value=p_cant, step=1, key=f"cant_{p_nombre}")
                        
                        col_e1, col_e2 = st.columns(2)
                        with col_e1:
                            btn_aceptar_edit = st.form_submit_button("Guardar")
                        with col_e2:
                            btn_borrar_item = st.form_submit_button("Borrar")

                        if btn_aceptar_edit:
                            estado_global["productos_manuales_global"][p_nombre] = {
                                "cantidad": int(nueva_cant_val),
                                "infinito": nuevo_inf_val,
                                "urgente": nuevo_urg_val
                            }
                            st.toast(f"Actualizado: {p_nombre}")
                            st.rerun()

                        if btn_borrar_item:
                            estado_global["productos_manuales_global"].pop(p_nombre, None)
                            estado_global["completados"].discard(p_nombre)
                            estado_global["cantidades_al_completar"].pop(p_nombre, None)
                            estado_global["asignaciones_productos"].pop(p_nombre, None)
                            st.toast(f"Borrado: {p_nombre}")
                            st.rerun()

        st.markdown("---")
        if st.button("Limpiar Tablero (Barrera)", use_container_width=True):
            borrar_todo()
            st.rerun()
        if st.button("Restaurar Respaldo", use_container_width=True):
            restaurar_estado()
            st.rerun()

    # ==========================================
    # ENCABEZADO PRINCIPAL
    # ==========================================
    col_hdr_left, col_hdr_right = st.columns([0.70, 0.30])
    
    with col_hdr_left:
        st.markdown(f"""
            <div class="header-logo-container">
                <div class="header-left-group">
                    <img src="{LOGO_URL}" class="header-logo-img" alt="Logo Mostacho">
                    <div>
                        <h1 class="header-title">TABLA DE PRODUCCIÓN</h1>
                        <div class="sub-brand-line">
                            <span>MOSTACHO BOTANAS</span>
                            <span class="sync-text-inline">| SYNC: {hora_sync_loyverse}</span>
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col_hdr_right:
        notas_filtradas_header = [(idx + 1, txt) for idx, txt in enumerate(estado_global["notas_tablero"]) if txt.strip()]
        total_notas_h = len(notas_filtradas_header)

        def alternar_desglose_h():
            st.session_state.desglosar_notas = not st.session_state.desglosar_notas

        if total_notas_h > 0:
            subcol1, subcol2 = st.columns([0.8, 0.2])
            with subcol1:
                st.markdown(f"""
                    <div style="background: #151c2c; border: 1px solid rgba(0,119,237,0.3); border-radius: 10px; padding: 6px 10px; color: #fff; font-size: 11px; font-weight: 800; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                        {notas_filtradas_header[0][1]}
                    </div>
                """, unsafe_allow_html=True)
            with subcol2:
                if total_notas_h > 1:
                    if st.session_state.get("desglosar_notas", False):
                        st.button("▲", key="btn_toggle_colapsar_header", on_click=alternar_desglose_h, use_container_width=True)
                    else:
                        st.button(f"▼ ({total_notas_h})", key="btn_toggle_ver_header", on_click=alternar_desglose_h, use_container_width=True)

    # RENDERIZAR NOTAS ACTIVAS DESGLOSADAS SI APLICA
    notas_filtradas = [(idx + 1, txt) for idx, txt in enumerate(estado_global["notas_tablero"]) if txt.strip()]
    if notas_filtradas and st.session_state.get("desglosar_notas", False):
        for num_nota, nota_txt in notas_filtradas:
            st.markdown(f"""
                <div class="banner-notas-container">
                    <div class="banner-notas-tag">NOTA {num_nota}</div>
                    <div class="banner-notas-text">{nota_txt.upper()}</div>
                </div>
            """, unsafe_allow_html=True)

    for prod, info in list(st.session_state.popups_nuevos.items()):
        if (ahora_utc - info["hora"]).total_seconds() >= 30:
            st.session_state.popups_nuevos.pop(prod, None)

    piezas_completadas = max(0, piezas_totales - piezas_pendientes)
    pct_progreso = int((piezas_completadas / piezas_totales * 100)) if piezas_totales > 0 else 100

    # MÉTRICAS
    st.markdown(f"""
        <div class="metrics-row">
            <div class="metric-inline">
                <span>Tickets:</span>
                <span class="val" style="color: #38bdf8;">{len(recibos)}</span>
            </div>
            <div class="metric-inline">
                <span>Pendientes:</span>
                <span class="val" style="color: {'#34c759' if piezas_pendientes == 0 else '#f87171'};">{piezas_pendientes}</span>
            </div>
            <div class="pct-avance">{pct_progreso}% COMPLETADO</div>
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" style="width: {pct_progreso}%;"></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # VISTA DE CELEBRACIÓN
    if conteo_productos and piezas_pendientes == 0 and not estado_global["descartar_celebracion"]:
        if not st.session_state.reproducido_modal_audio:
            reproducir_sonido_celebracion()
            st.session_state.reproducido_modal_audio = True

        st.markdown(f"""
            <div class="full-screen-celebracion">
                <img src="{LOGO_URL}" class="img-celebracion-logo" style="height: 75px; width: auto; filter: drop-shadow(0 3px 12px rgba(255, 149, 0, 0.6));" alt="Logo">
                <h2 style="color: #ff9500; font-weight: 800; font-size: 22px; text-transform: uppercase; margin-bottom: 6px;">PRODUCCIÓN FINALIZADA</h2>
                <p style="color: #9ca3af; font-weight: 700; font-size: 13px; margin-bottom: 12px;">Se han completado todos los pedidos pendientes.</p>
            </div>
        """, unsafe_allow_html=True)

        if st.button("REVISAR PENDIENTES", use_container_width=True, type="primary", key="btn_pantalla_completa_cerrar"):
            estado_global["descartar_celebracion"] = True
            st.rerun()

    # RENDERIZADO DE TARJETAS MAESTRAS EN 4 COLUMNAS
    else:
        if conteo_productos:
            activos = []
            completados = []

            for prod, cant_total in conteo_productos.items():
                if prod in estado_global["completados"]:
                    completados.append((prod, cant_total))
                else:
                    activos.append((prod, cant_total))

            def clave_ordenamiento(item):
                producto, cant_total = item
                es_urgente = producto in urgentes_activos
                es_infinito = producto in infinitos_activos
                ultima_upd = st.session_state.tiempos_actualizacion.get(producto)
                es_reciente = bool(ultima_upd and (ahora_utc - ultima_upd).total_seconds() < 120 and not es_infinito)
                
                if es_urgente:
                    prioridad = 0
                elif es_reciente:
                    prioridad = 1
                else:
                    prioridad = 2
                    
                return (prioridad, -cant_total)

            activos.sort(key=clave_ordenamiento)
            completados.sort(key=lambda x: x[1], reverse=True)

            def renderizar_lista_productos(lista):
                for i in range(0, len(lista), 4):
                    grupo = lista[i:i+4]
                    cols = st.columns(4)

                    for idx, (producto, cant_total) in enumerate(grupo):
                        with cols[idx]:
                            es_completado = producto in estado_global["completados"]
                            es_infinito = producto in infinitos_activos
                            es_urgente = producto in urgentes_activos
                            colab_asignado = estado_global["asignaciones_productos"].get(producto)

                            if es_infinito:
                                valor_mostrar = "∞"
                            else:
                                cant_base = estado_global["cantidades_al_completar"].get(producto, 0)
                                cant_mostrar = cant_total if es_completado else (cant_total - cant_base)
                                valor_mostrar = str(cant_mostrar)

                            ultima_upd = st.session_state.tiempos_actualizacion.get(producto)
                            es_reciente = False
                            if ultima_upd and (ahora_utc - ultima_upd).total_seconds() < 120 and not es_completado and not es_infinito:
                                es_reciente = True

                            # ESTILOS Y COLORES DE TARJETA
                            if es_urgente and not es_completado:
                                clase_css = "card-master-urgente"
                                texto_estado = "TERMINAR"
                                html_flama = '🔥 '
                            elif colab_asignado and not es_completado:
                                clase_css = "card-master-asignado"
                                texto_estado = "TERMINAR"
                                html_flama = ''
                            elif es_reciente:
                                clase_css = "card-master-reciente anim-pulso-nuevo"
                                texto_estado = "TERMINAR"
                                html_flama = ''
                            elif es_completado:
                                clase_css = "card-master-completado"
                                texto_estado = "PENDIENTE"
                                html_flama = ''
                            else:
                                clase_css = "card-master-pendiente"
                                texto_estado = "TERMINAR"
                                html_flama = ''

                            info_popup = st.session_state.popups_nuevos.get(producto)
                            html_incremento = ""
                            if info_popup and not es_completado and not es_infinito:
                                inc = info_popup["incremento"]
                                html_incremento = f'<span class="txt-incremento">+{inc}</span>'

                            html_badge_colab = f'<div class="colab-asignado-txt">{colab_asignado}</div>' if colab_asignado else ''

                            # TARJETA PRINCIPAL
                            st.markdown(f"""
                                <div class="card-master-container {clase_css}">
                                    <div class="card-content-top">
                                        <div class="card-master-title">{html_flama}{producto} {html_incremento}</div>
                                        <div class="card-master-num">{valor_mostrar}</div>
                                    </div>
                                    {html_badge_colab}
                                </div>
                            """, unsafe_allow_html=True)

                            # SELECCIÓN DIRECTA DE COLABORADOR (UN SOLO TOQUE) Y TERMINAR
                            col_btn_1, col_btn_2 = st.columns(2)
                            
                            with col_btn_1:
                                lista_colabs = ["NINGUNO"] + estado_global["colaboradores"]
                                index_actual = 0
                                if colab_asignado and colab_asignado in lista_colabs:
                                    index_actual = lista_colabs.index(colab_asignado)

                                colab_seleccionado = st.selectbox(
                                    f"Asignar {producto}",
                                    options=lista_colabs,
                                    index=index_actual,
                                    key=f"select_asignar_{producto}",
                                    label_visibility="collapsed"
                                )

                                # Asignación inmediata al cambiar la selección en el selectbox
                                if colab_seleccionado != (colab_asignado if colab_asignado else "NINGUNO"):
                                    asignar_colaborador(producto, colab_seleccionado)
                                    st.rerun()

                            with col_btn_2:
                                st.button(
                                    texto_estado, 
                                    key=f"tarjeta_btn_{producto}", 
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

    # FOOTER SUTIL
    st.markdown(f"""
        <div class="footer-sutil">
            PROCESADAS HOY: <span>{piezas_completadas}</span> DE <span>{piezas_totales}</span> PIEZAS
        </div>
    """, unsafe_allow_html=True)

renderizar_tablero()