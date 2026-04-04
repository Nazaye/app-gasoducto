# app.py
# Proyecto de Optimización - Simulación de gasoducto
# Estudiante: [tu nombre] - 9no semestre

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# --------------------------------------------------
# Datos de tuberías (Tabla 1 del enunciado)
# --------------------------------------------------
tuberias = {
    "12": {"OD_mm": 323.8, "espesor_mm": 10.31, "costo_usd_m": 185},
    "16": {"OD_mm": 406.4, "espesor_mm": 12.70, "costo_usd_m": 260},
    "20": {"OD_mm": 508.0, "espesor_mm": 15.09, "costo_usd_m": 350},
    "24": {"OD_mm": 609.6, "espesor_mm": 17.48, "costo_usd_m": 440}
}

# Datos de aceros (Tabla 2)
aceros = {
    "X52": {"SMYS_psi": 52000, "F": 0.72},
    "X60": {"SMYS_psi": 60000, "F": 0.72}
}

# Parámetros fijos del problema
L_total_km = 400
P_recepcion = 800
P_min_entrega = 500
T_succ_C = 20
T_succ_R = (T_succ_C + 273.15) * 9/5
gamma = 0.65
Z = 0.90
k = 1.3
eta_comp = 0.85
horas_anuales = 8000
vida_anios = 20
R_univ = 1545
MW_aire = 28.97
MW_gas = gamma * MW_aire
R_gas = R_univ / MW_gas

# --------------------------------------------------
# Funciones de cálculo
# --------------------------------------------------
def diametro_interno(od_mm, esp_mm):
    id_mm = od_mm - 2 * esp_mm
    return id_mm / 25.4

def caida_presion_weymouth(P1, Q, L_mi, D_in, gamma, T_R, Z):
    const = 433.5
    term = const * (Q**2) * (L_mi * gamma * T_R * Z) / (D_in**5.33)
    P2_cuad = P1**2 - term
    if P2_cuad <= 0:
        return 1.0   # valor mínimo para evitar división por cero
    return np.sqrt(P2_cuad)

def potencia_compresor(Q, P_suc, P_desc, T_suc_R, Z, R_gas, k, eta):
    Q_scf_s = Q * 1e6 / (24 * 3600)
    rho_std = (14.7 * MW_gas) / (1.0 * R_univ * 520)
    m_dot = Q_scf_s * rho_std
    n = (k-1)/k
    head = (Z * R_gas * T_suc_R) * (1/n) * ((P_desc/P_suc)**n - 1)
    HP = (m_dot * head) / (550 * eta)
    return HP

def temp_descarga(T_suc_R, P_suc, P_desc, k):
    return T_suc_R * (P_desc / P_suc)**((k-1)/k)

def maop_barlow(OD_in, espesor_in, SMYS, F):
    return 2 * SMYS * F * espesor_in / OD_in

def costo_tuberia(dn, factor):
    return tuberias[dn]["costo_usd_m"] * (L_total_km * 1000) * factor

def crf(tasa, n):
    if tasa == 0:
        return 1/n
    return tasa * (1+tasa)**n / ((1+tasa)**n - 1)

# --------------------------------------------------
# Interfaz de Streamlit
# --------------------------------------------------
st.set_page_config(page_title="Gasoducto", layout="wide")
st.title("Simulación de Gasoducto Trans-Andino")
st.markdown("Optimización de Procesos - 3er semestre 2025")

# Sidebar: parámetros que el usuario puede cambiar
st.sidebar.header("Parámetros de diseño")

st.sidebar.subheader("Económicos")
costo_energia = st.sidebar.number_input("Costo energía (USD/kWh)", value=0.05, step=0.01)
factor_acero = st.sidebar.number_input("Factor costo acero", value=1.0, step=0.05)
tasa_int = st.sidebar.number_input("Tasa interés (%)", value=8.0) / 100.0
costo_comp_por_HP = st.sidebar.number_input("Costo compresor (USD/HP)", value=1200, step=100)

st.sidebar.subheader("Materiales")
dn_sel = st.sidebar.selectbox("Diámetro nominal (pulg)", options=list(tuberias.keys()))
grado_sel = st.sidebar.selectbox("Grado del acero", options=list(aceros.keys()))

st.sidebar.subheader("Operación")
Q = st.sidebar.number_input("Flujo (MMscfd)", value=500, step=50)
N = st.sidebar.slider("Número de estaciones de compresión", 0, 6, 2, 1)

# --------------------------------------------------
# Cálculos con los valores elegidos
# --------------------------------------------------
od_mm = tuberias[dn_sel]["OD_mm"]
esp_mm = tuberias[dn_sel]["espesor_mm"]
od_in = od_mm / 25.4
esp_in = esp_mm / 25.4
d_int_in = diametro_interno(od_mm, esp_mm)
SMYS = aceros[grado_sel]["SMYS_psi"]
F = aceros[grado_sel]["F"]

maop = maop_barlow(od_in, esp_in, SMYS, F)

L_mi = L_total_km * 0.621371
L_seg_mi = L_mi / (N + 1)

# Simulación de presión a lo largo del ducto
distancias_km = [0]
presiones = [P_recepcion]
P_actual = P_recepcion
HP_total = 0
T_max_C = 0

for i in range(N + 1):
    if i < N:
        # Caída en el segmento
        P_fin = caida_presion_weymouth(P_actual, Q, L_seg_mi, d_int_in, gamma, T_succ_R, Z)
        dist_km = (i+1) * (L_total_km / (N+1))
        distancias_km.append(dist_km)
        presiones.append(P_fin)

        # Compresor: eleva a P_recepcion
        P_suc = P_fin
        P_desc = P_recepcion
        HP = potencia_compresor(Q, P_suc, P_desc, T_succ_R, Z, R_gas, k, eta_comp)
        HP_total += HP

        T2_R = temp_descarga(T_succ_R, P_suc, P_desc, k)
        T2_C = (T2_R - 491.67) * 5/9
        if T2_C > T_max_C:
            T_max_C = T2_C

        P_actual = P_desc
    else:
        # Último tramo (sin compresor)
        P_final = caida_presion_weymouth(P_actual, Q, L_seg_mi, d_int_in, gamma, T_succ_R, Z)
        dist_km = (i+1) * (L_total_km / (N+1))
        distancias_km.append(dist_km)
        presiones.append(P_final)

# Costos
costo_ducto = costo_tuberia(dn_sel, factor_acero)
costo_comp = HP_total * costo_comp_por_HP
CAPEX = costo_ducto + costo_comp
CRF = crf(tasa_int, vida_anios)
OPEX = HP_total * 0.7457 * horas_anuales * costo_energia
TAC = CAPEX * CRF + OPEX

# Alertas
alerta_maop = P_recepcion > maop
alerta_temp = T_max_C > 65
alerta_presion = presiones[-1] < P_min_entrega

# --------------------------------------------------
# Mostrar resultados en la página principal
# --------------------------------------------------
st.subheader("Resultados principales")
col1, col2, col3 = st.columns(3)
col1.metric("TAC (USD/año)", f"${TAC:,.0f}")
col2.metric("Potencia total (HP)", f"{HP_total:,.0f}")
col3.metric("Presión final (psia)", f"{presiones[-1]:.1f}")

# Gráfico de perfil de presión
st.subheader("Perfil de presión")
fig = go.Figure()
fig.add_trace(go.Scatter(x=distancias_km, y=presiones, mode='lines+markers', name='Presión'))
fig.add_hline(y=P_min_entrega, line_dash="dash", line_color="red", annotation_text="P mínima entrega")
fig.add_hline(y=maop, line_dash="dash", line_color="orange", annotation_text="MAOP")
fig.update_layout(xaxis_title="Distancia (km)", yaxis_title="Presión (psia)")
st.plotly_chart(fig, use_container_width=True)

# Gráfico de desglose de costos
st.subheader("Desglose de costos anualizados")
costos_df = pd.DataFrame({
    "Concepto": ["CAPEX Tubería", "CAPEX Compresores", "OPEX Energía"],
    "Monto": [costo_ducto*CRF, costo_comp*CRF, OPEX]
})
fig2 = px.bar(costos_df, x="Concepto", y="Monto", text="Monto", title="Costo Total Anualizado")
st.plotly_chart(fig2, use_container_width=True)

# Validaciones
st.subheader("Validación de seguridad")
if alerta_maop:
    st.error(f"❌ La presión de descarga ({P_recepcion} psia) excede el MAOP de {maop:.1f} psia.")
else:
    st.success(f"✅ MAOP OK: {P_recepcion} ≤ {maop:.1f} psia")

if alerta_temp:
    st.error(f"❌ Temperatura máxima de descarga: {T_max_C:.1f} °C > 65 °C")
else:
    st.success(f"✅ Temperatura OK: {T_max_C:.1f} °C ≤ 65 °C")

if alerta_presion:
    st.error(f"❌ Presión final {presiones[-1]:.1f} psia < {P_min_entrega} psia")
else:
    st.success(f"✅ Presión de entrega OK: {presiones[-1]:.1f} ≥ {P_min_entrega} psia")

with st.expander("Ver detalles técnicos"):
    st.write(f"Diámetro interno: {d_int_in:.2f} in")
    st.write(f"Espesor de pared: {esp_in:.3f} in")
    st.write(f"MAOP calculado: {maop:.1f} psia")
    st.write(f"CRF: {CRF:.4f}")
    st.write(f"Potencia en kW: {HP_total * 0.7457:.0f} kW")
