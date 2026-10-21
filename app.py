import base64
import os
import requests
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timezone, timedelta
import zoneinfo

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="MOSTACHO BOTANAS - ONE UI", 
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
# 2. ESTADO GLOBAL COMPARTIDO Y PERSISTENTE
# ==========================================
@st.cache_resource
def obtener_estado_global():
    return {
        "completados": set(),
        "cantidades_al_completar": {},
        "hora_corte_utc": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0),
        "respaldo": None,
        "descartar_celebracion": False
    }

estado_global = obtener_estado_global()

# Asegurar persistencia absoluta en session_state para Notas y Productos Manuales
if "notas_tablero_state" not in st.session_state:
    st.session_state.notas_tablero_state = ["", "", ""]

if "productos_manuales_state" not in st.session_state:
    st.session_state.productos_manuales_state = {}

def borrar_todo():
    estado_global["respaldo"] = {
        "completados": estado_global["completados"].copy(),
        "cantidades_al_completar": estado_global["cantidades_al_completar"].copy(),
        "productos_manuales": {k: v.copy() for k, v in st.session_state.productos_manuales_state.items()},
        "notas_tablero": st.session_state.notas_tablero_state.copy(),
        "hora_corte_utc": estado_global["hora_corte_utc"]
    }
    estado_global["hora_corte_utc"] = datetime.now(timezone.utc)
    estado_global["completados"].clear()
    estado_global["cantidades_al_completar"].clear()
    st.session_state.productos_manuales_state.clear()
    st.session_state.notas_tablero_state = ["", "", ""]
    estado_global["descartar_celebracion"] = False
    st.toast("Tablero limpiado correctamente", icon="ℹ️")

def restaurar_estado():
    if estado_global["respaldo"]:
        estado_global["completados"] = estado_global["respaldo"]["completados"].copy()
        estado_global["cantidades_al_completar"] = estado_global["respaldo"]["cantidades_al_completar"].copy()
        st.session_state.productos_manuales_state = {k: v.copy() for k, v in estado_global["respaldo"]["productos_manuales"].items()}
        st.session_state.notas_tablero_state = estado_global["respaldo"]["notas_tablero"].copy()
        estado_global["hora_corte_utc"] = estado_global["respaldo"]["hora_corte_utc"]
        estado_global["respaldo"] = None
        estado_global["descartar_celebracion"] = False
        st.toast("Tablero restaurado correctamente", icon="✅")
    else:
        st.toast("Sin respaldo previo disponible", icon="⚠️")

def alternar_estado(producto, cantidad_actual):
    if producto in estado_global["completados"]:
        estado_global["completados"].remove(producto)
        estado_global["cantidades_al_completar"].pop(producto, None)
    else:
        estado_global["completados"].add(producto)
        estado_global["cantidades_al_completar"][producto] = cantidad_actual

    estado_global["descartar_celebracion"] = False

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
# 3. ESTILOS CSS - ESTILO ONE UI DE SAMSUNG
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

    .stApp {{ background-color: #0b0f19 !important; font-family: 'Plus Jakarta Sans', sans-serif !important; }}
    
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
        padding-top: 0.6rem !important; 
        padding-bottom: 4rem !important;
        padding-left: 0.5rem !important; 
        padding-right: 0.5rem !important;
        max-width: 100% !important;
    }}

    @keyframes deslizarDegradado {{
        0% {{ opacity: 0; transform: translateY(-10px); background-position: 200% 0; }}
        100% {{ opacity: 1; transform: translateY(0); background-position: 0 0; }}
    }}

    /* BANNER DE NOTAS ESTILIZADO ONE UI */
    .banner-notas-container {{
        background: linear-gradient(135deg, #182232 0%, #111827 50%, #0077ed 200%);
        background-size: 200% 100%;
        animation: deslizarDegradado 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        border: 1px solid rgba(0, 119, 237, 0.3);
        border-radius: 22px;
        padding: 14px 20px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        display: flex;
        align-items: center;
        width: 100% !important;
        box-sizing: border-box;
        gap: 14px;
        min-height: 64px;
    }}

    .banner-notas-tag {{
        background: #0077ed;
        color: #ffffff;
        font-weight: 900;
        font-size: 13px !important;
        letter-spacing: 1.5px;
        padding: 8px 14px;
        border-radius: 14px;
        text-transform: uppercase;
        white-space: nowrap;
    }}

    .banner-notas-text {{
        color: #ffffff;
        font-size: 26px !important;
        font-weight: 900 !important;
        line-height: 1.25;
        letter-spacing: 0.8px;
        text-transform: uppercase !important;
        flex: 1 !important;
        width: 100% !important;
        word-break: break-word;
    }}

    /* ESTILO GENERAL PARA LOS BOTONES DE NOTAS LATERALES */
    div[data-testid="stElementContainer"]:has(button[key^="btn_toggle_"]) button {{
        height: 64px !important;
        min-height: 64px !important;
        border-radius: 16px !important;
        background-color: #151c2c !important;
        border: 1px solid rgba(0, 119, 237, 0.4) !important;
        color: #60a5fa !important;
        font-weight: 900 !important;
        font-size: 12px !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.25);
        white-space: nowrap !important;
    }}

    .full-screen-celebracion {{
        background: linear-gradient(180deg, #1e1b18 0%, #0b0f19 100%);
        border: 1px solid rgba(255, 149, 0, 0.3);
        border-radius: 28px;
        box-shadow: 0 0 50px rgba(255, 149, 0, 0.25);
        padding: 40px 24px 28px 24px;
        text-align: center;
        margin: 10px 0 20px 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }}

    @media (min-width: 769px) {{
        .full-screen-celebracion {{
            min-height: 65vh !important;
            padding: 60px 40px !important;
            justify-content: center !important;
        }}
        .img-celebracion-logo {{ height: 140px !important; margin-bottom: 24px !important; }}
        .txt-celebracion-titulo {{ font-size: 40px !important; letter-spacing: 2px !important; margin-bottom: 12px !important; }}
        .txt-celebracion-sub {{ font-size: 18px !important; margin-bottom: 36px !important; }}
        div[data-testid="stElementContainer"]:has(button[key="btn_pantalla_completa_cerrar"]) {{
            max-width: 260px !important;
            margin: 0 auto !important;
        }}
    }}

    .header-logo-container {{
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 12px; width: 100%; padding: 0 4px; flex-wrap: nowrap; gap: 8px;
    }}
    
    .header-left-group {{ display: flex; align-items: center; gap: 14px; flex-wrap: nowrap; }}
    .header-logo-img {{ height: 58px !important; width: auto; object-fit: contain; filter: drop-shadow(0 4px 8px rgba(0,0,0,0.4)); display: block !important; }}

    .header-title {{
        color: #ffffff; font-weight: 800; font-size: 24px !important;
        line-height: 1.1; letter-spacing: 0.8px; margin: 0; padding: 0; white-space: nowrap;
        text-transform: uppercase;
    }}

    .sub-brand-line {{ display: flex; align-items: center; gap: 8px; font-size: 11px; color: #9ca3af; font-weight: 700; letter-spacing: 1px; }}
    .sync-text-inline {{ color: #38bdf8; font-weight: 700; }}
    .clocks-group {{ display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}

    .header-clock {{
        background: #151c2c; border: 1px solid rgba(255,255,255,0.06); border-radius: 16px; padding: 8px 16px;
        color: #ffffff !important; font-size: 20px !important; font-weight: 800 !important;
        letter-spacing: 1px; display: flex; align-items: center; gap: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3); white-space: nowrap;
    }}

    .status-dot {{
        height: 10px; width: 10px; background-color: #34c759; border-radius: 50%; display: inline-block;
        box-shadow: 0 0 10px #34c759; animation: pulseDot 2s infinite;
    }}

    @keyframes pulseDot {{ 0% {{ opacity: 0.4; }} 50% {{ opacity: 1; }} 100% {{ opacity: 0.4; }} }}

    @keyframes pulseGlow {{
        0% {{ box-shadow: 0 0 8px rgba(0, 119, 237, 0.4); border-color: #0077ed; }}
        50% {{ box-shadow: 0 0 22px rgba(0, 119, 237, 0.8); border-color: #3b82f6; }}
        100% {{ box-shadow: 0 0 8px rgba(0, 119, 237, 0.4); border-color: #0077ed; }}
    }}

    .anim-pulso-nuevo {{ animation: pulseGlow 1.2s infinite ease-in-out !important; }}

    .txt-incremento {{
        display: inline-block; background-color: rgba(0, 119, 237, 0.25); color: #60a5fa;
        font-size: 18px !important; font-weight: 800 !important; padding: 2px 10px;
        border-radius: 10px; margin-left: 8px; border: 1px solid rgba(0, 119, 237, 0.4); vertical-align: middle;
    }}

    .metrics-row {{
        display: flex; justify-content: space-around; align-items: center;
        background: #111827; border-radius: 20px; padding: 12px 18px 16px 18px;
        margin-bottom: 16px; border: 1px solid rgba(255,255,255,0.06); position: relative; overflow: hidden;
        box-shadow: 0 6px 16px rgba(0,0,0,0.3);
    }}

    .progress-bar-bg {{ position: absolute; bottom: 0; left: 0; right: 0; height: 5px; background: #1f2937; }}
    .progress-bar-fill {{
        height: 100%; background: linear-gradient(90deg, #ff9500 0%, #ffcc00 100%);
        box-shadow: 0 0 10px rgba(255, 149, 0, 0.6); transition: width 0.5s ease-in-out;
        border-radius: 0 4px 4px 0;
    }}

    .metric-inline {{
        display: flex; align-items: center; gap: 10px; font-size: 14px !important;
        font-weight: 700 !important; color: #9ca3af; letter-spacing: 0.5px; text-transform: uppercase;
    }}

    .metric-inline .val {{ font-size: 20px !important; font-weight: 800 !important; color: #f87171; }}
    .pct-avance {{ font-size: 13px !important; font-weight: 800 !important; color: #9ca3af !important; letter-spacing: 0.8px; text-transform: uppercase; }}

    .divider-completados {{
        display: flex; align-items: center; text-align: center; color: #34c759;
        font-size: 11px; font-weight: 800; letter-spacing: 2px; margin: 20px 0 14px 0;
    }}

    .divider-completados::before, .divider-completados::after {{ content: ''; flex: 1; border-bottom: 1px solid #34c759; opacity: 0.25; }}
    .divider-completados span {{ padding: 0 14px; background-color: #0b0f19; }}

    div[data-testid="stPopover"] button {{
        height: 38px !important; font-size: 12px !important; font-weight: 800 !important; background-color: #151c2c !important; color: #9ca3af !important; border: 1px solid rgba(255,255,255,0.08) !important; border-radius: 12px !important;
    }}

    .footer-sutil {{
        position: fixed; bottom: 0; left: 0; right: 0; background: #070a10; border-top: 1px solid rgba(255,255,255,0.06); padding: 6px 16px; text-align: center; font-size: 11px !important; font-weight: 800 !important; color: #6b7280 !important; z-index: 999;
    }}

    .footer-sutil span {{ color: #34c759 !important; font-weight: 900 !important; }}

    /* TARJETAS MAESTRAS ESTILO ONE UI */
    .card-master-container {{
        border-radius: 24px;
        padding: 18px 20px;
        margin-bottom: 8px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.45);
        display: flex;
        align-items: center;
        justify-content: space-between;
        min-height: 126px;
        backdrop-filter: blur(10px);
    }}

    .card-master-pendiente {{ background: #dc2626 !important; border: 1px solid rgba(239, 68, 68, 0.4) !important; color: #ffffff !important; }}
    
    .card-master-completado {{ background: #047857 !important; border: 1px solid rgba(16, 185, 129, 0.4) !important; color: #ffffff !important; opacity: 0.75; }}
    .card-master-completado .card-master-title,
    .card-master-completado .card-master-num {{
        text-decoration: line-through !important;
        text-decoration-thickness: 4px !important;
        text-decoration-color: rgba(255, 255, 255, 0.8) !important;
    }}

    .card-master-reciente {{ background: #1d4ed8 !important; border: 1px solid rgba(96, 165, 250, 0.4) !important; color: #ffffff !important; }}

    .card-master-title {{
        font-size: 30px !important;
        font-weight: 800 !important;
        text-transform: uppercase !important;
        line-height: 1.15 !important;
        flex: 1;
        padding-right: 12px;
    }}

    .card-master-num {{
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 72px !important;
        font-weight: 900 !important;
        line-height: 1 !important;
        text-align: center;
        min-width: 90px;
    }}

    /* BOTONES TIPO PÍLDORA FLOTANTE PARA PRODUCTOS */
    div[data-testid="stElementContainer"]:has(button[key^="tarjeta_btn_"]) {{ margin-bottom: 16px !important; }}
    
    div[data-testid="stElementContainer"]:has(button[key^="tarjeta_btn_"]) button {{
        height: 44px !important;
        min-height: 44px !important;
        width: 100% !important;
        border-radius: 16px !important;
        background-color: #151c2c !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        color: #f3f4f6 !important;
        font-weight: 800 !important;
        font-size: 13px !important;
        letter-spacing: 1.5px !important;
        text-transform: uppercase !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.25);
    }}

    /* VERSIÓN MÓVIL Y TABLET COMPACTA */
    @media (max-width: 768px) {{
        .block-container {{ padding-left: 6px !important; padding-right: 6px !important; }}
        div[data-testid="column"] {{ width: 100% !important; flex: 1 1 100% !important; margin-bottom: 4px !important; }}
        div[data-testid="stHorizontalBlock"] {{ flex-direction: row !important; width: 100% !important; gap: 6px !important; }}
        .clocks-group {{ display: none !important; }}
        
        .header-logo-container {{
            flex-direction: row !important;
            justify-content: space-between !important;
            align-items: center !important;
            padding: 0 2px !important;
        }}
        .header-logo-img {{
            height: 46px !important;
            display: block !important;
            visibility: visible !important;
        }}
        .header-title {{ font-size: 17px !important; }}
        .sub-brand-line {{ font-size: 10px !important; }}
        .pct-avance {{ font-size: 11px !important; }}

        .full-screen-celebracion {{ padding: 28px 16px 20px 16px !important; }}
        .img-celebracion-logo {{ height: 100px !important; margin-bottom: 16px !important; }}
        .txt-celebracion-titulo {{ font-size: 26px !important; margin-bottom: 8px !important; }}
        .txt-celebracion-sub {{ font-size: 15px !important; margin-bottom: 24px !important; }}
        
        .card-master-title {{ font-size: 21px !important; }}
        .card-master-num {{ font-size: 52px !important; }}
        .card-master-container {{ min-height: 96px !important; padding: 14px 16px !important; border-radius: 20px !important; }}
        .banner-notas-text {{ font-size: 20px !important; }}
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
@st.fragment(run_every=5)
def renderizar_tablero():
    recibos = obtener_recibos_hoy()
    conteo_productos = {}
    infinitos_activos = set()
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

    # FUSIONAR PRODUCTOS MANUALES DESDE SESSION STATE
    for prod_manual, datos in st.session_state.productos_manuales_state.items():
        if isinstance(datos, dict):
            cant_manual = datos.get("cantidad", 1)
            es_infinito = datos.get("infinito", False)
        else:
            cant_manual = datos
            es_infinito = False

        if es_infinito:
            conteo_productos[prod_manual] = 1  
            infinitos_activos.add(prod_manual)
        else:
            conteo_productos[prod_manual] = conteo_productos.get(prod_manual, 0) + cant_manual

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

    # ENCABEZADO
    col_hdr_left, col_hdr_right = st.columns([0.82, 0.18])
    
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
                <div class="clocks-group">
                    <div class="header-clock" title="Hora local de México">
                        <span class="status-dot"></span> <span>{hora_mexico_12h}</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col_hdr_right:
        with st.popover("OPCIONES", use_container_width=True):
            st.markdown("### Notas del Tablero")
            with st.form("form_notas_tablero", clear_on_submit=False):
                n1 = st.text_input("Nota 1", value=st.session_state.notas_tablero_state[0], placeholder="EJ. PONERLE ETIQUETA A 20 CHURRITOS")
                n2 = st.text_input("Nota 2", value=st.session_state.notas_tablero_state[1], placeholder="EJ. PRIORIDAD PEDIDOS FRIMEX")
                n3 = st.text_input("Nota 3", value=st.session_state.notas_tablero_state[2], placeholder="EJ. LIMPIAR ÁREA AL TERMINAR")
                
                col_n1, col_n2 = st.columns(2)
                with col_n1:
                    btn_guardar_notas = st.form_submit_button("Guardar Notas", use_container_width=True)
                with col_n2:
                    btn_limpiar_notas = st.form_submit_button("Limpiar Todas", use_container_width=True)

                if btn_guardar_notas:
                    nuevas_notas = [n1.strip().upper(), n2.strip().upper(), n3.strip().upper()]
                    if nuevas_notas != st.session_state.notas_tablero_state:
                        st.session_state.notas_tablero_state = nuevas_notas
                        st.session_state.indice_nota_carrusel = 0
                        reproducir_sonido_nota()
                        st.toast("Notas actualizadas en el tablero", icon="✅")
                    else:
                        st.toast("Sin cambios en las notas", icon="ℹ️")
                    st.rerun()

                if btn_limpiar_notas:
                    if any(st.session_state.notas_tablero_state):
                        st.session_state.notas_tablero_state = ["", "", ""]
                        st.session_state.indice_nota_carrusel = 0
                        reproducir_sonido_nota()
                        st.toast("Todas las notas fueron eliminadas", icon="ℹ️")
                    st.rerun()

            st.markdown("---")
            st.markdown("### Agregar Producto Manual")
            with st.form("form_agregar_manual", clear_on_submit=True):
                nombre_manual = st.text_input("Nombre del producto")
                es_infinito_nuevo = st.checkbox("Marcar como Infinito (∞ / Hasta terminar)")
                cantidad_manual = st.number_input("Cantidad", min_value=1, value=1, step=1)
                submit_manual = st.form_submit_button("Agregar al tablero")
                
                if submit_manual and nombre_manual.strip():
                    prod_key = nombre_manual.strip().upper()
                    st.session_state.productos_manuales_state[prod_key] = {
                        "cantidad": int(cantidad_manual),
                        "infinito": es_infinito_nuevo
                    }
                    st.toast(f"Agregado: {prod_key}", icon="✅")
                    st.rerun()

            if st.session_state.productos_manuales_state:
                st.markdown("---")
                st.markdown("### Modificar Productos Manuales")
                for p_nombre, p_datos in list(st.session_state.productos_manuales_state.items()):
                    p_cant = p_datos.get("cantidad", 1) if isinstance(p_datos, dict) else p_datos
                    p_inf = p_datos.get("infinito", False) if isinstance(p_datos, dict) else False
                    
                    st.markdown(f"**{p_nombre}** ({'∞' if p_inf else p_cant})")
                    
                    with st.expander(f"Editar {p_nombre}"):
                        with st.form(key=f"form_edit_{p_nombre}"):
                            nuevo_inf_val = st.checkbox("Infinito (∞)", value=p_inf, key=f"inf_{p_nombre}")
                            nueva_cant_val = st.number_input("Cantidad", min_value=1, value=p_cant, step=1, key=f"cant_{p_nombre}")
                            
                            col_e1, col_e2 = st.columns(2)
                            with col_e1:
                                btn_aceptar_edit = st.form_submit_button("Aceptar")
                            with col_e2:
                                btn_borrar_item = st.form_submit_button("Borrar")

                            if btn_aceptar_edit:
                                st.session_state.productos_manuales_state[p_nombre] = {
                                    "cantidad": int(nueva_cant_val),
                                    "infinito": nuevo_inf_val
                                }
                                st.toast(f"Actualizado: {p_nombre}", icon="✅")
                                st.rerun()

                            if btn_borrar_item:
                                st.session_state.productos_manuales_state.pop(p_nombre, None)
                                estado_global["completados"].discard(p_nombre)
                                estado_global["cantidades_al_completar"].pop(p_nombre, None)
                                st.toast(f"Producto borrado: {p_nombre}", icon="ℹ️")
                                st.rerun()

            st.markdown("---")
            st.markdown("### Acciones de Tablero")
            if st.button("Borrar todo", use_container_width=True):
                borrar_todo()
                st.rerun()
            if st.button("Restaurar", use_container_width=True):
                restaurar_estado()
                st.rerun()

    # RENDERIZAR NOTAS ACTIVAS CON UN SOLO BOTÓN DE COLAPSAR LIMPIO Y ÚNICO
    notas_filtradas = [(idx + 1, txt) for idx, txt in enumerate(st.session_state.notas_tablero_state) if txt.strip()]
    
    if notas_filtradas:
        total_notas_validas = len(notas_filtradas)
        
        def alternar_desglose():
            st.session_state.desglosar_notas = not st.session_state.desglosar_notas

        if st.session_state.desglosar_notas or total_notas_validas == 1:
            for i, (num_nota, nota_txt) in enumerate(notas_filtradas):
                # Si hay varias notas, solo ponemos el botón de colapsar en la PRIMERA nota para que no se repita
                col_banner, col_btn = st.columns([0.84, 0.16]) if (total_notas_validas > 1 and i == 0) else (st.columns([1, 0.001]) if total_notas_validas > 1 else (st.columns([1, 0.001])))
                
                with col_banner:
                    st.markdown(f"""
                        <div class="banner-notas-container">
                            <div class="banner-notas-tag">NOTA {num_nota}</div>
                            <div class="banner-notas-text">{nota_txt.upper()}</div>
                        </div>
                    """, unsafe_allow_html=True)
                
                # Renderizamos el botón único de colapsar exclusivamente en la primera columna lateral
                if total_notas_validas > 1 and i == 0:
                    with col_btn:
                        st.button("▲ COLAPSAR", key="btn_toggle_colapsar_unico", on_click=alternar_desglose, use_container_width=True)
                
                st.markdown("<div style='margin-bottom: 6px;'></div>", unsafe_allow_html=True)
        else:
            st.session_state.indice_nota_carrusel = (st.session_state.indice_nota_carrusel + 1) % total_notas_validas
            num_nota_actual, texto_actual = notas_filtradas[st.session_state.indice_nota_carrusel]
            
            col_banner, col_btn = st.columns([0.82, 0.18])
            with col_banner:
                st.markdown(f"""
                    <div class="banner-notas-container">
                        <div class="banner-notas-tag">NOTA {num_nota_actual}/{total_notas_validas}</div>
                        <div class="banner-notas-text">{texto_actual.upper()}</div>
                    </div>
                """, unsafe_allow_html=True)
            with col_btn:
                st.button(f"▼ VER ({total_notas_validas})", key="btn_toggle_ver_todas", on_click=alternar_desglose, use_container_width=True)

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
                <img src="{LOGO_URL}" class="img-celebracion-logo" style="width: auto; filter: drop-shadow(0 6px 20px rgba(255, 149, 0, 0.6));" alt="Logo">
                <h2 class="txt-celebracion-titulo" style="color: #ff9500; font-weight: 800; text-transform: uppercase;">PRODUCCIÓN FINALIZADA</h2>
                <p class="txt-celebracion-sub" style="color: #9ca3af; font-weight: 700;">Se han completado todos los pedidos pendientes.</p>
            </div>
        """, unsafe_allow_html=True)

        if st.button("REVISAR PENDIENTES", use_container_width=True, type="primary", key="btn_pantalla_completa_cerrar"):
            estado_global["descartar_celebracion"] = True
            st.rerun()

    # RENDERIZADO DE TARJETAS MAESTRAS
    else:
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

            def renderizar_lista_productos(lista):
                for i in range(0, len(lista), 3):
                    grupo = lista[i:i+3]
                    cols = st.columns(3)

                    for idx, (producto, cant_total) in enumerate(grupo):
                        with cols[idx]:
                            es_completado = producto in estado_global["completados"]
                            es_infinito = producto in infinitos_activos

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

                            if es_reciente:
                                clase_css = "card-master-reciente anim-pulso-nuevo"
                                texto_estado = "NUEVO"
                            elif es_completado:
                                clase_css = "card-master-completado"
                                texto_estado = "MARCAR COMO PENDIENTE"
                            else:
                                clase_css = "card-master-pendiente"
                                texto_estado = "MARCAR COMO TERMINADO"

                            info_popup = st.session_state.popups_nuevos.get(producto)
                            html_incremento = ""
                            if info_popup and not es_completado and not es_infinito:
                                inc = info_popup["incremento"]
                                html_incremento = f'<span class="txt-incremento">+{inc}</span>'

                            # TARJETA ONE UI
                            st.markdown(f"""
                                <div class="card-master-container {clase_css}">
                                    <div class="card-master-title">{producto} {html_incremento}</div>
                                    <div class="card-master-num">{valor_mostrar}</div>
                                </div>
                            """, unsafe_allow_html=True)

                            # BOTÓN PÍLDORA
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