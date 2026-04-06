import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from math import sqrt, pow

# ------------------ CONFIGURACIÓN DE LA PÁGINA ------------------
st.set_page_config(page_title="Gasoducto Trans-Andino", layout="wide")

# Estilos CSS personalizados para homogeneidad
st.markdown("""
    <style>
    /* Fuente global profesional */
    html, body, .stApp, .stMarkdown, .stText, .stNumberInput, .stSelectbox, .stSlider {
        font-family: 'Poppins', 'Segoe UI', 'Roboto', sans-serif;
    }
    
    /* Fondo negro */
    .stApp {
        background-color: #000000;
    }

    /* Título principal */
    .titulo-principal {
        font-family: 'Arial Black', sans-serif;
        font-size: 4rem !important;
        font-weight: 800;
        color: #7FFFD4;
        text-align: center;
        margin-bottom: 0.2rem;
        letter-spacing: 2px;
        text-transform: uppercase;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    /* Subtítulo */
    .subtitulo-principal {
        font-family: 'Poppins', 'Segoe UI', sans-serif;
        font-size: 24px !important;
        font-weight: 300;
        color: #FFFFFF;
        text-align: center;
        margin-top: -10px;
        margin-bottom: 40px;
        letter-spacing: 1px;
    }
    
    /* Encabezados de sección */
    .seccion-titulo {
        font-family: 'Poppins', 'Segoe UI', sans-serif;
        font-size: 28px;
        font-weight: 600;
        color: #FFFFFF;
        margin-top: 30px;
        margin-bottom: 20px;
        border-left: 5px solid #7FFFD4;
        padding-left: 15px;
    }
    
    /* Tarjetas de métricas */
    .metric-card {
        background-color: #1E1E2E;
        border-radius: 20px;
        padding: 25px 15px;
        text-align: center;
        box-shadow: 0 10px 20px rgba(0,0,0,0.4);
        border: 1px solid #2c5a9e;
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-5px);
    }
    .metric-label {
        font-family: 'Poppins', 'Segoe UI', sans-serif;
        font-size: 18px;
        font-weight: 500;
        color: #DDDDDD;
        margin-bottom: 12px;
    }
    .metric-value {
        font-family: 'Poppins', 'Segoe UI', sans-serif;
        font-size: 36px;
        font-weight: 700;
        color: #7FFFD4;
        margin: 0;
    }
    .metric-unit {
        font-family: 'Poppins', 'Segoe UI', sans-serif;
        font-size: 18px;
        font-weight: 400;
        color: #FFFFFF;
    }
    
    /* Descripciones en sidebar */
    .descripcion {
        font-size: 13px;
        color: #FFFACD;
        margin-bottom: 8px;
        font-style: italic;
        background-color: #2E2E2E;
        padding: 5px 8px;
        border-radius: 8px;
        font-family: 'Poppins', 'Segoe UI', sans-serif;
    }
    
    /* ========== BARRA LATERAL Y EXPANDERS NEGROS ========== */
    /* Fondo de la barra lateral */
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] > div,
    section[data-testid="stSidebar"] div[data-testid="stSidebarContent"],
    .css-1d391kg, .st-emotion-cache-1d391kg,
    .st-emotion-cache-16txtl3, .st-emotion-cache-1v0mbdj {
        background-color: #000000 !important;
    }
    
    /* Encabezados de expander (color del texto) */
    .streamlit-expanderHeader {
        font-family: 'Poppins', 'Segoe UI', sans-serif;
        font-weight: 600;
        font-size: 18px;
        color: #7FFFD4 !important;
        background-color: #000000 !important;
    }
    
    /* Inputs y otros elementos */
    section[data-testid="stSidebar"] .stNumberInput,
    section[data-testid="stSidebar"] .stSelectbox,
    section[data-testid="stSidebar"] .stSlider {
        background-color: #000000 !important;
    }
    
    /* Etiquetas de los inputs en la barra lateral: blanco */
    section[data-testid="stSidebar"] .stNumberInput label,
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stSlider label {
        color: #FFFFFF !important;
    }
    </style>
""", unsafe_allow_html=True)

# Títulos (con emoji de gas 💨)
st.markdown('<p class="titulo-principal">💨 GASODUCTO TRANS-ANDINO</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitulo-principal">Gemelo digital | Simulación hidráulica & económica</p>', unsafe_allow_html=True)

# ------------------ FUNCIONES DE CÁLCULO (CORREGIDAS) ------------------
L_km = 400.0
L_miles = L_km * 0.621371
T1_K = 293.15
T1_R = T1_K * 9/5        # Rankine
gamma = 0.65
Z = 0.90
k = 1.28                 # Relación de calores específicos (dato típico)
eta = 0.85               # Eficiencia del compresor
horas_anio = 8760        # horas de operación por año

# Constante universal
R_univ = 10.7316         # psi·ft³/(lbmol·R)
MW_aire = 28.97
MW = gamma * MW_aire     # lb/lbmol
R_esp = R_univ / MW      # psi·ft³/(lbm·R)   (constante específica)

# Factor de conversión para potencia (de la ecuación del enunciado)
# La fórmula: HP = (Q*1e6)/(24*3600*η) * (Z*R_esp*T1_R)/(k-1) * [(Pout/Pin)^((k-1)/k) - 1]
# El primer factor da scf/s. Multiplicado por (Z*R_esp*T1_R)/(k-1) da (lbf·ft/lbm)·(scf/s)
# Para obtener HP (550 lbf·ft/s = 1 HP), necesitamos convertir scf a lb usando la densidad en condiciones estándar.
# Pero como la fórmula del enunciado ya está "adimensionalizada", asumimos que R_esp está en (lbf·ft)/(lbm·R)
# y que Q está en MMscfd. Para evitar confusiones, usaremos una versión común en ingeniería:
# HP = 0.0857 * Q * (Z * T1_R / MW) * (k/(k-1)) * (r^((k-1)/k) - 1) / eta  (con Q en MMscfd, T1_R en R, MW en lb/lbmol)
# Este factor 0.0857 proviene de (1e6)/(24*3600)* (R_univ/550) etc. Es ampliamente usado.
# Lo dejamos así para mantener coherencia con cálculos previos que sí daban resultados razonables.
# Pero para mayor precisión, usaremos la fórmula directa con la densidad estándar.
# Vamos a implementar la fórmula correcta paso a paso.

def potencia_compresor(Q_MMscfd, P_suc_psia, P_desc_psia, T_suc_R, Z, k, MW, eta):
    """
    Calcula la potencia en HP usando la fórmula termodinámica estándar.
    Q_MMscfd: flujo en millones de pies cúbicos por día (base 14.7 psia, 60°F)
    """
    # Flujo másico en lb/s
    Q_scf_s = Q_MMscfd * 1e6 / (24 * 3600)   # scf/s
    # Densidad del gas en condiciones estándar (14.7 psia, 60°F = 520 R)
    P_std = 14.7          # psia
    T_std = 520           # Rankine
    Z_std = 1.0
    rho_std = (P_std * 144) * MW / (R_univ * T_std)   # lb/scf (144 para convertir psia a lbf/ft²)
    m_dot = Q_scf_s * rho_std                         # lb/s
    # Relación de compresión
    r = P_desc_psia / P_suc_psia
    # Exponente politrópico
    n = (k - 1) / k
    # Head politrópico (ft·lbf/lb)
    H_p = (Z * R_esp * T_suc_R) * (1 / n) * (pow(r, n) - 1)
    # Potencia en HP
    HP = (m_dot * H_p) / (550 * eta)
    return HP

def weymouth_drop(P1, Q, L_mi, D_in, gamma, T_R, Z):
    """Retorna P2 (psia) después de un segmento de longitud L_mi (millas)"""
    const = 433.5
    term = const * (Q**2) * L_mi * gamma * T_R * Z / (pow(D_in, 5.33))
    P2_sq = P1**2 - term
    if P2_sq <= 0:
        return 0.1
    return sqrt(P2_sq)

def calcular_MAOP(D_ext_in, t_in, SMYS_psi, F):
    return 2 * SMYS_psi * F * t_in / D_ext_in

# Datos de tuberías y aceros (igual que antes)
pipe_data_base = {
    "12\"": {"D_ext_mm": 323.8, "t_mm": 10.31, "costo_m": 185},
    "16\"": {"D_ext_mm": 406.4, "t_mm": 12.70, "costo_m": 260},
    "20\"": {"D_ext_mm": 508.0, "t_mm": 15.09, "costo_m": 350},
    "24\"": {"D_ext_mm": 609.6, "t_mm": 17.48, "costo_m": 440},
}
steel_data = {
    "X52": {"SMYS_psi": 52000, "F": 0.72},
    "X60": {"SMYS_psi": 60000, "F": 0.72},
}

def calcular_perfil(N, Q, diametro, grado_acero, params_economicos, pipe_data_actual):
    # Extraer datos de tubería
    D_ext_mm = pipe_data_actual[diametro]["D_ext_mm"]
    t_mm = pipe_data_actual[diametro]["t_mm"]
    D_int_mm = D_ext_mm - 2*t_mm
    D_int_pulg = D_int_mm / 25.4
    costo_pipe_m = pipe_data_actual[diametro]["costo_m"]
    
    # Datos del acero
    SMYS_psi = steel_data[grado_acero]["SMYS_psi"]
    F = steel_data[grado_acero]["F"]
    D_ext_pulg = D_ext_mm / 25.4
    t_pulg = t_mm / 25.4
    MAOP_psi = calcular_MAOP(D_ext_pulg, t_pulg, SMYS_psi, F)
    
    # Longitud de cada segmento (millas). Hay N+1 segmentos (entre estaciones)
    L_seg_mi = L_miles / (N + 1)
    
    # Inicializar vectores
    distancias_km = [0.0]
    presiones_psi = [800.0]   # presión inicial
    P_actual = 800.0
    HP_total = 0.0
    T2_max_C = 0.0
    
    # Simular los primeros N segmentos (cada uno seguido de un compresor)
    for i in range(N):
        # Caída en el segmento i+1
        P_fin_seg = weymouth_drop(P_actual, Q, L_seg_mi, D_int_pulg, gamma, T1_R, Z)
        dist_km = (i+1) * (L_km / (N+1))
        distancias_km.append(dist_km)
        presiones_psi.append(P_fin_seg)
        
        # Compresor: eleva la presión a 800 psia
        P_suc = P_fin_seg
        P_desc = 800.0
        HP = potencia_compresor(Q, P_suc, P_desc, T1_R, Z, k, MW, eta)
        HP_total += HP
        
        # Temperatura de descarga
        r = P_desc / P_suc
        T2_R = T1_R * pow(r, (k-1)/k)
        T2_C = (T2_R - 491.67) * 5/9
        if T2_C > T2_max_C:
            T2_max_C = T2_C
        
        # Actualizar presión para el siguiente segmento
        P_actual = P_desc
        # Agregar punto de presión de descarga (para el gráfico)
        if i < N-1:
            distancias_km.append(dist_km)
            presiones_psi.append(P_desc)
    
    # Último segmento (sin compresor al final)
    P_final = weymouth_drop(P_actual, Q, L_seg_mi, D_int_pulg, gamma, T1_R, Z)
    distancias_km.append(L_km)
    presiones_psi.append(P_final)
    
    # Alertas
    supera_maop = (800.0 > MAOP_psi)   # la presión de descarga es 800 psia
    alerta_termica = (T2_max_C > 65.0)
    alerta_entrega = (P_final < 500.0)
    
    # Costos
    longitud_m = L_km * 1000
    capex_pipe = longitud_m * costo_pipe_m
    capex_comp = HP_total * 1500.0   # costo estándar por HP instalado
    
    i_tasa = params_economicos["tasa_interes"] / 100.0
    n = 20
    if i_tasa > 0:
        CRF = i_tasa * (1+i_tasa)**n / ((1+i_tasa)**n - 1)
    else:
        CRF = 1/n
    
    energia_anual_kWh = HP_total * 0.7457 * horas_anio
    opex_energia = energia_anual_kWh * params_economicos["costo_energia"]
    opex_mant = 0.05 * capex_comp
    OPEX_total = opex_energia + opex_mant
    CAPEX_total = capex_pipe + capex_comp
    TAC = CAPEX_total * CRF + OPEX_total
    
    cost_breakdown = {
        "CAPEX Ducto": capex_pipe,
        "CAPEX Compresores": capex_comp,
        "OPEX Energía": opex_energia,
        "OPEX Mantenimiento": opex_mant,
    }
    
    return {
        "TAC": TAC,
        "HP_total": HP_total,
        "presion_final": P_final,
        "P_descarga": 800.0,
        "MAOP": MAOP_psi,
        "supera_MAOP": supera_maop,
        "alerta_termica": alerta_termica,
        "alerta_entrega": alerta_entrega,
        "T2_max_C": T2_max_C,
        "distancias_km": distancias_km,
        "presiones_psi": presiones_psi,
        "cost_breakdown": cost_breakdown,
        "capex_total": CAPEX_total,
        "opex_total": OPEX_total,
    }

# ------------------ BARRA LATERAL ------------------
st.sidebar.markdown('<p style="font-size:24px; font-weight:700; color:#7FFFD4; margin-bottom:15px;">⚙️ CONFIGURACIÓN</p>', unsafe_allow_html=True)

pipe_data = pipe_data_base.copy()

with st.sidebar.expander("💰 PARÁMETROS ECONÓMICOS", expanded=True):
    st.markdown('<div class="descripcion">💡 Mayor costo energía → mayor OPEX (gasto anual).</div>', unsafe_allow_html=True)
    costo_energia = st.number_input("USD/kWh", min_value=0.01, max_value=1.0, value=0.05, step=0.01, format="%.3f", key="energia")
    
    st.markdown('<div class="descripcion">💡 Tasa interés alta → encarece el costo anual del capital (CRF).</div>', unsafe_allow_html=True)
    tasa_interes = st.number_input("% anual", min_value=0.0, max_value=30.0, value=8.0, step=0.5, key="interes")
    
    st.markdown('<div class="descripcion">💡 Multiplica costo del acero (simula variaciones de mercado).</div>', unsafe_allow_html=True)
    factor_steel = st.number_input("Factor acero", min_value=0.5, max_value=2.0, value=1.0, step=0.05, key="acero")

with st.sidebar.expander("📏 TUBERÍA Y MATERIAL", expanded=True):
    st.markdown('<div class="descripcion">💡 Mayor diámetro → menor caída presión, pero más CAPEX.</div>', unsafe_allow_html=True)
    diametro = st.selectbox("Diámetro nominal", list(pipe_data.keys()), key="diam")
    
    st.markdown('<div class="descripcion">💡 Mayor grado (X60) soporta más presión (MAOP más alto).</div>', unsafe_allow_html=True)
    grado_acero = st.selectbox("Grado del acero", list(steel_data.keys()), key="grado")

with st.sidebar.expander("🔧 OPERACIÓN", expanded=True):
    st.markdown('<div class="descripcion">💡 Más flujo → más pérdida de presión y más potencia requerida.</div>', unsafe_allow_html=True)
    Q_diseno = st.number_input("Flujo (MMscfd)", min_value=100, max_value=1500, value=500, step=10, key="flujo")
    
    st.markdown('<div class="descripcion">💡 Más estaciones → reduce presión por etapa, pero sube CAPEX compresores.</div>', unsafe_allow_html=True)
    N_estaciones = st.slider("N° estaciones", min_value=1, max_value=10, value=2, step=1, key="estaciones")

# Aplicar factor de acero
for diam in pipe_data:
    pipe_data[diam]["costo_m"] = pipe_data_base[diam]["costo_m"] * factor_steel

params_economicos = {
    "costo_energia": costo_energia,
    "tasa_interes": tasa_interes,
}

# ------------------ PANEL PRINCIPAL ------------------
st.markdown('<div class="seccion-titulo">📊 RESULTADOS</div>', unsafe_allow_html=True)

resultados = calcular_perfil(N_estaciones, Q_diseno, diametro, grado_acero, params_economicos, pipe_data)

if resultados:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">💰 TAC (USD/año)</div>
                <div class="metric-value">${resultados['TAC']:,.0f}</div>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">⚙️ Potencia total</div>
                <div class="metric-value">{resultados['HP_total']:,.0f} <span class="metric-unit">HP</span></div>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">📉 Presión final</div>
                <div class="metric-value">{resultados['presion_final']:.1f} <span class="metric-unit">psia</span></div>
            </div>
        """, unsafe_allow_html=True)
    
    # Perfil hidráulico
    st.markdown('<div class="seccion-titulo">📈 PERFIL HIDRÁULICO</div>', unsafe_allow_html=True)
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=resultados['distancias_km'], y=resultados['presiones_psi'],
                             mode='lines+markers', name='Presión del gas',
                             line=dict(color='#7FFFD4', width=4),
                             marker=dict(size=8, color='#FFD700')))
    fig1.update_layout(
        title="Presión vs Distancia a lo largo del gasoducto",
        xaxis_title="Distancia (km)",
        yaxis_title="Presión (psia)",
        plot_bgcolor='#1E1E1E',
        paper_bgcolor='#000000',
        font=dict(family="Poppins, Segoe UI, Roboto, sans-serif", color='white', size=12),
        hovermode='x',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig1, use_container_width=True)
    
    # Desglose de costos
    st.markdown('<div class="seccion-titulo">💰 DESGLOSE DE COSTOS ANUALIZADOS</div>', unsafe_allow_html=True)
    costs = resultados['cost_breakdown']
    conceptos = list(costs.keys())
    montos = list(costs.values())
    colores = ['#1F77B4', '#FF7F0E', '#2CA02C', '#D62728']
    fig2 = go.Figure(go.Bar(
        x=conceptos,
        y=montos,
        marker_color=colores,
        text=[f"${m:,.0f}" for m in montos],
        textposition='outside',
        name='Monto USD'
    ))
    fig2.update_layout(
        title="Distribución de CAPEX y OPEX",
        yaxis_title="USD",
        plot_bgcolor='#1E1E1E',
        paper_bgcolor='#000000',
        font=dict(family="Poppins, Segoe UI, Roboto, sans-serif", color='white'),
        showlegend=False
    )
    st.plotly_chart(fig2, use_container_width=True)
    
    # Validación de seguridad
    st.markdown('<div class="seccion-titulo">⚠️ VALIDACIÓN DE SEGURIDAD</div>', unsafe_allow_html=True)
    if resultados['supera_MAOP']:
        st.error(f"🚨 ALERTA: Presión de descarga (800 psia) > MAOP ({resultados['MAOP']:.1f} psia)")
    else:
        st.success(f"✅ MAOP verificado: 800 psia ≤ {resultados['MAOP']:.1f} psia")
    
    if resultados['alerta_termica']:
        st.error(f"🔥 ALERTA TÉRMICA: Temperatura máxima = {resultados['T2_max_C']:.1f} °C > 65 °C")
    else:
        st.success(f"✅ Temperatura de descarga: {resultados['T2_max_C']:.1f} °C ≤ 65 °C")
    
    if resultados['alerta_entrega']:
        st.error(f"⚠️ Presión final de entrega = {resultados['presion_final']:.1f} psia < 500 psia")
    else:
        st.success(f"✅ Presión de entrega: {resultados['presion_final']:.1f} psia ≥ 500 psia")
    
    with st.expander("🔍 Ver detalles técnicos del diseño"):
        st.write(f"**Diámetro interno:** {(pipe_data[diametro]['D_ext_mm'] - 2*pipe_data[diametro]['t_mm'])/25.4:.2f} pulg")
        st.write(f"**Presión de descarga por estación:** 800 psia")
        st.write(f"**CAPEX total:** ${resultados['capex_total']:,.0f}")
        st.write(f"**OPEX total anual:** ${resultados['opex_total']:,.0f}")
        i = tasa_interes / 100.0
        n = 20
        if i > 0:
            CRF = i * (1+i)**n / ((1+i)**n - 1)
        else:
            CRF = 1/n
        st.write(f"**Factor CRF (i={tasa_interes}%, 20 años):** {CRF:.4f}")
else:
    st.error("No se pudo calcular con los parámetros actuales. Revise los valores ingresados.")
