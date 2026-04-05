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

    /* Título principal: GRANDE, mismo color que las tarjetas */
    .titulo-principal {
        font-family: 'Arial Black', sans-serif;
        font-size: 2.8rem;          /* Tamaño fijo enorme */
        font-weight: 800;
        color: #7FFFD4          /* Acuamarine */
        text-align: center;
        margin-bottom: 0.2rem;
        letter-spacing: 2px;
        text-transform: uppercase;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    /* Subtítulo: más pequeño, blanco, elegante */
    .subtitulo-principal {
        font-family: 'Poppins', 'Segoe UI', sans-serif;
        font-size: 22px;
        font-weight: 300;
        color: #FFFFFF;
        text-align: center;
        margin-top: -10px;
        margin-bottom: 40px;
        letter-spacing: 1px;
    }
    
    /* Encabezados de sección (RESULTADOS, Perfil Hidráulico, etc.) */
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
    
    /* Tarjetas de métricas (mismo color que el título) */
    .metric-card {
        background-color: #ccccc;   /* Azul os */
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
        color: #7FFFD4;   /* Aguamarina */
        margin: 0;
    }
    .metric-unit {
        font-family: 'Poppins', 'Segoe UI', sans-serif;
        font-size: 18px;
        font-weight: 400;
        color: #FFFFFF;
    }
    
    /* Descripciones en sidebar (amarillo suave) */
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
    
    /* Ajustes para los expanders de la sidebar */
    .streamlit-expanderHeader {
        font-family: 'Poppins', 'Segoe UI', sans-serif;
        font-weight: 600;
        font-size: 18px;
        color: #7FFFD4;
    }
    </style>
""", unsafe_allow_html=True)

# Títulos
st.markdown('<p class="titulo-principal">🔥 GASODUCTO TRANS-ANDINO</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitulo-principal">Gemelo digital | Simulación hidráulica & económica</p>', unsafe_allow_html=True)

# ------------------ FUNCIONES DE CÁLCULO ------------------
L_km = 400.0
L_miles = L_km * 0.621371
T1_K = 293.15
T1_R = T1_K * 9/5
gamma = 0.65
Z = 0.90
k = 1.28
eta = 0.85
horas_anio = 8760

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

def calcular_MAOP(D_ext_in, t_in, SMYS_psi, F):
    return 2 * SMYS_psi * F * t_in / D_ext_in

def weymouth_k_loss(Q_MMscfd, L_seg_millas, D_in_pulg, gamma, T_R, Z):
    return 433.5 * (Q_MMscfd**2) * L_seg_millas * gamma * T_R * Z / (D_in_pulg**5.33)

def calcular_perfil(N, Q, diametro, grado_acero, params_economicos, pipe_data_actual):
    diam_nom = diametro
    D_ext_mm = pipe_data_actual[diam_nom]["D_ext_mm"]
    t_mm = pipe_data_actual[diam_nom]["t_mm"]
    D_int_mm = D_ext_mm - 2*t_mm
    D_int_pulg = D_int_mm / 25.4
    costo_pipe_m = pipe_data_actual[diam_nom]["costo_m"]
    
    SMYS_psi = steel_data[grado_acero]["SMYS_psi"]
    F = steel_data[grado_acero]["F"]
    
    D_ext_pulg = D_ext_mm / 25.4
    t_pulg = t_mm / 25.4
    MAOP_psi = calcular_MAOP(D_ext_pulg, t_pulg, SMYS_psi, F)
    
    L_seg_millas = L_miles / N
    K_seg = weymouth_k_loss(Q, L_seg_millas, D_int_pulg, gamma, T1_R, Z)
    
    if K_seg < 0:
        return None
    P_desc_psi = sqrt(500**2 + K_seg)
    supera_maop = P_desc_psi > MAOP_psi
    
    distancias_km = []
    presiones_psi = []
    dist_actual = 0.0
    for i in range(N):
        distancias_km.append(dist_actual)
        presiones_psi.append(P_desc_psi)
        dist_seg_km = L_km / N
        distancias_km.append(dist_actual + dist_seg_km)
        presiones_psi.append(500.0)
        dist_actual += dist_seg_km
    
    HP_total = 0.0
    T2_max_C = 0.0
    factor = 0.0857
    P_suc = 800.0
    r = P_desc_psi / P_suc
    HP_est = factor * Q * P_suc * (pow(r, (k-1)/k) - 1) / eta
    HP_total += HP_est
    T2_K = T1_K * pow(r, (k-1)/k)
    T2_C = T2_K - 273.15
    T2_max_C = T2_C
    
    for _ in range(1, N):
        P_suc = 500.0
        r = P_desc_psi / P_suc
        HP_est = factor * Q * P_suc * (pow(r, (k-1)/k) - 1) / eta
        HP_total += HP_est
        T2_K = T1_K * pow(r, (k-1)/k)
        T2_C = T2_K - 273.15
        if T2_C > T2_max_C:
            T2_max_C = T2_C
    
    alerta_termica = T2_max_C > 65.0
    presion_final_psi = presiones_psi[-1]
    alerta_entrega = presion_final_psi < 500.0
    
    longitud_m = L_km * 1000
    capex_pipe = longitud_m * costo_pipe_m
    capex_comp = HP_total * 1500.0
    
    i = params_economicos["tasa_interes"] / 100.0
    n = 20
    if i > 0:
        CRF = i * (1+i)**n / ((1+i)**n - 1)
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
        "presion_final": presion_final_psi,
        "P_descarga": P_desc_psi,
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
        st.error(f"🚨 ALERTA: Presión de descarga ({resultados['P_descarga']:.1f} psia) > MAOP ({resultados['MAOP']:.1f} psia)")
    else:
        st.success(f"✅ MAOP verificado: {resultados['P_descarga']:.1f} ≤ {resultados['MAOP']:.1f} psia")
    
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
        st.write(f"**Presión de descarga por estación:** {resultados['P_descarga']:.1f} psia")
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
