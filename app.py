import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from math import sqrt, pow

# ------------------ CONFIGURACIÓN DE LA PÁGINA ------------------
st.set_page_config(page_title="Optimización Gasoducto Trans-Andino", layout="wide")

# Estilos personalizados
st.markdown("""
    <style>
    /* Fondo general negro */
    .stApp {
        background-color: #000000;
    }
    /* Título principal: tamaño 110, mayúsculas, azul aguamarina */
    .titulo-principal {
        font-family: 'Arial', sans-serif;
        font-size: 110px;
        color: #7FFFD4;
        text-align: center;
        font-weight: bold;
        margin-bottom: 5px;
        line-height: 1.1;
        text-transform: uppercase;
    }
    /* Subtítulo: fuente cursiva / serif blanca más pequeña */
    .subtitulo-principal {
        font-family: 'Courier New', monospace;
        font-size: 20px;
        color: #FFFFFF;
        text-align: center;
        margin-top: 0px;
        margin-bottom: 30px;
        letter-spacing: 1px;
    }
    /* Subtítulos de sección (Resultados, etc.) */
    .subtitulo {
        font-family: 'Georgia', serif;
        font-size: 28px;
        color: #FFFFFF;
        margin-top: 20px;
        margin-bottom: 10px;
        font-weight: bold;
    }
    /* Texto normal blanco */
    .texto-normal {
        font-family: 'Verdana', sans-serif;
        font-size: 14px;
        color: #F0F0F0;
    }
    /* Descripciones cortas en amarillo suave */
    .descripcion {
        font-size: 13px;
        color: #FFFACD;   /* amarillo suave */
        margin-bottom: 8px;
        font-style: italic;
        background-color: #2E2E2E;
        padding: 5px;
        border-radius: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# Título principal (mayúsculas, tamaño 110)
st.markdown('<p class="titulo-principal">GASODUCTO TRANS-ANDINO</p>', unsafe_allow_html=True)
# Subtítulo
st.markdown('<p class="subtitulo-principal">Gemelo digital | Simulación hidráulica & económica</p>', unsafe_allow_html=True)

# ------------------ FUNCIONES DE CÁLCULO ------------------
# Constantes y parámetros fijos
L_km = 400.0
L_miles = L_km * 0.621371
T1_K = 293.15
T1_R = T1_K * 9/5
gamma = 0.65
Z = 0.90
k = 1.28
eta = 0.85
horas_anio = 8760

# Tabla de tuberías base
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

# ------------------ BARRA LATERAL (EXPANDERS CON DESCRIPCIONES CORTAS) ------------------
st.sidebar.markdown('<p style="font-size:24px; font-weight:bold; color:#7FFFD4;">⚙️ CONFIGURACIÓN</p>', unsafe_allow_html=True)

# Copia de trabajo de pipe_data
pipe_data = pipe_data_base.copy()

# Sección Económicos
with st.sidebar.expander("💰 PARÁMETROS ECONÓMICOS", expanded=True):
    st.markdown('<div class="descripcion">💡 Mayor costo energía → mayor OPEX (gasto anual).</div>', unsafe_allow_html=True)
    costo_energia = st.number_input("USD/kWh", min_value=0.01, max_value=1.0, value=0.05, step=0.01, format="%.3f", key="energia")
    
    st.markdown('<div class="descripcion">💡 Tasa interés alta → encarece el costo anual del capital (CRF).</div>', unsafe_allow_html=True)
    tasa_interes = st.number_input("% anual", min_value=0.0, max_value=30.0, value=8.0, step=0.5, key="interes")
    
    st.markdown('<div class="descripcion">💡 Multiplica costo del acero (simula variaciones de mercado).</div>', unsafe_allow_html=True)
    factor_steel = st.number_input("Factor acero", min_value=0.5, max_value=2.0, value=1.0, step=0.05, key="acero")

# Sección Tubería y Material
with st.sidebar.expander("📏 TUBERÍA Y MATERIAL", expanded=True):
    st.markdown('<div class="descripcion">💡 Mayor diámetro → menor caída presión, pero más CAPEX.</div>', unsafe_allow_html=True)
    diametro = st.selectbox("Diámetro nominal", list(pipe_data.keys()), key="diam")
    
    st.markdown('<div class="descripcion">💡 Mayor grado (X60) soporta más presión (MAOP más alto).</div>', unsafe_allow_html=True)
    grado_acero = st.selectbox("Grado del acero", list(steel_data.keys()), key="grado")

# Sección Operación
with st.sidebar.expander("🔧 OPERACIÓN", expanded=True):
    st.markdown('<div class="descripcion">💡 Más flujo → más pérdida de presión y más potencia requerida.</div>', unsafe_allow_html=True)
    Q_diseno = st.number_input("Flujo (MMscfd)", min_value=100, max_value=1500, value=500, step=10, key="flujo")
    
    st.markdown('<div class="descripcion">💡 Más estaciones → reduce presión por etapa, pero sube CAPEX compresores.</div>', unsafe_allow_html=True)
    N_estaciones = st.slider("N° estaciones", min_value=1, max_value=10, value=2, step=1, key="estaciones")

# Aplicar multiplicador del acero a los costos de tubería
for diam in pipe_data:
    pipe_data[diam]["costo_m"] = pipe_data_base[diam]["costo_m"] * factor_steel

params_economicos = {
    "costo_energia": costo_energia,
    "tasa_interes": tasa_interes,
}

# ------------------ PANEL PRINCIPAL ------------------
st.markdown('<p class="subtitulo">📊 RESULTADOS</p>', unsafe_allow_html=True)  # Cambiado de Dashboard a Resultados

resultados = calcular_perfil(N_estaciones, Q_diseno, diametro, grado_acero, params_economicos, pipe_data)

if resultados:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💰 TAC (USD/año)", f"${resultados['TAC']:,.0f}")
    with col2:
        st.metric("⚙️ Potencia total (HP)", f"{resultados['HP_total']:,.0f} HP")
    with col3:
        st.metric("📉 Presión final (psia)", f"{resultados['presion_final']:.1f}")
    
    # Gráfico de perfil hidráulico (con leyenda)
    st.markdown('<p class="subtitulo" style="font-size:22px;">📉 Perfil Hidráulico</p>', unsafe_allow_html=True)
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(x=resultados['distancias_km'], y=resultados['presiones_psi'],
                             mode='lines+markers', name='Presión del gas',
                             line=dict(color='#7FFFD4', width=3),
                             marker=dict(size=6, color='#FFD700')))
    fig1.update_layout(
        title="Presión vs Distancia a lo largo del gasoducto",
        xaxis_title="Distancia (km)",
        yaxis_title="Presión (psia)",
        plot_bgcolor='#1E1E1E',
        paper_bgcolor='#000000',
        font=dict(color='white'),
        hovermode='x',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig1, use_container_width=True)
    
    # Gráfico de desglose de costos (SIN leyenda)
    st.markdown('<p class="subtitulo" style="font-size:22px;">📊 Desglose de Costos Anualizados</p>', unsafe_allow_html=True)
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
        font=dict(color='white'),
        showlegend=False   # Leyenda eliminada del gráfico de barras
    )
    st.plotly_chart(fig2, use_container_width=True)
    
    # Alertas de seguridad
    st.markdown('<p class="subtitulo" style="font-size:22px;">⚠️ Validación de Seguridad</p>', unsafe_allow_html=True)
    if resultados['supera_MAOP']:
        st.error(f"🚨 ALERTA: Descarga {resultados['P_descarga']:.1f} psia > MAOP {resultados['MAOP']:.1f} psia")
    else:
        st.success(f"✅ MAOP: {resultados['P_descarga']:.1f} ≤ {resultados['MAOP']:.1f} psia")
    
    if resultados['alerta_termica']:
        st.error(f"🔥 ALERTA: Temperatura máxima {resultados['T2_max_C']:.1f} °C > 65 °C")
    else:
        st.success(f"✅ Temperatura: {resultados['T2_max_C']:.1f} °C ≤ 65 °C")
    
    if resultados['alerta_entrega']:
        st.error(f"⚠️ Presión final {resultados['presion_final']:.1f} psia < 500 psia")
    else:
        st.success(f"✅ Presión entrega: {resultados['presion_final']:.1f} psia")
    
    with st.expander("🔍 Detalles técnicos del diseño"):
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
        st.write(f"**CRF (i={tasa_interes}%, 20 años):** {CRF:.4f}")
else:
    st.error("Error en los cálculos. Revise los valores ingresados.")
