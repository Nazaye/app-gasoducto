import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from math import sqrt, pow

# ------------------ CONFIGURACIÓN DE LA PÁGINA ------------------
st.set_page_config(page_title="Optimización Gasoducto Trans-Andino", layout="wide")

# Estilos personalizados (fondo negro, letras, etc.)
st.markdown("""
    <style>
    /* Fondo general negro */
    .stApp {
        background-color: #000000;
    }
    /* Título principal: Arial 20, azul aguamarina */
    .titulo-principal {
        font-family: 'Arial', sans-serif;
        font-size: 20px;
        color: #7FFFD4;
        text-align: center;
        font-weight: bold;
    }
    /* Subtítulos: otra fuente bonita (Georgia) blanca */
    .subtitulo {
        font-family: 'Georgia', serif;
        font-size: 18px;
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
    /* Fondo de los bloques de métricas y alertas */
    .stMetric, .stAlert {
        background-color: #1E1E1E;
        border-radius: 10px;
        padding: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# Título principal
st.markdown('<p class="titulo-principal">📊 Proyecto: Optimización y Simulación Digital - Gasoducto Trans-Andino</p>', unsafe_allow_html=True)

# ------------------ FUNCIONES DE CÁLCULO ------------------
# Constantes y parámetros fijos
L_km = 400.0                # km
L_miles = L_km * 0.621371   # millas
T1_K = 293.15               # 20°C
T1_R = T1_K * 9/5           # Rankine (527.67 R)
gamma = 0.65
Z = 0.90
k = 1.28                    # índice adiabático para gas natural
eta = 0.85                  # eficiencia del compresor
horas_anio = 8760           # horas operación continua

# Tabla de tuberías (Diámetro Nominal, Ext mm, Esp mm, Costo $/m)
pipe_data = {
    "12\"": {"D_ext_mm": 323.8, "t_mm": 10.31, "costo_m": 185},
    "16\"": {"D_ext_mm": 406.4, "t_mm": 12.70, "costo_m": 260},
    "20\"": {"D_ext_mm": 508.0, "t_mm": 15.09, "costo_m": 350},
    "24\"": {"D_ext_mm": 609.6, "t_mm": 17.48, "costo_m": 440},
}

# Grados de acero
steel_data = {
    "X52": {"SMYS_psi": 52000, "F": 0.72},
    "X60": {"SMYS_psi": 60000, "F": 0.72},
}

def calcular_MAOP(D_ext_in, t_in, SMYS_psi, F):
    """Presión máxima admisible (Barlow) en psia"""
    return 2 * SMYS_psi * F * t_in / D_ext_in

def weymouth_k_loss(Q_MMscfd, L_seg_millas, D_in_pulg, gamma, T_R, Z):
    """Constante K = P1^2 - P2^2 para un segmento (E=1)"""
    return 433.5 * (Q_MMscfd**2) * L_seg_millas * gamma * T_R * Z / (D_in_pulg**5.33)

def calcular_perfil(N, Q, diametro, grado_acero, params_economicos):
    """
    Calcula presiones, potencias, costos y alertas.
    Retorna diccionario con resultados.
    """
    # Datos geométricos y de material
    diam_nom = diametro
    D_ext_mm = pipe_data[diam_nom]["D_ext_mm"]
    t_mm = pipe_data[diam_nom]["t_mm"]
    D_int_mm = D_ext_mm - 2*t_mm
    D_int_pulg = D_int_mm / 25.4
    costo_pipe_m = pipe_data[diam_nom]["costo_m"]
    
    SMYS_psi = steel_data[grado_acero]["SMYS_psi"]
    F = steel_data[grado_acero]["F"]
    
    # MAOP (límite de presión por Barlow)
    D_ext_pulg = D_ext_mm / 25.4
    t_pulg = t_mm / 25.4
    MAOP_psi = calcular_MAOP(D_ext_pulg, t_pulg, SMYS_psi, F)
    
    # Longitud por segmento (millas)
    L_seg_millas = L_miles / N
    # Pérdida K para cada segmento
    K_seg = weymouth_k_loss(Q, L_seg_millas, D_int_pulg, gamma, T1_R, Z)
    
    # Para cumplir presión final = 500 psia, despejamos P_descarga
    # P_final^2 = P_desc^2 - K_seg  =>  P_desc = sqrt(500^2 + K_seg)
    if K_seg < 0:
        st.error("Error numérico en la caída de presión.")
        return None
    P_desc_psi = sqrt(500**2 + K_seg)
    
    # Verificar que no supere MAOP
    supera_maop = P_desc_psi > MAOP_psi
    
    # Construir arrays de presión a lo largo del ducto (para gráfico)
    distancias_km = []
    presiones_psi = []
    dist_actual = 0.0
    # Presión en inicio antes de comprimir: 800 psia
    # Estación 1: succión = 800, descarga = P_desc_psi
    # Luego cada segmento baja hasta sqrt(P_desc^2 - K_seg) = 500 psia
    for i in range(N):
        # punto justo después de la compresión (inicio del segmento i)
        distancias_km.append(dist_actual)
        presiones_psi.append(P_desc_psi)
        # recorrido del segmento
        dist_seg_km = L_km / N
        # presión final del segmento (siempre 500 psia por diseño)
        distancias_km.append(dist_actual + dist_seg_km)
        presiones_psi.append(500.0)
        dist_actual += dist_seg_km
    
    # Cálculo de potencias y temperaturas de descarga en cada estación
    HP_total = 0.0
    T2_max_C = 0.0
    potencias_estacion = []
    
    # Primera estación: succión 800 psia
    P_suc = 800.0
    r = P_desc_psi / P_suc
    # Potencia fórmula empírica común en industria: HP = 0.0857 * Q * P_suc * (r^((k-1)/k)-1) / eta
    # (válida para Q en MMscfd, P en psia)
    factor = 0.0857
    HP_est = factor * Q * P_suc * (pow(r, (k-1)/k) - 1) / eta
    HP_total += HP_est
    potencias_estacion.append(HP_est)
    # Temperatura de descarga
    T2_K = T1_K * pow(r, (k-1)/k)
    T2_C = T2_K - 273.15
    if T2_C > T2_max_C:
        T2_max_C = T2_C
    
    # Estaciones 2 a N (succión siempre 500 psia, porque así lo impone el diseño)
    for _ in range(1, N):
        P_suc = 500.0
        r = P_desc_psi / P_suc
        HP_est = factor * Q * P_suc * (pow(r, (k-1)/k) - 1) / eta
        HP_total += HP_est
        potencias_estacion.append(HP_est)
        T2_K = T1_K * pow(r, (k-1)/k)
        T2_C = T2_K - 273.15
        if T2_C > T2_max_C:
            T2_max_C = T2_C
    
    # Alertas térmica y de presión final
    alerta_termica = T2_max_C > 65.0
    # Presión final de entrega (último punto del perfil)
    presion_final_psi = presiones_psi[-1]  # siempre 500 por construcción
    alerta_entrega = presion_final_psi < 500.0
    
    # ------------------ CÁLCULO DE COSTOS ------------------
    # CAPEX Tubería
    longitud_m = L_km * 1000
    capex_pipe = longitud_m * costo_pipe_m
    
    # CAPEX Compresores (estimado $1500 por HP)
    capex_comp = HP_total * 1500.0
    
    # CRF (factor de recuperación de capital)
    i = params_economicos["tasa_interes"] / 100.0
    n = 20  # años de vida útil
    if i > 0:
        CRF = i * (1+i)**n / ((1+i)**n - 1)
    else:
        CRF = 1/n
    
    # OPEX energía
    energia_anual_kWh = HP_total * 0.7457 * horas_anio   # HP a kW
    costo_energia = params_economicos["costo_energia"]   # USD/kWh
    opex_energia = energia_anual_kWh * costo_energia
    
    # OPEX adicional (mantenimiento) = 5% del CAPEX compresores (suposición)
    opex_mant = 0.05 * capex_comp
    
    OPEX_total = opex_energia + opex_mant
    CAPEX_total = capex_pipe + capex_comp
    TAC = CAPEX_total * CRF + OPEX_total
    
    # Desglose para gráfico
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

# ------------------ BARRA LATERAL (PARÁMETROS) ------------------
st.sidebar.markdown('<p class="subtitulo">⚙️ Panel de Configuración</p>', unsafe_allow_html=True)

# Parámetros económicos
st.sidebar.markdown("### 💰 Parámetros Económicos")
costo_energia = st.sidebar.number_input("Costo de energía (USD/kWh)", min_value=0.01, max_value=1.0, value=0.05, step=0.01, format="%.3f")
tasa_interes = st.sidebar.number_input("Tasa de interés anual (%)", min_value=0.0, max_value=30.0, value=8.0, step=0.5)
factor_steel = st.sidebar.number_input("Costo del acero (multiplicador)", min_value=0.5, max_value=2.0, value=1.0, step=0.05)

# Selección de diámetro y grado de acero
st.sidebar.markdown("### 📏 Tubería y Material")
diametro = st.sidebar.selectbox("Diámetro nominal", list(pipe_data.keys()))
grado_acero = st.sidebar.selectbox("Grado del acero", list(steel_data.keys()))

# Variables operativas
st.sidebar.markdown("### 🔧 Operación")
Q_diseno = st.sidebar.number_input("Flujo de gas (MMscfd)", min_value=100, max_value=1500, value=500, step=10)
N_estaciones = st.sidebar.slider("Número de estaciones de compresión", min_value=1, max_value=10, value=2, step=1)

# Aplicar multiplicador al costo de tubería (costo del acero)
for diam in pipe_data:
    pipe_data[diam]["costo_m"] *= factor_steel

params_economicos = {
    "costo_energia": costo_energia,
    "tasa_interes": tasa_interes,
}

# ------------------ PANEL PRINCIPAL ------------------
st.markdown('<p class="subtitulo">📈 Dashboard de Resultados</p>', unsafe_allow_html=True)

# Calcular todo
resultados = calcular_perfil(N_estaciones, Q_diseno, diametro, grado_acero, params_economicos)

if resultados:
    # Métricas principales
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💰 TAC (USD/año)", f"${resultados['TAC']:,.0f}")
    with col2:
        st.metric("⚙️ Potencia total instalada (HP)", f"{resultados['HP_total']:,.0f} HP")
    with col3:
        st.metric("📉 Presión final de entrega (psia)", f"{resultados['presion_final']:.1f}")
    
    # Gráfico de perfil hidráulico
    st.markdown('<p class="subtitulo">📉 Perfil Hidráulico: Presión vs Distancia</p>', unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=resultados['distancias_km'], y=resultados['presiones_psi'],
                             mode='lines+markers', name='Presión',
                             line=dict(color='#7FFFD4', width=3)))
    fig.update_layout(
        title="Presión a lo largo del gasoducto",
        xaxis_title="Distancia (km)",
        yaxis_title="Presión (psia)",
        plot_bgcolor='#1E1E1E',
        paper_bgcolor='#000000',
        font=dict(color='white'),
        hovermode='x'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Desglose de costos (gráfico de barras)
    st.markdown('<p class="subtitulo">📊 Desglose de Costos Anualizados</p>', unsafe_allow_html=True)
    costs = resultados['cost_breakdown']
    df_costs = pd.DataFrame({
        "Concepto": list(costs.keys()),
        "Monto (USD)": list(costs.values())
    })
    fig2 = go.Figure(go.Bar(x=df_costs["Concepto"], y=df_costs["Monto (USD)"],
                            marker_color='#7FFFD4'))
    fig2.update_layout(
        title="CAPEX vs OPEX",
        yaxis_title="USD",
        plot_bgcolor='#1E1E1E',
        paper_bgcolor='#000000',
        font=dict(color='white')
    )
    st.plotly_chart(fig2, use_container_width=True)
    
    # Sistema de alertas
    st.markdown('<p class="subtitulo">⚠️ Validación de Seguridad</p>', unsafe_allow_html=True)
    alerta1 = resultados['supera_MAOP']
    alerta2 = resultados['alerta_termica']
    alerta3 = resultados['alerta_entrega']
    
    if alerta1:
        st.error(f"🚨 ALERTA: La presión de descarga ({resultados['P_descarga']:.1f} psia) supera el MAOP de {resultados['MAOP']:.1f} psia. ¡Diseño inseguro!")
    else:
        st.success(f"✅ MAOP verificado: Descarga {resultados['P_descarga']:.1f} psia ≤ {resultados['MAOP']:.1f} psia")
    
    if alerta2:
        st.error(f"🔥 ALERTA TÉRMICA: Temperatura máxima de descarga = {resultados['T2_max_C']:.1f} °C > 65 °C. Riesgo de sobrecalentamiento.")
    else:
        st.success(f"✅ Temperatura de descarga máxima: {resultados['T2_max_C']:.1f} °C ≤ 65 °C")
    
    if alerta3:
        st.error(f"⚠️ Presión final de entrega ({resultados['presion_final']:.1f} psia) es inferior a 500 psia. No cumple requerimiento.")
    else:
        st.success(f"✅ Presión final de entrega = {resultados['presion_final']:.1f} psia ≥ 500 psia")
    
    # Información adicional de diseño
    with st.expander("🔍 Ver detalles del diseño actual"):
        st.write(f"**Diámetro interno:** {(pipe_data[diametro]['D_ext_mm'] - 2*pipe_data[diametro]['t_mm'])/25.4:.2f} pulgadas")
        st.write(f"**Presión de descarga por estación:** {resultados['P_descarga']:.1f} psia")
        st.write(f"**CAPEX total:** ${resultados['capex_total']:,.0f}")
        st.write(f"**OPEX total anual:** ${resultados['opex_total']:,.0f}")
        st.write(f"**Factor CRF (i={tasa_interes}%, 20 años):** {((tasa_interes/100)*(1+tasa_interes/100)**20/((1+tasa_interes/100)**20-1)):.4f}")
else:
    st.error("No se pudo calcular con los parámetros actuales. Revise los valores ingresados.")
