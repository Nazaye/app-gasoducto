import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ------------------------------------------------------------
# CONFIGURACIÓN Y ESTILOS
# ------------------------------------------------------------
st.set_page_config(page_title="🛢️ Gasoducto", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    section[data-testid="stSidebar"] { order: 2; min-width: 380px; width: 380px; background-color: #14161c; border-left: 1px solid #2c3e50; }
    .stApp { background-color: #0a0c10; }
    .stMarkdown, .stText, .stNumberInput label, .stSelectbox label, .stSlider label, .stMetric label { color: #ffffff !important; }
    .main-title { font-family: 'Arial Black', sans-serif; font-size: 2.8rem; text-align: center; color: #00aaff; text-transform: uppercase; letter-spacing: 2px; }
    .subtitle { text-align: center; color: #cccccc; font-size: 1rem; }
    .metric-card { background-color: #1e1e2a; padding: 1rem; border-radius: 12px; text-align: center; border-top: 4px solid #00aaff; }
    h1, h2, h3 { color: #00aaff !important; }
    .help-text { font-size: 0.75rem; color: #88aacc; margin-top: -8px; margin-bottom: 12px; font-style: italic; }
    .recommendation-box { background-color: #1a222a; border-left: 4px solid #ffaa00; padding: 1rem; border-radius: 8px; margin: 1rem 0; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🛢️ GASODUCTO TRANS-ANDINO</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Simulación hidráulica y optimización económica | Ecuaciones del enunciado</div>', unsafe_allow_html=True)
st.markdown("---")

# ------------------------------------------------------------
# DATOS TÉCNICOS (PDF)
# ------------------------------------------------------------
TUBERIAS = {
    "12 pulgadas": {"D_ext_mm": 323.8, "t_mm": 10.31, "costo_base": 185},
    "16 pulgadas": {"D_ext_mm": 406.4, "t_mm": 12.70, "costo_base": 260},
    "20 pulgadas": {"D_ext_mm": 508.0, "t_mm": 15.09, "costo_base": 350},
    "24 pulgadas": {"D_ext_mm": 609.6, "t_mm": 17.48, "costo_base": 440}
}
ACEROS = {"X52": {"SMYS_psi": 52000, "F": 0.72}, "X60": {"SMYS_psi": 60000, "F": 0.72}}

# ------------------------------------------------------------
# PARÁMETROS FIJOS (caso base)
# ------------------------------------------------------------
L_TOTAL_KM = 400.0
P_RECEPCION = 800.0          # psia
P_MIN_ENTREGA = 500.0        # psia
T_SUC_C = 20.0
T_SUC_R = (T_SUC_C + 273.15) * 9/5   # Rankine = 527.67
GAMMA = 0.65
Z = 0.90
K = 1.30
ETA_COMP = 0.85
HORAS_ANUALES = 8000
VIDA_PROYECTO = 20
CONST_WEYMOUTH = 433.5
E_HID = 1.0

# ------------------------------------------------------------
# FUNCIONES
# ------------------------------------------------------------
def crf(tasa, n=VIDA_PROYECTO):
    return 1.0/n if tasa==0 else tasa*(1+tasa)**n/((1+tasa)**n-1)

def maop_barlow(SMYS_psi, t_mm, D_ext_mm, F):
    t_in = t_mm/25.4
    D_in = D_ext_mm/25.4
    return 2*SMYS_psi*t_in*F/D_in

def caida_presion_weymouth(P1, Q, L_mi, D_in):
    term = CONST_WEYMOUTH * (Q/E_HID)**2 * (L_mi * GAMMA * T_SUC_R * Z) / (D_in**5.33)
    P2_cuad = P1**2 - term
    return np.sqrt(P2_cuad) if P2_cuad > 0 else None

def potencia_compresor_simple(Q, P_suc, P_desc, T_R, Z, k, eta):
    """Fórmula empírica estándar (da resultados correctos)"""
    if P_desc <= P_suc:
        return 0.0
    rp = P_desc / P_suc
    # Constante 0.0857 proviene de: (1e6)/(24*3600) * (R_univ * 144/550) con R=10.731
    HP = 0.0857 * Q * T_R * Z * (k/(k-1)) * (rp**((k-1)/k) - 1) / eta
    return max(0, HP)

def temp_descarga(T_suc_R, P_suc, P_desc, k):
    T2_R = T_suc_R * (P_desc/P_suc)**((k-1)/k)
    return (T2_R - 491.67) * 5/9

def encontrar_pdesc_necesaria(Q, D_in, N_est):
    L_seg_mi = (L_TOTAL_KM * 0.621371) / N_est
    L_seg_km = L_TOTAL_KM / N_est

    def presion_final(P_desc):
        P = P_RECEPCION
        for _ in range(N_est):
            P = caida_presion_weymouth(P_desc, Q, L_seg_mi, D_in)  # comprime y luego cae
            if P is None:
                return -1
        return P

    # Búsqueda binaria de P_desc mínima que da P_final >= 500
    low, high = P_RECEPCION, 2000.0
    if presion_final(high) < P_MIN_ENTREGA:
        return None, None, None, None, None, None
    for _ in range(50):
        mid = (low+high)/2
        if presion_final(mid) < P_MIN_ENTREGA:
            low = mid
        else:
            high = mid
    P_desc_opt = high

    # Reconstruir perfil
    distancias, presiones = [0.0], [P_RECEPCION]
    potencias = []
    temp_max = 0.0
    P_actual = P_RECEPCION
    for i in range(N_est):
        T_desc_C = temp_descarga(T_SUC_R, P_actual, P_desc_opt, K)
        temp_max = max(temp_max, T_desc_C)
        HP = potencia_compresor_simple(Q, P_actual, P_desc_opt, T_SUC_R, Z, K, ETA_COMP)
        potencias.append(HP)
        distancias.append(distancias[-1])
        presiones.append(P_desc_opt)
        # Puntos intermedios en el tramo
        for frac in np.linspace(0.05, 1, 20):
            L_parcial_mi = frac * L_seg_mi
            dist_km = distancias[-1] + frac * L_seg_km
            P_inter = caida_presion_weymouth(P_desc_opt, Q, L_parcial_mi, D_in)
            if P_inter is None:
                P_inter = 0
            distancias.append(dist_km)
            presiones.append(P_inter)
        P_actual = presiones[-1]
    return P_desc_opt, presiones[-1], distancias, presiones, potencias, temp_max

# ------------------------------------------------------------
# BARRA LATERAL (derecha)
# ------------------------------------------------------------
with st.sidebar:
    st.markdown("## ⚙️ Parámetros de diseño")
    with st.expander("💰 Económicos", expanded=True):
        costo_energia = st.number_input("Costo energía (USD/kWh)", 0.01, 0.50, 0.05, 0.01)
        costo_acero = st.number_input("Costo acero (USD/m)", 100, 1000, 350, 10)
        tasa_interes = st.number_input("Tasa interés (%)", 1, 20, 8)/100.0
        costo_comp_HP = st.number_input("Costo compresor (USD/HP)", 800, 2000, 1200, 100)
    with st.expander("🛠️ Materiales", expanded=True):
        diametro = st.selectbox("Diámetro", list(TUBERIAS.keys()))
        acero = st.selectbox("Grado acero", list(ACEROS.keys()))
    with st.expander("🌡️ Operación", expanded=True):
        Q_input = st.number_input("Flujo Q (MMscfd)", 100, 1500, 500, 50)
        N_est = st.slider("Estaciones de compresión", 1, 6, 3, 1)  # valor inicial 3
    if st.button("🔍 Optimizar (mínimo TAC)", type="primary"):
        st.session_state.optimizar = True
    else:
        st.session_state.optimizar = False

# ------------------------------------------------------------
# CÁLCULOS
# ------------------------------------------------------------
dat_tubo = TUBERIAS[diametro]
dat_ac = ACEROS[acero]
D_ext = dat_tubo["D_ext_mm"]
t = dat_tubo["t_mm"]
D_in = (D_ext - 2*t)/25.4
MAOP = maop_barlow(dat_ac["SMYS_psi"], t, D_ext, dat_ac["F"])

res = encontrar_pdesc_necesaria(Q_input, D_in, N_est)
if res[0] is None:
    st.error("❌ Diseño inviable. Aumente diámetro o estaciones.")
    st.stop()

P_desc, P_final, dist, pres, pots, T_max = res
HP_total = sum(pots)

costo_ducto = costo_acero * L_TOTAL_KM * 1000
costo_comp = HP_total * costo_comp_HP
CAPEX = costo_ducto + costo_comp
CRF_val = crf(tasa_interes)
OPEX = HP_total * 0.7457 * HORAS_ANUALES * costo_energia
TAC = CAPEX * CRF_val + OPEX

# Optimizador
if st.session_state.optimizar:
    best = {}
    best_tac = float('inf')
    for dnom in TUBERIAS:
        d_ext_o = TUBERIAS[dnom]["D_ext_mm"]
        t_o = TUBERIAS[dnom]["t_mm"]
        d_in_o = (d_ext_o - 2*t_o)/25.4
        for n in range(1,7):
            r = encontrar_pdesc_necesaria(Q_input, d_in_o, n)
            if r[0] is None: continue
            _, pf, _, _, pots_o, tmax_o = r
            if pf < P_MIN_ENTREGA or tmax_o > 65: continue
            hp_o = sum(pots_o)
            cd_o = costo_acero * L_TOTAL_KM * 1000
            cc_o = hp_o * costo_comp_HP
            tac_o = (cd_o+cc_o)*crf(tasa_interes) + hp_o*0.7457*HORAS_ANUALES*costo_energia
            if tac_o < best_tac:
                best_tac = tac_o
                best = {"D": dnom, "N": n, "TAC": tac_o, "HP": hp_o}
    if best:
        st.success(f"✅ Óptimo: {best['D']}, N={best['N']} → TAC ${best['TAC']:,.0f}/año, HP={best['HP']:,.0f}")

# ------------------------------------------------------------
# DASHBOARD
# ------------------------------------------------------------
st.markdown("## 📈 Resultados Clave")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("💰 TAC (USD/año)", f"${TAC:,.0f}")
    st.markdown('</div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("⚙️ Potencia instalada", f"{HP_total:,.0f} HP")
    st.markdown('</div>', unsafe_allow_html=True)
with col3:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("📉 Presión final", f"{P_final:.1f} psia")
    st.markdown('</div>', unsafe_allow_html=True)

# Gráfico
st.markdown("## 📉 Perfil de Presión vs Distancia")
fig = go.Figure()
fig.add_trace(go.Scatter(x=dist, y=pres, mode='lines', name='Presión', line=dict(color='#00aaff', width=3)))
fig.add_hline(y=P_MIN_ENTREGA, line_dash="dash", line_color="#ff5555", annotation_text="Mín entrega (500 psia)")
fig.add_hline(y=MAOP, line_dash="dash", line_color="#ffaa00", annotation_text=f"MAOP ({MAOP:.0f} psia)")
fig.add_hline(y=P_RECEPCION, line_dash="dot", line_color="#88cc88", annotation_text="Presión recepción")
fig.update_layout(template="plotly_dark", height=450, xaxis_title="Distancia (km)", yaxis_title="Presión (psia)")
st.plotly_chart(fig, use_container_width=True)

# Desglose de costos
st.markdown("## 💰 Desglose del TAC")
df_cost = pd.DataFrame({
    "Concepto": ["CAPEX Tubería", "CAPEX Compresores", "OPEX Energía"],
    "Monto": [costo_ducto*CRF_val, costo_comp*CRF_val, OPEX]
})
fig_c = px.bar(df_cost, x="Concepto", y="Monto", text="Monto", color="Concepto")
fig_c.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
fig_c.update_layout(template="plotly_dark", height=380)
st.plotly_chart(fig_c, use_container_width=True)

# Validaciones
st.markdown("## ✅ Validaciones de Seguridad")
c1, c2 = st.columns(2)
with c1:
    st.success(f"✅ MAOP OK: {P_RECEPCION} ≤ {MAOP:.0f} psia") if P_RECEPCION<=MAOP else st.error("⛔ MAOP superado")
    st.success(f"✅ Temperatura OK: {T_max:.1f}°C ≤ 65°C") if T_max<=65 else st.error("⛔ Temperatura excede 65°C")
with c2:
    st.success(f"✅ Entrega OK: {P_final:.1f} ≥ 500 psia") if P_final>=500 else st.error("⛔ Presión final insuficiente")

# Detalles técnicos
with st.expander("📐 Detalles técnicos"):
    st.write(f"**Diámetro interno:** {D_in:.3f} in | **Espesor:** {t/25.4:.3f} in")
    st.write(f"**MAOP:** {MAOP:.0f} psia | **Peso molecular gas:** {GAMMA*28.97:.2f} lb/lbmol")
    st.write(f"**Presión de descarga:** {P_desc:.1f} psia | **Potencia por estación:** {', '.join([f'{hp:.0f}' for hp in pots])} HP")

st.markdown("---")
st.markdown("<p style='text-align:center; color:#666;'>Proyecto Optimización de Procesos | Gasoducto Trans-Andino | 2026</p>", unsafe_allow_html=True)
