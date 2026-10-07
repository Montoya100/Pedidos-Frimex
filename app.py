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
    if "cerrar_modal_celebracion" in st.session_state:
        st.session_state.cerrar_modal_celebracion = False
    st.toast("Tablero limpiado", icon="ℹ️")

def restaurar_estado():
    if estado_global["respaldo"]:
        estado_global["completados"] = estado_global["respaldo"]["completados"].copy()
        estado_global["cantidades_al_completar"] = estado_global["respaldo"]["cantidades_al_completar"].copy()
        estado_global["hora_corte_utc"] = estado_global["respaldo"]["hora_corte_utc"]
        estado_global["respaldo"] = None
        if "cerrar_modal_celebracion" in st.session_state:
            st.session_state.cerrar_modal_celebracion = False
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
    
    if "cerrar_modal_celebracion" in st.session_state:
        st.session_state.cerrar_modal_celebracion = False

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
# 3. ESTILOS CSS ESTÁTICOS Y ANIMACIONES
# ==========================================
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@800;900&display=swap');

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

    .stApp {{ background-color: #0b0d13 !important; }}
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    
    .block-container {{
        padding-top: 0.4rem !important; 
        padding-bottom: 2.5rem !important;
        padding-left: 0.2rem !important; 
        padding-right: 0.2rem !important;
        max-width: 100% !important;
    }}

    /* ENCABEZADO RESPONSIVE */
    .header-logo-container {{
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 8px; width: 100%; padding: 0 4px; flex-wrap: wrap; gap: 8px;
    }}
    
    .header-left-group {{
        display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
    }}

    .header-logo-img {{ height: 50px !important; width: auto; object-fit: contain; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5)); }}

    .header-title {{
        color: #ffffff; font-weight: 900; font-size: 20px !important;
        line-height: 1.1; letter-spacing: 1px; margin: 0; padding: 0; white-space: nowrap;
        text-transform: uppercase;
    }}

    /* DUAL CLOCK CONTAINER */
    .clocks-group {{
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
    }}

    /* RELOJ SUTIL DE REFRESCADO DE TABLA (GRIS) */
    .reloj-tabla-sutil {{
        font-size: 11px !important;
        font-weight: 700 !important;
        color: #64748b !important;
        letter-spacing: 0.8px;
        background: #12151e;
        padding: 6px 10px;
        border-radius: 6px;
        border: 1px solid #1e293b;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        white-space: nowrap;
    }}

    /* RELOJ TIEMPO REAL MÉXICO (MÁS GRANDE Y CON NÚMEROS BLANCOS EN ESCRITORIO) */
    .header-clock {{
        background: #161922;
        border: 1px solid #2a2e39;
        border-radius: 8px;
        padding: 6px 14px;
        color: #ffffff !important;
        font-size: 22px !important;
        font-weight: 900 !important;
        letter-spacing: 1.2px;
        display: flex; align-items: center; gap: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.4);
        white-space: nowrap;
    }}

    .status-dot {{
        height: 9px; width: 9px;
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

    /* MODAL FLOTANTE ULTRA OSCURO TRASLÚCIDO EN PANTALLA COMPLETA */
    .custom-modal-overlay {{
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        background-color: rgba(5, 7, 10, 0.96) !important;
        backdrop-filter: blur(18px) !important;
        -webkit-backdrop-filter: blur(18px) !important;
        z-index: 999999 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }}

    .custom-modal-box {{
        background: linear-gradient(180deg, #18131a 0%, #0d0e14 100%) !important;
        border: 2px solid #f97316 !important;
        border-radius: 24px !important;
        box-shadow: 0 0 70px rgba(249, 115, 22, 0.5) !important;
        text-align: center !important;
        max-width: 580px !important;
        width: 88% !important;
        padding: 36px 28px !important;
        margin: auto !important;
    }}

    .modal-logo-img-large {{
        height: 80px !important;
        width: auto;
        margin-bottom: 16px;
        filter: drop-shadow(0 6px 18px rgba(249, 115, 22, 0.5));
    }}

    .celebration-title-orange-large {{
        font-size: 28px !important;
        font-weight: 900 !important;
        margin-bottom: 10px;
        color: #fb923c;
        letter-spacing: 1.5px;
        text-transform: uppercase;
    }}

    .celebration-sub-orange-large {{
        font-size: 16px !important;
        font-weight: 700 !important;
        color: #94a3b8;
        line-height: 1.5;
        margin-bottom: 24px;
    }}

    /* ESTILO DEL BOTÓN DEL MODAL */
    div[data-testid="stElementContainer"]:has(button[key="btn_cerrar_custom_modal"]) button {{
        background-color: #f97316 !important;
        color: #ffffff !important;
        border: 1px solid #fb923c !important;
        border-radius: 12px !important;
        font-weight: 900 !important;
        font-size: 15px !important;
        letter-spacing: 1.5px !important;
        height: 52px !important;
        box-shadow: 0 4px 22px rgba(249, 115, 22, 0.45) !important;
        transition: all 0.2s ease !important;
    }}

    div[data-testid="stElementContainer"]:has(button[key="btn_cerrar_custom_modal"]) button:hover {{
        background-color: #ea580c !important;
        border-color: #fdba74 !important;
        box-shadow: 0 6px 30px rgba(249, 115, 22, 0.7) !important;
        transform: translateY(-2px) !important;
    }}

    /* MÉTRICAS EN LÍNEA CON BARRA DE PROGRESO EN NARANJA NEÓN SUAVE */
    .metrics-row {{
        display: flex; justify-content: space-around; align-items: center;
        background: #141822;
        border-radius: 10px; padding: 10px 16px 14px 16px;
        margin-bottom: 14px; border: 1px solid #232936;
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
        margin: 18px 0 12px 0;
    }}

    .divider-completados::before, .divider-completados::after {{
        content: '';
        flex: 1;
        border-bottom: 1px solid #10b981;
        opacity: 0.3;
    }}

    .divider-completados span {{
        padding: 0 12px;
        background-color: #0b0d13;
    }}

    /* TARJETA DE TEXTO DEL PRODUCTO CON ELEVACIÓN SUTIL */
    .card-box-img {{
        border-radius: 10px;
        height: 100px !important;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 0 12px;
        font-size: 28px !important;
        font-weight: 900 !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.35);
        white-space: normal;
        word-wrap: break-word;
        line-height: 1.15;
        margin-bottom: 6px;
        letter-spacing: 0.5px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}

    .card-box-img:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.5);
    }}

    /* CAJA DEL NÚMERO MASIVO GIGANTE CON TIPOGRAFÍA IMPACTO MONOSPACE */
    .num-box-masivo {{
        border-radius: 10px;
        height: 100px !important;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 66px !important;
        font-weight: 900 !important;
        line-height: 1 !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.4);
        margin-bottom: 6px;
        user-select: none;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        letter-spacing: -2px;
    }}

    .num-box-masivo:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.55);
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
        padding-bottom: 8px !important;
    }}

    /* ETIQUETA EN BOTÓN TRANSPARENTE */
    div[data-testid="stElementContainer"]:has(button[key^="num_btn_"]) button * {{
        font-size: 11px !important;
        font-weight: 900 !important;
        letter-spacing: 1.5px !important;
        text-transform: uppercase !important;
        color: #ffffff !important;
        opacity: 0.95 !important;
        text-shadow: 0 1px 3px rgba(0,0,0,0.6);
    }}

    /* ESTILO BOTÓN DE CONFIGURACIÓN SIN EMOJIS */
    div[data-testid="stPopover"] button {{
        height: 36px !important;
        font-size: 12px !important;
        font-weight: 800 !important;
        background-color: #141822 !important;
        color: #94a3b8 !important;
        border: 1px solid #232936 !important;
        border-radius: 8px !important;
        letter-spacing: 1px;
    }}
    
    div[data-testid="stPopover"] button:hover {{
        border-color: #38bdf8 !important;
        color: #ffffff !important;
    }}

    /* FOOTER SUTIL DE PROCESADAS HOY */
    .footer-sutil {{
        position: fixed;
        bottom: 0; left: 0; right: 0;
        background: #090b10;
        border-top: 1px solid #181d28;
        padding: 5px 16px;
        text-align: center;
        font-size: 11px !important;
        font-weight: 800 !important;
        color: #64748b !important;
        letter-spacing: 1.5px;
        z-index: 999;
    }}

    .footer-sutil span {{
        color: #10b981 !important;
        font-weight: 900 !important;
    }}

    /* REGLAS MÓVILES EXCLUSIVAS (LISTA FLUIDA + RELOJ DE SYNC CENTRADO DE BORDES COMPLETOS) */
    @media (max-width: 768px) {{
        .block-container {{
            padding-left: 6px !important;
            padding-right: 6px !important;
        }}
        
        div[data-testid="column"] {{
            width: 100% !important;
            flex: 1 1 100% !important;
            padding-left: 0px !important;
            padding-right: 0px !important;
            margin-bottom: 4px !important;
        }}
        
        div[data-testid="stHorizontalBlock"] {{
            flex-direction: row !important;
            width: 100% !important;
            gap: 6px !important;
        }}

        /* RELOJ DE SYNC EN MÓVIL: ANCHO COMPLETO Y CENTRADO PERFECTO */
        .clocks-group {{
            width: 100% !important;
            margin-top: 4px !important;
        }}

        .reloj-tabla-sutil {{
            width: 100% !important;
            text-align: center !important;
            justify-content: center !important;
            padding: 8px 12px !important;
        }}

        /* AJUSTAR EL TAMAÑO DEL NOMBRE Y NÚMERO DENTRO DE LA TARJETA EN MÓVIL */
        .card-box-img {{
            font-size: 22px !important;
            height: 90px !important;
        }}
        
        .num-box-masivo {{
            font-size: 50px !important;
            height: 90px !important;
        }}

        div[data-testid="stElementContainer"]:has(button[key^="num_btn_"]) {{
            height: 90px !important;
            margin-top: -96px !important;
        }}

        div[data-testid="stElementContainer"]:has(button[key^="num_btn_"]) button {{
            height: 90px !important;
            min-height: 90px !important;
        }}

        /* OCULTAR EL RELOJ DE 12 HORAS EN MÓVIL */
        .header-clock {{
            display: none !important;
        }}
        
        .header-logo-container {{
            flex-direction: row !important;
            justify-content: space-between !important;
            align-items: center !important;
            padding: 0 4px !important;
        }}
        
        .header-title {{
            font-size: 15px !important;
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

    if "popups_nuevos" not in st.session_state:
        st.session_state.popups_nuevos = {}

    if "cerrar_modal_celebracion" not in st.session_state:
        st.session_state.cerrar_modal_celebracion = False

    if "reproducido_modal_audio" not in st.session_state:
        st.session_state.reproducido_modal_audio = False

    ahora_utc = datetime.now(timezone.utc)
    tz_mexico = zoneinfo.ZoneInfo("America/Mexico_City")
    ahora_mexico = datetime.now(tz_mexico)
    hora_mexico_12h = ahora_mexico.strftime("%I:%M:%S %p")
    hora_sincro_tabla = ahora_mexico.strftime("%H:%M:%S")

    if "ultimo_conteo" not in st.session_state:
        st.session_state.ultimo_conteo = conteo_productos.copy()
    else:
        nuevo_pedido_detectado = False
        for prod, cant in conteo_productos.items():
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
            st.session_state.cerrar_modal_celebracion = False
            st.session_state.reproducido_modal_audio = False

        st.session_state.ultimo_conteo = conteo_productos.copy()

    # ENCABEZADO MINIMALISTA SIN EMOJIS
    col_hdr_left, col_hdr_right = st.columns([0.82, 0.18])
    
    with col_hdr_left:
        st.markdown(f"""
            <div class="header-logo-container">
                <div class="header-left-group">
                    <img src="{LOGO_URL}" class="header-logo-img" alt="Logo">
                    <div>
                        <h1 class="header-title">TABLA DE PRODUCCIÓN</h1>
                        <span style="font-size:11px; color:#64748b; font-weight: 800; letter-spacing: 1px;">MOSTACHO BOTANAS</span>
                    </div>
                </div>
                <div class="clocks-group">
                    <div class="reloj-tabla-sutil" title="Última sincronización de datos">
                        <span>SYNC:</span> <span>{hora_sincro_tabla}</span>
                    </div>
                    <div class="header-clock" title="Hora local de México">
                        <span class="status-dot"></span> <span>{hora_mexico_12h}</span>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col_hdr_right:
        with st.popover("OPCIONES", use_container_width=True):
            st.markdown("### Acciones de Tablero")
            if st.button("Borrar todo", use_container_width=True):
                borrar_todo()
            if st.button("Restaurar", use_container_width=True):
                restaurar_estado()

    # LIMPIEZA DE NOTIFICACIONES EXPIRADAS (> 30 SEG)
    for prod, info in list(st.session_state.popups_nuevos.items()):
        if (ahora_utc - info["hora"]).total_seconds() >= 30:
            st.session_state.popups_nuevos.pop(prod, None)

    # CÁLCULO DE MÉTRICAS Y PROGRESO REAL DE PRODUCCIÓN
    piezas_totales = sum(conteo_productos.values())
    piezas_pendientes = 0
    
    for prod, cant_total in conteo_productos.items():
        if prod in estado_global["completados"]:
            cant_marcada = estado_global["cantidades_al_completar"].get(prod, cant_total)
            piezas_pendientes += max(0, cant_total - cant_marcada)
        else:
            cant_marcada = estado_global["cantidades_al_completar"].get(prod, 0)
            piezas_pendientes += (cant_total - cant_marcada)

    piezas_completadas = max(0, piezas_totales - piezas_pendientes)
    pct_progreso = int((piezas_completadas / piezas_totales * 100)) if piezas_totales > 0 else 100

    # MÉTRICAS DESTACADAS CON BARRA DE PROGRESO EN NARANJA NEÓN SUAVE Y TEXTO SUTIL
    st.markdown(f"""
        <div class="metrics-row">
            <div class="metric-inline">
                <span>Tickets:</span>
                <span class="val" style="color: #38bdf8;">{len(recibos)}</span>
            </div>
            <div class="pct-avance">{pct_progreso}% COMPLETADO</div>
            <div class="metric-inline">
                <span>Pendientes:</span>
                <span class="val" style="color: {'#10b981' if piezas_pendientes == 0 else '#f87171'};">{piezas_pendientes}</span>
            </div>
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" style="width: {pct_progreso}%;"></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # POP-UP NATIVO EN PANTALLA COMPLETA FUNCIONAL CON EFECTO AUDIO
    if conteo_productos and piezas_pendientes == 0 and not st.session_state.cerrar_modal_celebracion:
        if not st.session_state.reproducido_modal_audio:
            reproducir_sonido_celebracion()
            st.session_state.reproducido_modal_audio = True

        st.markdown(f"""
            <div class="custom-modal-overlay">
                <div class="custom-modal-box">
                    <img src="{LOGO_URL}" class="modal-logo-img-large" alt="Logo Mostacho">
                    <div class="celebration-title-orange-large">PRODUCCIÓN FINALIZADA</div>
                    <div class="celebration-sub-orange-large">
                        Se han completado todos los pedidos pendientes de la jornada.
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        modal_btn_col1, modal_btn_col2, modal_btn_col3 = st.columns([0.15, 0.70, 0.15])
        with modal_btn_col2:
            if st.button("REVISAR PENDIENTES", key="btn_cerrar_custom_modal", use_container_width=True):
                st.session_state.cerrar_modal_celebracion = True
                st.rerun()

    if conteo_productos:
        activos = []
        completados = []

        for prod, cant_total in conteo_productos.items():
            if prod in estado_global["completados"]:
                completados.append((prod, cant_total))
            else:
                activos.append((prod, cant_total))

        # ORDENAMIENTO POR CANTIDAD TOTAL (MAYOR A MENOR)
        activos.sort(key=lambda x: x[1], reverse=True)
        completados.sort(key=lambda x: x[1], reverse=True)

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
                        if ultima_upd and (ahora_utc - ultima_upd).total_seconds() < 120 and not es_completado:
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

                        # INDICADOR EN LÍNEA + ANIMACIÓN DE PULSO (< 30s)
                        info_popup = st.session_state.popups_nuevos.get(producto)
                        clase_pulso = ""
                        html_incremento = ""
                        if info_popup and not es_completado:
                            inc = info_popup["incremento"]
                            clase_pulso = "anim-pulso-nuevo"
                            html_incremento = f'<span class="txt-incremento">+{inc}</span>'

                        # RELACIÓN DE ASPECTO INTERNO FLUIDA PARA MÓVIL
                        col_txt, col_btn = st.columns([0.75, 0.25], gap="small")

                        with col_txt:
                            st.markdown(f"""
                                <div class="card-box-img {clase_estado} {clase_pulso}">
                                    {producto} {html_incremento}
                                </div>
                            """, unsafe_allow_html=True)

                        with col_btn:
                            st.markdown(f"""
                                <div class="num-box-masivo {clase_num_box} {clase_pulso}">
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

    # FOOTER DISCRETO Y SUTIL EN LA PARTE INFERIOR
    st.markdown(f"""
        <div class="footer-sutil">
            PROCESADAS HOY: <span>{piezas_completadas}</span> DE <span>{piezas_totales}</span> PIEZAS
        </div>
    """, unsafe_allow_html=True)

renderizar_tablero()