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
    page_title="Tablero Mostacho", 
    page_icon="logo.png" if os.path.exists("logo.png") else "⚡",
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
# INYECCIÓN DE METADATOS PARA COMPARTIR ENLACE (OG)
# ==========================================
st.markdown(f"""
    <head>
        <meta property="og:title" content="Tablero Mostacho - Producción en Vivo">
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
        "notas_tablero": [],          # Notas ilimitadas
        "productos_manuales_global": {},  
        "colaboradores": ["COLABORADOR 1", "COLABORADOR 2", "COLABORADOR 3", "COLABORADOR 4", "COLABORADOR 5", "COLABORADOR 6"],
        "asignaciones_productos": {}, # {producto: nombre_colaborador}
        "urgentes_activos": set(),    # Productos marcados como urgentes
        "tickets_completados_items": set(), # IDs únicos de items de tickets marcados como listos
        "titulos_personalizados_tickets": {}, # {ticket_id: custom_name}
        "vista_actual": "TABLERO",    # "TABLERO", "TICKETS" o "AJUSTES"
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
        "urgentes_activos": estado_global["urgentes_activos"].copy(),
        "tickets_completados_items": estado_global["tickets_completados_items"].copy(),
        "titulos_personalizados_tickets": estado_global["titulos_personalizados_tickets"].copy(),
        "hora_corte_utc": estado_global["hora_corte_utc"]
    }
    estado_global["hora_corte_utc"] = datetime.now(timezone.utc)
    estado_global["completados"].clear()
    estado_global["cantidades_al_completar"].clear()
    estado_global["productos_manuales_global"].clear()
    estado_global["asignaciones_productos"].clear()
    estado_global["urgentes_activos"].clear()
    estado_global["tickets_completados_items"].clear()
    estado_global["titulos_personalizados_tickets"].clear()
    estado_global["notas_tablero"].clear()
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
        estado_global["urgentes_activos"] = estado_global["respaldo"]["urgentes_activos"].copy()
        estado_global["tickets_completados_items"] = estado_global["respaldo"]["tickets_completados_items"].copy()
        estado_global["titulos_personalizados_tickets"] = estado_global["respaldo"]["titulos_personalizados_tickets"].copy()
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

def alternar_urgente(producto):
    if producto in estado_global["urgentes_activos"]:
        estado_global["urgentes_activos"].remove(producto)
        st.toast(f"Urgente retirado de {producto}")
    else:
        estado_global["urgentes_activos"].add(producto)
        st.toast(f"¡{producto} marcado como URGENTE!", icon="🔥")

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
# 3. ESTILOS CSS, TRANSICIÓN DE NOTAS Y AUTO-REFRESH
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
        padding-bottom: 3.5rem !important;
        padding-left: 0.3rem !important; 
        padding-right: 0.3rem !important;
        max-width: 100% !important;
    }}

    @keyframes fadeInOut {{
        0% {{ opacity: 0; transform: translateY(4px); }}
        10% {{ opacity: 1; transform: translateY(0); }}
        90% {{ opacity: 1; transform: translateY(0); }}
        100% {{ opacity: 0; transform: translateY(-4px); }}
    }}

    .banner-notas-container {{
        background: linear-gradient(135deg, #182232 0%, #111827 50%, #0077ed 200%);
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
        margin-bottom: 6px;
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

    .banner-nota-item {{
        display: none;
        color: #ffffff;
        font-size: 18px !important;
        font-weight: 900 !important;
        line-height: 1.2;
        letter-spacing: 0.6px;
        text-transform: uppercase !important;
        flex: 1 !important;
        width: 100% !important;
        word-break: break-word;
        animation: fadeInOut 10s infinite;
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

    .header-clock-large {{
        background: #151c2c; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 8px 16px;
        color: #ffffff !important; font-size: 18px !important; font-weight: 900 !important;
        letter-spacing: 1px; display: flex; align-items: center; gap: 8px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.35); white-space: nowrap;
    }}

    .status-dot {{
        height: 9px; width: 9px; background-color: #34c759; border-radius: 50%; display: inline-block;
        box-shadow: 0 0 8px #34c759; animation: pulseDot 2s infinite;
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
        margin-bottom: 6px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.35);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 70px;
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
        font-size: 11px !important;
        font-weight: 900 !important;
        color: #ffffff !important;
        margin-top: 4px;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        border-top: 1px solid rgba(255, 255, 255, 0.25);
        padding-top: 3px;
    }}

    button:focus, button:active, button:focus-visible {{
        outline: none !important;
        box-shadow: none !important;
    }}

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
        height: 36px !important;
        min-height: 36px !important;
    }}

    div[data-testid="stButton"] button:hover {{
        background-color: #1e293b !important;
        background: #1e293b !important;
        color: #60a5fa !important;
        border-color: #3b82f6 !important;
    }}

    @media (max-width: 768px) {{
        .ocultar-en-movil {{ display: none !important; }}
        .block-container {{ padding-left: 2px !important; padding-right: 2px !important; }}
        div[data-testid="column"] {{ width: 100% !important; flex: 1 1 100% !important; margin-bottom: 2px !important; }}
        .header-logo-container {{ flex-direction: row !important; justify-content: space-between !important; align-items: center !important; padding: 0 2px !important; }}
        .header-logo-img {{ height: 34px !important; display: block !important; }}
        .header-title {{ font-size: 14px !important; }}
        .card-master-title {{ font-size: 14px !important; }}
        .card-master-num {{ font-size: 34px !important; }}
        .card-master-container {{ min-height: 60px !important; padding: 8px 10px !important; border-radius: 12px !important; }}
    }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# SCRIPT JS: AUTO-REFRESH DE SINCRONIZACIÓN CADA 3 SEGUNDOS + ROTACIÓN DE NOTAS CADA 10s
# ==========================================
utilidades_js = """
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
    }
    
    setInterval(limpiarUI, 1000);
    limpiarUI();

    // Rotación automática de notas en el banner cada 10 segundos
    let notaActual = 0;
    setInterval(function() {
        const notas = document.querySelectorAll('.banner-nota-item');
        if (notas.length > 0) {
            notas.forEach(n => n.style.display = 'none');
            notaActual = (notaActual + 1) % notas.length;
            notas[notaActual].style.display = 'block';
        }
    }, 10000);

    // Activar primera nota si existe
    setTimeout(function() {
        const notas = document.querySelectorAll('.banner-nota-item');
        if (notas.length > 0) {
            notas[0].style.display = 'block';
        }
    }, 200);
}
iniciarUtilidades();

// Auto-sync automático en tiempo real recargando fragmentos clave cada 3 segundos sin perder foco
setInterval(function() {
    if (typeof window !== 'undefined' && !window.location.search.includes('sync=off')) {
        const trigger = document.querySelector('[data-testid="stStatusWidget"]');
        // Disparador silencioso Streamlit
        window.dispatchEvent(new Event('resize'));
    }
}, 3000);
</script>
"""
components.html(utilidades_js, height=0, width=0)

# ==========================================
# 4. CONSULTA A LA API DE LOYVERSE
# ==========================================
@st.cache_data(ttl=2, show_spinner=False)
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
# 5. APLICACIÓN PRINCIPAL
# ==========================================
def renderizar_aplicacion():
    recibos = obtener_recibos_hoy()
    conteo_productos = {}
    infinitos_activos = set()
    urgentes_activos = estado_global["urgentes_activos"]
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
                
                # EN EL TABLERO AGRUPAMOS CON VARIANTES PARA MANTENER ORDEN
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
    # ENCABEZADO PRINCIPAL
    # ==========================================
    col_hdr_left, col_hdr_mid, col_hdr_right = st.columns([0.42, 0.18, 0.40])
    
    with col_hdr_left:
        st.markdown(f"""
            <div class="header-logo-container">
                <div class="header-left-group">
                    <img src="{LOGO_URL}" class="header-logo-img" alt="Logo Mostacho">
                    <div>
                        <h1 class="header-title">Tablero Mostacho</h1>
                        <div class="sub-brand-line">
                            <span>MOSTACHO BOTANAS</span>
                            <span class="sync-text-inline">| SYNC: {hora_sync_loyverse}</span>
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col_hdr_mid:
        st.markdown(f"""
            <div class="ocultar-en-movil" style="display: flex; align-items: center; justify-content: center; height: 100%;">
                <div class="header-clock-large" title="Hora local de México">
                    <span class="status-dot"></span> <span>{hora_mexico_12h}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col_hdr_right:
        c_nav1, c_nav2, c_nav3 = st.columns(3)
        with c_nav1:
            if st.button("TABLERO", use_container_width=True, type="primary" if estado_global["vista_actual"] == "TABLERO" else "secondary"):
                estado_global["vista_actual"] = "TABLERO"
                st.rerun()
        with c_nav2:
            if st.button("TICKETS", use_container_width=True, type="primary" if estado_global["vista_actual"] == "TICKETS" else "secondary"):
                estado_global["vista_actual"] = "TICKETS"
                st.rerun()
        with c_nav3:
            if st.button("AJUSTES", use_container_width=True, type="primary" if estado_global["vista_actual"] == "AJUSTES" else "secondary"):
                estado_global["vista_actual"] = "AJUSTES"
                st.rerun()

    # BANNER DE NOTAS CON TRANSICIÓN (CARRUSEL DE 10 SEGUNDOS)
    notas_filtradas = [txt for txt in estado_global["notas_tablero"] if txt.strip()]
    if notas_filtradas:
        html_notas_items = ""
        for idx_n, nota_txt in enumerate(notas_filtradas):
            html_notas_items += f'<div class="banner-nota-item">NOTA {idx_n + 1}: {nota_txt.upper()}</div>'

        st.markdown(f"""
            <div class="banner-notas-container">
                <div class="banner-notas-tag">AVISOS</div>
                {html_notas_items}
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

    # ==========================================
    # SECCIÓN 1: GESTIÓN DE TICKETS INDEPENDIENTES (VARIANTES DESGLOSADAS)
    # ==========================================
    if estado_global["vista_actual"] == "TICKETS":
        st.markdown("### GESTIÓN DE TICKETS INDIVIDUALES")
        st.markdown("<p style='color: #9ca3af; font-size: 12px;'>Visualiza los tickets con sus productos y variantes exactas tal cual se registran en Loyverse.</p>", unsafe_allow_html=True)
        
        if recibos:
            tickets_pendientes_lista = []
            tickets_completados_lista = []

            for idx_recibo, recibo in enumerate(recibos):
                ticket_id = recibo.get("id", str(idx_recibo))
                line_items = recibo.get("line_items", [])
                
                todos_listos = True
                if line_items:
                    for idx_item, item in enumerate(line_items):
                        nombre = item.get("item_name", "Producto")
                        variante = item.get("variant_name")
                        var_str = f" ({variante})" if variante and variante != "Default" else ""
                        item_key_uid = f"{ticket_id}_{idx_item}_{nombre}{var_str}"
                        if item_key_uid not in estado_global["tickets_completados_items"]:
                            todos_listos = False
                            break
                else:
                    todos_listos = False

                if todos_listos and len(line_items) > 0:
                    tickets_completados_lista.append((idx_recibo, recibo, ticket_id))
                else:
                    tickets_pendientes_lista.append((idx_recibo, recibo, ticket_id))

            def renderizar_bloque_ticket(idx_recibo, recibo, ticket_id, completado=False):
                receipt_number = recibo.get("receipt_number", f"#{idx_recibo + 1}")
                created_at_str = recibo.get("receipt_date") or recibo.get("created_at", "")
                
                customer_name = recibo.get("customer_name") or recibo.get("customer", {}).get("name")
                note_recibo = recibo.get("note") or recibo.get("comment") or ""
                
                titulo_custom = estado_global["titulos_personalizados_tickets"].get(ticket_id)
                titulo_principal = titulo_custom if titulo_custom else (customer_name.upper() if customer_name else f"TICKET {receipt_number}")
                sub_detalle = f"TICKET {receipt_number}" if customer_name or titulo_custom else ""
                
                try:
                    dt_ticket = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                    hora_ticket = dt_ticket.astimezone(tz_mexico).strftime("%I:%M:%S %p")
                except:
                    hora_ticket = "---"

                line_items = recibo.get("line_items", [])
                bg_color = "#0f172a" if completado else "#111827"
                border_color = "rgba(52, 199, 89, 0.4)" if completado else "rgba(255,255,255,0.08)"
                
                # CONTENEDOR SEGURO CONTRA TEXTO PLANO
                with st.container():
                    st.markdown(f"""
                        <div style="background: {bg_color}; border: 1px solid {border_color}; border-radius: 12px; padding: 14px; margin-bottom: 12px; opacity: {'0.85' if completado else '1'};">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 8px;">
                                <div>
                                    <div style="font-weight: 900; color: {'#34c759' if completado else '#ffffff'}; font-size: 17px; letter-spacing: 0.5px; text-transform: uppercase;">{titulo_principal}</div>
                                    <div style="font-weight: 700; color: #38bdf8; font-size: 11px; margin-top: 2px;">{sub_detalle}</div>
                                </div>
                                <span style="font-size: 11px; color: #9ca3af; font-weight: 700; background: #151c2c; padding: 3px 8px; border-radius: 6px;">{hora_ticket}</span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                    if note_recibo:
                        st.markdown(f"<div style='font-style: italic; color: #fbbf24; font-size: 12px; margin-bottom: 10px;'>💬 Nota: {note_recibo}</div>", unsafe_allow_html=True)

                    # EXPANDER CON CIERRE AUTOMÁTICO AL GUARDAR Y TEXTO SIMPLIFICADO
                    with st.expander(f"Editar nombre del ticket #{receipt_number}"):
                        with st.form(key=f"form_title_{ticket_id}"):
                            nuevo_nombre_ticket = st.text_input("Nombre o alias personalizado:", value=titulo_custom if titulo_custom else (customer_name if customer_name else ""))
                            btn_guardar_nombre = st.form_submit_button("GUARDAR", use_container_width=True)

                            if btn_guardar_nombre:
                                if nuevo_nombre_ticket.strip():
                                    estado_global["titulos_personalizados_tickets"][ticket_id] = nuevo_nombre_ticket.strip().upper()
                                else:
                                    estado_global["titulos_personalizados_tickets"].pop(ticket_id, None)
                                st.toast("Nombre de ticket actualizado")
                                st.rerun()

                    for idx_item, item in enumerate(line_items):
                        nombre = item.get("item_name", "Producto")
                        cantidad = item.get("quantity", 0)
                        variante = item.get("variant_name")
                        var_str = f" ({variante})" if variante and variante != "Default" else ""
                        nombre_completo = f"{nombre}{var_str}"

                        cant_num = int(cantidad) if float(cantidad).is_integer() else cantidad
                        item_key_uid = f"{ticket_id}_{idx_item}_{nombre_completo}"
                        
                        esta_listo = item_key_uid in estado_global["tickets_completados_items"]
                        es_urgente_prod = nombre_completo in estado_global["urgentes_activos"]

                        col_t1, col_t2 = st.columns([0.76, 0.24])
                        
                        with col_t1:
                            # SOLO EMOJIS, NEGRITA Y TAMAÑO AMPLIADO
                            btn_text = f"✅ **{cant_num}x {nombre_completo}**" if esta_listo else f"⬜ **{cant_num}x {nombre_completo}**"
                            if st.button(btn_text, key=f"btn_toggle_item_{item_key_uid}", use_container_width=True):
                                if esta_listo:
                                    estado_global["tickets_completados_items"].discard(item_key_uid)
                                else:
                                    estado_global["tickets_completados_items"].add(item_key_uid)
                                st.rerun()

                        with col_t2:
                            urg_label = "🔥 URGENTE" if es_urgente_prod else "⚡ NORMAL"
                            if st.button(urg_label, key=f"btn_urg_{item_key_uid}", use_container_width=True):
                                alternar_urgente(nombre_completo)
                                st.rerun()

                    st.markdown("<hr style='border: none; border-top: 1px dashed rgba(255,255,255,0.12); margin: 14px 0;'>", unsafe_allow_html=True)

            if tickets_pendientes_lista:
                st.markdown("#### ⏳ Tickets Pendientes de Producción")
                for idx_recibo, recibo, ticket_id in tickets_pendientes_lista:
                    renderizar_bloque_ticket(idx_recibo, recibo, ticket_id, completado=False)

            if tickets_completados_lista:
                st.markdown("""
                    <div class="divider-completados" style="margin: 24px 0 12px 0;">
                        <span>TICKETS COMPLETADOS Y CONCRETADOS</span>
                    </div>
                """, unsafe_allow_html=True)
                for idx_recibo, recibo, ticket_id in tickets_completados_lista:
                    renderizar_bloque_ticket(idx_recibo, recibo, ticket_id, completado=True)

            st.markdown("#### Agregar Nota al Tablero Principal")
            with st.form("form_nota_rapida_tickets", clear_on_submit=True):
                nueva_nota_txt = st.text_input("Escribe una nota rápida para el banner superior:")
                btn_enviar_nota_ticket = st.form_submit_button("Publicar Nota en Tablero", use_container_width=True)

                if btn_enviar_nota_ticket and nueva_nota_txt.strip():
                    estado_global["notas_tablero"].append(nueva_nota_txt.strip().upper())
                    reproducir_sonido_nota()
                    st.toast("¡Nota publicada en el tablero con éxito!")
                    st.rerun()

        else:
            st.info("No hay tickets disponibles para mostrar en este periodo.")

    # ==========================================
    # SECCIÓN 2: PANEL DE AJUSTES (NOTAS ILIMITADAS)
    # ==========================================
    elif estado_global["vista_actual"] == "AJUSTES":
        st.markdown("### PANEL DE AJUSTES Y CONFIGURACIÓN")
        st.markdown("---")

        # 1. TOP DEL DÍA
        st.markdown("#### 🏆 Top del día")
        conteo_colab = {colab: 0 for colab in estado_global["colaboradores"]}
        for prod, colab_asig in estado_global["asignaciones_productos"].items():
            if colab_asig in conteo_colab:
                cant_prod = conteo_productos.get(prod, 1)
                conteo_colab[colab_asig] += (1 if prod in infinitos_activos else cant_prod)

        ranking_ordenado = sorted(conteo_colab.items(), key=lambda x: x[1], reverse=True)
        for pos, (nombre_colab, total_piezas) in enumerate(ranking_ordenado):
            medalla = "🥇" if pos == 0 else ("🥈" if pos == 1 else ("🥉" if pos == 2 else f"#{pos+1}"))
            st.markdown(f"<div style='font-size: 13px; font-weight: 800; padding: 6px 10px; background: #111827; border-radius: 8px; margin-bottom: 6px; color: #e2e8f0; display: flex; justify-content: space-between;'><span>{medalla} {nombre_colab}</span><span style='color: #38bdf8;'>{total_piezas} pzas</span></div>", unsafe_allow_html=True)

        st.markdown("---")

        # 2. NOTAS DEL TABLERO (ILIMITADAS)
        st.markdown("#### Notas del Tablero (Ilimitadas)")
        with st.form("form_notas_tablero", clear_on_submit=True):
            nueva_nota_ajustes = st.text_input("Agregar nueva nota al carrusel:")
            btn_add_nota = st.form_submit_button("Agregar Nota", use_container_width=True)

            if btn_add_nota and nueva_nota_ajustes.strip():
                estado_global["notas_tablero"].append(nueva_nota_ajustes.strip().upper())
                reproducir_sonido_nota()
                st.toast("Nota agregada")
                st.rerun()

        if estado_global["notas_tablero"]:
            st.markdown("<p style='font-size: 12px; color: #9ca3af;'>Notas actuales en rotación:</p>", unsafe_allow_html=True)
            for idx_n, nota_act in enumerate(estado_global["notas_tablero"]):
                col_n1, col_n2 = st.columns([0.80, 0.20])
                with col_n1:
                    st.markdown(f"<div style='font-size: 12px; padding: 6px; background: #151c2c; border-radius: 6px; margin-bottom: 4px;'>{idx_n + 1}. {nota_act}</div>", unsafe_allow_html=True)
                with col_n2:
                    if st.button("Borrar", key=f"del_nota_{idx_n}", use_container_width=True):
                        estado_global["notas_tablero"].pop(idx_n)
                        st.toast("Nota eliminada")
                        st.rerun()

        st.markdown("---")

        # 3. AGREGAR PRODUCTOS MANUALES
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
                if es_urgente_nuevo:
                    estado_global["urgentes_activos"].add(prod_key)
                st.toast(f"Agregado: {prod_key}")
                st.rerun()

        if estado_global["productos_manuales_global"]:
            st.markdown("#### Modificar Manuales")
            for p_nombre, p_datos in list(estado_global["productos_manuales_global"].items()):
                p_cant = p_datos.get("cantidad", 1) if isinstance(p_datos, dict) else p_datos
                p_inf = p_datos.get("infinito", False) if isinstance(p_datos, dict) else False
                p_urg = p_nombre in estado_global["urgentes_activos"]
                
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
                            if nuevo_urg_val:
                                estado_global["urgentes_activos"].add(p_nombre)
                            else:
                                estado_global["urgentes_activos"].discard(p_nombre)
                            st.toast(f"Actualizado: {p_nombre}")
                            st.rerun()

                        if btn_borrar_item:
                            estado_global["productos_manuales_global"].pop(p_nombre, None)
                            estado_global["completados"].discard(p_nombre)
                            estado_global["cantidades_al_completar"].pop(p_nombre, None)
                            estado_global["asignaciones_productos"].pop(p_nombre, None)
                            estado_global["urgentes_activos"].discard(p_nombre)
                            st.toast(f"Borrado: {p_nombre}")
                            st.rerun()

        st.markdown("---")

        # EDICIÓN DE ASIGNACIONES
        st.markdown("#### 👥 Edición y Asignación de Colaboradores por Producto")
        if conteo_productos:
            lista_colabs = ["NINGUNO"] + estado_global["colaboradores"]
            for prod_asignable in sorted(conteo_productos.keys()):
                colab_actual = estado_global["asignaciones_productos"].get(prod_asignable, "NINGUNO")
                idx_asig = lista_colabs.index(colab_actual) if colab_actual in lista_colabs else 0
                
                nuevo_asig = st.selectbox(f"Asignar a: {prod_asignable}", options=lista_colabs, index=idx_asig, key=f"ajustes_asig_{prod_asignable}")
                if nuevo_asig != colab_actual:
                    asignar_colaborador(prod_asignable, nuevo_asig)
                    st.rerun()
        else:
            st.info("No hay productos activos para asignar.")

        st.markdown("---")

        # 4. CONFIGURACIÓN DE COLABORADORES
        st.markdown("#### Configuración de Colaboradores")
        with st.form("form_colaboradores", clear_on_submit=False):
            colab_inputs = []
            for idx_c in range(st.session_state.num_campos_colab):
                nombre_actual = estado_global["colaboradores"][idx_c] if idx_c < len(estado_global["colaboradores"]) else ""
                c_in = st.text_input(f"Colaborador {idx_c + 1}", value=nombre_actual, key=f"input_colab_{idx_c}")
                colab_inputs.append(c_in)
            
            col_cf1, col_cf2 = st.columns(2)
            with col_cf1:
                btn_guardar_colabs = st.form_submit_button("Guardar Colaboradores", use_container_width=True)
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

        # 5. BOTÓN DE LIMPIAR TABLERO
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            if st.button("Limpiar tablero", use_container_width=True):
                borrar_todo()
                st.rerun()
        with col_res2:
            if st.button("Restaurar Respaldo", use_container_width=True):
                restaurar_estado()
                st.rerun()

    # ==========================================
    # SECCIÓN 3: TABLA DE PRODUCCIÓN PRINCIPAL (VISTA POR DEFECTO)
    # ==========================================
    else:
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

                                # BOTÓN DE TERMINAR + SELECTOR DE ASIGNACIÓN EN LA MISMA FILA
                                col_f1, col_f2 = st.columns([0.45, 0.55])
                                with col_f1:
                                    st.button(
                                        texto_estado, 
                                        key=f"tarjeta_btn_{producto}", 
                                        on_click=alternar_estado, 
                                        args=(producto, cant_total),
                                        use_container_width=True
                                    )

                                with col_f2:
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

                                    if colab_seleccionado != (colab_asignado if colab_asignado else "NINGUNO"):
                                        asignar_colaborador(producto, colab_seleccionado)
                                        st.rerun()

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

renderizar_aplicacion()