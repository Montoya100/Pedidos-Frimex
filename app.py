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
    st.toast("Tablero limpiado", icon="ℹ️")

def restaurar_estado():
    if estado_global["respaldo"]:
        estado_global["completados"] = estado_global["respaldo"]["completados"].copy()
        estado_global["cantidades_al_completar"] = estado_global["respaldo"]["cantidades_al_completar"].copy()
        estado_global["hora_corte_utc"] = estado_global["respaldo"]["hora_corte_utc"]
        estado_global["respaldo"] = None
        st.toast("Tablero restaurado", icon="✅")
    else:
        st.toast("Sin respaldo previo", icon="⚠️")

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
# 3. ESTILOS CSS ESTÁTICOS Y ANIMACIONES
# ==========================================
st.markdown(f"""
    <style>
    /* ELIMINAR PARPADEO Y OPACIDAD DURANTE REFRESCADOS */
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

    /* ENCABEZADO MINIMALISTA */
    .header-logo-container {{
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 8px; width: 100%; padding: 0 4px;
    }}
    
    .header-left-group {{
        display: flex; align-items: center; gap: 14px;
    }}

    .header-logo-img {{ height: 58px !important; width: auto; object-fit: contain; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5)); }}

    .header-title {{
        color: #ffffff; font-weight: 900; font-size: 22px !important;
        line-height: 1.1; letter-spacing: 1.2px; margin: 0; padding: 0; white-space: nowrap;
        text-transform: uppercase;
    }}

    /* DUAL CLOCK CONTAINER */
    .clocks-group {{
        display: flex;
        align-items: center;
        gap: 12px;
    }}

    /* RELOJ SUTIL DE REFRESCADO DE TABLA (GRIS) */
    .reloj-tabla-sutil {{
        font-size: 11px !important;
        font-weight: 700 !important;
        color: #64748b !important;
        letter-spacing: 0.8px;
        background: #12151e;
        padding: 5px 10px;
        border-radius: 6px;
        border: 1px solid #1e293b;
        display: flex;
        align-items: center;
        gap: 6px;
    }}

    /* RELOJ TIEMPO REAL MÉXICO (DESTACADO) */
    .header-clock {{
        background: #161922;
        border: 1px solid #2a2e39;
        border-radius: 8px;
        padding: 6px 14px;
        color: #38bdf8;
        font-size: 18px !important;
        font-weight: 800 !important;
        letter-spacing: 1.2px;
        display: flex; align-items: center; gap: 8px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    }}

    .status-dot {{
        height: 8px; width: 8px;
        background-color: #10b981;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 8px #10b981;
        animation: pulseDot 2s infinite;
    }}

    @keyframes pulseDot {{
        0% {{ opacity: 0.4; }}
        50% {{ opacity: 1; }}
        100% {{ opacity: 0.4; }}
    }}

    /* ANIMACIÓN DE PULSO DE LUZ NEÓN EN CAMBIOS NUEVOS */
    @keyframes pulseGlow {{
        0% {{
            box-shadow: 0 0 4px rgba(56, 189, 248, 0.4);
            border-color: #38bdf8;
        }}
        50% {{
            box-shadow: 0 0 18px rgba(56, 189, 248, 0.9);
            border-color: #60a5fa;
        }}
        100% {{
            box-shadow: 0 0 4px rgba(56, 189, 248, 0.4);
            border-color: #38bdf8;
        }}
    }}

    .anim-pulso-nuevo {{
        animation: pulseGlow 1.2s infinite ease-in-out !important;
    }}

    /* ETIQUETA EN LÍNEA DE UNIDADES NUEVAS */
    .txt-incremento {{
        display: inline-block;
        background-color: #1e3a8a;
        color: #93c5fd;
        font-size: 18px !important;
        font-weight: 900 !important;
        padding: 2px 8px;
        border-radius: 6px;
        margin-left: 6px;
        border: 1px solid #3b82f6;
    }}

    /* MODAL POP-UP FLOTANTE DE CELEBRACIÓN MINIMALISTA */
    .celebration-overlay {{
        position: fixed;
        top: 0; left: 0; width: 100vw; height: 100vh;
        background: rgba(14, 17, 23, 0.85);
        backdrop-filter: blur(10px);
        z-index: 99999;
        display: flex; align-items: center; justify-content: center;
    }}

    .celebration-card {{
        background: linear-gradient(180deg, #121824 0%, #0d121c 100%);
        border: 1px solid #10b981;
        border-radius: 16px;
        padding: 40px;
        text-align: center;
        max-width: 520px; width: 90%;
        box-shadow: 0 0 40px rgba(16, 185, 129, 0.25);
        color: #ffffff;
    }}

    .celebration-title {{
        font-size: 28px !important;
        font-weight: 900 !important;
        margin-bottom: 12px;
        color: #34d399;
        letter-spacing: 1px;
    }}

    .celebration-sub {{
        font-size: 16px !important;
        font-weight: 700 !important;
        color: #94a3b8;
        line-height: 1.5;
    }}

    /* MÉTRICAS EN LÍNEA CON BARRA DE PROGRESO EN NARANJA NEÓN SUAVE */
    .metrics-row {{
        display: flex; justify-content: space-around; align-items: center;
        background: #161922;
        border-radius: 8px; padding: 10px 16px 14px 16px;
        margin-bottom: 12px; border: 1px solid #2a2e39;
        position: relative;
        overflow: hidden;
    }}

    .progress-bar-bg {{
        position: absolute;
        bottom: 0; left: 0; right: 0;
        height: 4px;
        background: #1f2430;
    }}

    .progress-bar-fill {{
        height: 100%;
        background: linear-gradient(90deg, #fb923c 0%, #f97316 100%);
        box-shadow: 0 0 8px rgba(249, 115, 22, 0.6);
        transition: width 0.5s ease-in-out;
    }}

    .metric-inline {{ 
        display: flex; 
        align-items: center; 
        gap: 10px; 
        font-size: 15px !important; 
        font-weight: 800 !important; 
        color: #94a3b8; 
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }}

    .metric-inline .val {{ 
        font-size: 22px !important; 
        font-weight: 900 !important; 
        color: #f87171; 
    }}

    /* INDICADOR DE PORCENTAJE SUTIL */
    .pct-avance {{
        font-size: 11px !important;
        font-weight: 700 !important;
        color: #94a3b8 !important;
        letter-spacing: 0.8px;
        background: transparent;
        padding: 2px 6px;
        opacity: 0.8;
    }}

    /* SEPARADOR DE SECCIÓN COMPLETADOS */
    .divider-completados {{
        display: flex;
        align-items: center;
        text-align: center;
        color: #10b981;
        font-size: 11px;
        font-weight: 900;
        letter-spacing: 2px;
        margin: 16px 0 10px 0;
    }}

    .divider-completados::before, .divider-completados::after {{
        content: '';
        flex: 1;
        border-bottom: 1px solid #10b981;
        opacity: 0.3;
    }}

    .divider-completados span {{
        padding: 0 12px;
        background-color: #0e1117;
    }}

    /* TARJETA DE TEXTO DEL PRODUCTO CON EFECTO HOVER */
    .card-box-img {{
        border-radius: 10px;
        height: 100px !important;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 0 12px;
        font-size: 30px !important;
        font-weight: 900 !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        white-space: normal;
        word-wrap: break-word;
        line-height: 1.15;
        margin-bottom: 6px;
        letter-spacing: 0.5px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}

    .card-box-img:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }}

    /* CAJA DEL NÚMERO MASIVO GIGANTE CON EFECTO HOVER */
    .num-box-masivo {{
        border-radius: 10px;
        height: 100px !important;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 68px !important;
        font-weight: 900 !important;
        line-height: 1 !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.35);
        margin-bottom: 6px;
        user-select: none;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}

    .num-box-masivo:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    }}

    .num-box-pendiente {{ 
        background: #dc2626 !important; 
        color: #ffffff !important; 
        border: 1px solid #ef4444 !important;
    }}
    .num-box-completado {{ 
        background: #059669 !important; 
        color: #ffffff !important; 
        opacity: 0.75; 
        border: 1px solid #10b981 !important;
    }}
    .num-box-reciente {{ 
        background: #2563eb !important; 
        color: #ffffff !important;
        border: 1px solid #60a5fa !important;
    }}

    /* TARJETA PENDIENTE (ROJO) */
    .card-pendiente {{
        background: #ef4444 !important;
        color: #ffffff !important;
        border: 1px solid #f87171 !important;
    }}

    /* TARJETA COMPLETADA (VERDE) */
    .card-completado {{
        background: #10b981 !important;
        color: #ffffff !important;
        border: 1px solid #34d399 !important;
        opacity: 0.75;
    }}

    /* ESTADO TEMPORAL AZUL (NUEVO PRODUCTO) */
    .card-nueva-orden {{
        background: #2563eb !important;
        color: #ffffff !important;
        border: 2px solid #60a5fa !important;
    }}

    /* BOTÓN TRANSPARENTE SUPERPUESTO */
    div[data-testid="stElementContainer"]:has(button