# app.py - Versión corregida (ecuaciones exactas del PDF)
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ------------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA Y ESTILOS (sidebar a la derecha)
# ------------------------------------------------------------
st.set_page_config(page_title="🛢️ Gasoducto", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    section[data-testid="stSidebar"] {
        order: 2;
        min-width: 380px !important;
        width: 380px !important;
        background-color: #14161c;
        border-left: 1px solid #2c3e50;
        border-right: none;
    }
    .main > div { order: 1; }
    .stApp { background-color: #0a0c10; }
    .stMarkdown, .stText, .stNumberInput label, .stSelectbox label, 
    .stSlider label, .stMetric label { color: #ffffff !important; }
    .main-title {
        font-family: 'Arial Black', sans-serif;
        font-size: 2.8rem;
        text-align: center;
        color: #00aaff;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        text-align: center;
        color: #cccccc;
        font-size: 1rem;
        margin-top: 0;
    }
    .metric-card {
        background-color: #1e1e2a;
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.6);
        text-align: center;
        border-top: 4px solid #00aaff;
    }
    h1, h2, h3 { color: #00aaff !important; font-weight: 600; }
    hr { border-color: #2c3e50; }
    .help-text {
        font-size: 0.75rem;
        color: #88aacc !important;
        margin-top: -8px;
        margin-bottom: 12px;
        font-style: italic;
    }
    .recommendation-box {
        background-color: #1a222a;
        border-left: 4px solid #ffaa00;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        color: #ffffff;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🛢️ GASODUCTO TRANS-ANDINO</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">| Gemelo Digital | Simulación hidráulica & optimización económica/div>', unsafe_allow_html=True)
st.markdown("---")

# ------------------------------------------------------------
# BASE DE DATOS TÉCNICA (PDF)
# ------------------------------------------------------------
TUBERIAS = {
    "12 pulgadas": {"D_ext_mm": 323.8, "t_mm": 10.31, "costo_base": 185},
    "16 pulgadas": {"D_ext_mm": 406.4, "t_mm": 12.70, "costo_base": 260},
    "20 pulgadas": {"D_ext_mm": 508.0, "t_mm": 15.09, "costo_base": 350},
    "24 pulgadas": {"D_ext_mm": 609.6, "t_mm": 17.48, "costo_base": 440}
}

ACEROS = {
    "X52": {"SMYS_psi": 52000, "F": 0.72},
    "X60": {"SMYS_psi": 60000, "F": 0.72}
}

# ------------------------------------------------------------
# PARÁMETROS FÍSICOS (caso base del PDF)
# ------------------------------------------------------------
L_TOTAL_KM = 400.0
P_RECEPCION = 800.0          # psia
P_MIN_ENTREGA = 500.0        # psia
T_SUC_C = 20.0
T_SUC_R = (T_SUC_C + 273.15) * 9/5   # Rankine
GAMMA = 0.65
Z = 0.90
K = 1.30
ETA_COMP = 0.85              # eficiencia del compresor
HORAS_ANUALES = 8000
VIDA_PROYECTO = 20
CONST_WEYMOUTH = 433.5        # constante de la ecuación de Weymouth (PDF)
E_HID = 1.0                   # eficiencia de la tubería (se asume 1.0)
R_UNIV = 10.731               # psia·ft³/(lbmol·°R) - constante universal

# ------------------------------------------------------------
# FUNCIONES SEGÚN EL ENUNCIADO
# ------------------------------------------------------------
def crf(tasa, n=VIDA_PROYECTO):
    """Factor de recuperación de capital (anualización)"""
    return 1.0 / n if tasa == 0 else tasa * (1 + tasa)**n / ((1 + tasa)**n - 1)

def maop_barlow(SMYS_psi, t_mm, D_ext_mm, F):
    """Presión máxima admisible (Barlow) - psia"""
    t_in = t_mm / 25.4
    D_in = D_ext_mm / 25.4
    return 2.0 * SMYS_psi * t_in * F / D_in

def caida_presion_weymouth(P1, Q, L_mi, D_in):
    """
    Ecuación de Weymouth (PDF)
    P1^2 - P2^2 = 433.5 * (Q/E)^2 * (L * γ * T * Z) / D^5.33
    Retorna P2 en psia, o None si es imposible.
    """
    term = CONST_WEYMOUTH * (Q / E_HID)**2 * (L_mi * GAMMA * T_SUC_R * Z) / (D_in**5.33)
    P2_cuad = P1**2 - term
    return np.sqrt(P2_cuad) if P2_cuad > 0 else None

def potencia_compresor(Q, P_suc, P_desc, T_suc_R, Z_val, k, eta):
    """
    Ecuación de potencia del PDF:
    HP = (Q * 1e6)/(24*3600*η) * (Z R T1)/(k-1) * [ (P_out/P_in)^((k-1)/k) - 1 ]
    Con R = 10.731 psia·ft³/(lbmol·°R)
    """
    if P_suc <= 0 or P_desc <= P_suc:
        return 0.0
    rp = P_desc / P_suc
    Q_scf_s = Q * 1e6 / (24 * 3600)          # scf/s
    term = (Z_val * R_UNIV * T_suc_R) / (k - 1)
    factor = (rp ** ((k-1)/k) - 1)
    # Potencia en (psia * ft³/s)
    potencia_psia_ft3_s = Q_scf_s * term * factor / eta
    # Convertir a HP: 1 psia = 144 lbf/ft², 1 HP = 550 ft·lbf/s
    HP = potencia_psia_ft3_s * 144 / 550
    return max(0, HP)

def temp_descarga(T_suc_R, P_suc, P_desc, k):
    """Ecuación de temperatura de descarga (PDF)"""
    T2_R = T_suc_R * (P_desc / P_suc) ** ((k-1)/k)
    return (T2_R - 491.67) * 5/9   # convertir a Celsius

def encontrar_pdesc_necesaria(Q, D_in, N_est):
    """
    Determina la presión de descarga (P_desc) que cumple que la presión final
    después de N_est segmentos sea al menos P_MIN_ENTREGA.
    Retorna (P_desc, P_final, distancias, presiones, potencias, T_max_C)
    """
    L_seg_mi = (L_TOTAL_KM * 0.621371) / N_est   # millas por segmento
    L_seg_km = L_TOTAL_KM / N_est

    # Función que calcula la presión final dado un P_desc (modelo correcto)
    def presion_final(P_desc):
        P_suc = P_RECEPCION
        for _ in range(N_est):
            # Comprimir desde P_suc hasta P_desc
            P_after_comp = P_desc
            # Caída en el tramo
            P_suc = caida_presion_weymouth(P_after_comp, Q, L_seg_mi, D_in)
            if P_suc is None:
                return -1.0
        return P_suc

    # Búsqueda binaria de la P_desc mínima que cumple presión final >= 500 psia
    low = P_RECEPCION
    high = 2000.0   # límite superior razonable
    if presion_final(high) < P_MIN_ENTREGA:
        return None, None, None, None, None, None  # inviable

    for _ in range(50):
        mid = (low + high) / 2
        if presion_final(mid) < P_MIN_ENTREGA:
            low = mid
        else:
            high = mid
    P_desc_opt = high

    # Reconstrucción del perfil completo (para gráfico y potencias)
    distancias = [0.0]
    presiones = [P_RECEPCION]
    potencias = []
    temp_max = 0.0
    P_actual = P_RECEPCION

    for i in range(N_est):
        P_desc = P_desc_opt
        T_desc_C = temp_descarga(T_SUC_R, P_actual, P_desc, K)
        temp_max = max(temp_max, T_desc_C)
        HP = potencia_compresor(Q, P_actual, P_desc, T_SUC_R, Z, K, ETA_COMP)
        potencias.append(HP)
        # Punto de salida del compresor (misma distancia, presión elevada)
        distancias.append(distancias[-1])
        presiones.append(P_desc)
        # Tramo de tubería: varios puntos para la curva
        num_puntos = 30
        for j in range(1, num_puntos + 1):
            frac = j / num_puntos
            L_parcial_mi = frac * L_seg_mi
            dist_km = distancias[-1] + frac * L_seg_km
            P_inter = caida_presion_weymouth(P_desc, Q, L_parcial_mi, D_in)
            if P_inter is None:
                P_inter = 0.0
            distancias.append(dist_km)
            presiones.append(P_inter)
        # Actualizar presión de succión para la siguiente etapa
        P_actual = presiones[-1]

    P_final_real = presiones[-1]
    return P_desc_opt, P_final_real, distancias, presiones, potencias, temp_max

# ------------------------------------------------------------
# BARRA LATERAL (derecha) - igual a la tuya
# ------------------------------------------------------------
with st.sidebar:
    st.markdown("## ⚙️ Parámetros de diseño")
    st.markdown("---")
    
    with st.expander("💰 Económicos", expanded=True):
        costo_energia = st.number_input("Costo de energía (USD/kWh)", 0.01, 0.50, 0.05, 0.01)
        st.markdown('<div class="help-text">💡 Afecta directamente el OPEX (costo operativo anual). A mayor costo, mayor TAC.</div>', unsafe_allow_html=True)
        
        costo_acero_usd_m = st.number_input("Costo del acero (USD/m)", 100.0, 1000.0, 350.0, 10.0)
        st.markdown('<div class="help-text">💡 Impacta el CAPEX de la tubería. A mayor costo, mayor inversión inicial.</div>', unsafe_allow_html=True)
        
        tasa_interes = st.number_input("Tasa de interés (%)", 1.0, 20.0, 8.0) / 100.0
        st.markdown('<div class="help-text">💡 Usada en el factor CRF. Tasas altas aumentan el costo anualizado del CAPEX.</div>', unsafe_allow_html=True)
        
        costo_comp_por_HP = st.number_input("Costo compresor (USD/HP)", 800, 2000, 1200, 100)
        st.markdown('<div class="help-text">💡 Influye en el CAPEX de los compresores. Mayor valor → mayor TAC.</div>', unsafe_allow_html=True)
    
    with st.expander("🛠️ Materiales", expanded=True):
        diametro_sel = st.selectbox("Diámetro comercial", list(TUBERIAS.keys()))
        st.markdown('<div class="help-text">💡 Diámetros mayores reducen la caída de presión y la potencia necesaria, pero aumentan el CAPEX de tubería.</div>', unsafe_allow_html=True)
        
        acero_sel = st.selectbox("Grado del acero", list(ACEROS.keys()))
        st.markdown('<div class="help-text">💡 X60 permite mayor MAOP (presión máxima segura) que X52.</div>', unsafe_allow_html=True)
    
    with st.expander("🌡️ Operación", expanded=True):
        Q_input = st.number_input("Flujo de gas Q (MMscfd)", 100.0, 1500.0, 500.0, 50.0)
        st.markdown('<div class="help-text">💡 Mayor flujo requiere más presión de descarga y más potencia. Aumenta TAC.</div>', unsafe_allow_html=True)
        
        N_est = st.slider("Estaciones de compresión (N)", 1, 6, 2, 1)
        st.markdown('<div class="help-text">💡 Más estaciones reduce la presión de descarga por etapa y la potencia total, pero aumenta el CAPEX en compresores.</div>', unsafe_allow_html=True)
    
    if st.button("🔍 Optimizar configuración (mínimo TAC)", type="primary"):
        st.session_state.run_optimizer = True
    else:
        st.session_state.run_optimizer = False

# ------------------------------------------------------------
# CÁLCULOS PRINCIPALES
# ------------------------------------------------------------
dat_tubo = TUBERIAS[diametro_sel]
dat_ac = ACEROS[acero_sel]
D_ext_mm = dat_tubo["D_ext_mm"]
t_mm = dat_tubo["t_mm"]
D_in = (D_ext_mm - 2*t_mm) / 25.4          # pulgadas
MAOP = maop_barlow(dat_ac["SMYS_psi"], t_mm, D_ext_mm, dat_ac["F"])

resultado = encontrar_pdesc_necesaria(Q_input, D_in, N_est)
if resultado[0] is None:
    st.error("❌ Diseño inviable: incluso con presión máxima de 2000 psia no se alcanza la presión de entrega. Aumente el diámetro o el número de estaciones.")
    st.stop()

P_desc_opt, P_final_real, distancias, presiones, potencias, T_max_C = resultado
HP_total = sum(potencias)

costo_ducto = costo_acero_usd_m * (L_TOTAL_KM * 1000)
costo_compresores = HP_total * costo_comp_por_HP
CAPEX = costo_ducto + costo_compresores
CRF_val = crf(tasa_interes)
OPEX = HP_total * 0.7457 * HORAS_ANUALES * costo_energia
TAC = CAPEX * CRF_val + OPEX

# ------------------------------------------------------------
# OPTIMIZADOR (corregido también)
# ------------------------------------------------------------
if st.session_state.run_optimizer:
    best_tac = float('inf')
    best_config = {}
    for dn_key in TUBERIAS.keys():
        d_ext = TUBERIAS[dn_key]["D_ext_mm"]
        t_mm_opt = TUBERIAS[dn_key]["t_mm"]
        d_in_opt = (d_ext - 2*t_mm_opt) / 25.4
        for n_opt in range(1, 7):
            res = encontrar_pdesc_necesaria(Q_input, d_in_opt, n_opt)
            if res[0] is None:
                continue
            _, pf, _, _, pots, tmax = res
            if pf < P_MIN_ENTREGA or tmax > 65:
                continue
            hp_tot = sum(pots)
            cd = costo_acero_usd_m * L_TOTAL_KM * 1000
            cc = hp_tot * costo_comp_por_HP
            tac_val = (cd + cc) * crf(tasa_interes) + hp_tot * 0.7457 * HORAS_ANUALES * costo_energia
            if tac_val < best_tac:
                best_tac = tac_val
                best_config = {"D": dn_key, "N": n_opt, "TAC": tac_val, "HP": hp_tot}
    if best_config:
        st.success(f"✅ Configuración óptima: Diámetro **{best_config['D']}**, **N={best_config['N']}** estaciones")
        st.info(f"💰 TAC mínimo: **${best_config['TAC']:,.0f}/año** | Potencia: **{best_config['HP']:,.0f} HP**")
    else:
        st.warning("No se encontró configuración factible con estos parámetros.")

# ------------------------------------------------------------
# DASHBOARD DE RESULTADOS (tarjetas)
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
    st.metric("📉 Presión final", f"{P_final_real:.1f} psia")
    st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------------------------
# PERFIL HIDRÁULICO
# ------------------------------------------------------------
st.markdown("## 📉 Perfil de Presión vs Distancia")
fig = go.Figure()
fig.add_trace(go.Scatter(x=distancias, y=presiones, mode='lines', name='Presión', line=dict(color='#00aaff', width=3)))
fig.add_hline(y=P_MIN_ENTREGA, line_dash="dash", line_color="#ff5555", annotation_text=f"Mín entrega ({P_MIN_ENTREGA} psia)")
fig.add_hline(y=MAOP, line_dash="dash", line_color="#ffaa00", annotation_text=f"MAOP ({MAOP:.0f} psia)")
fig.add_hline(y=P_RECEPCION, line_dash="dot", line_color="#88cc88", annotation_text="Presión recepción")
fig.update_layout(xaxis_title="Distancia (km)", yaxis_title="Presión (psia)", template="plotly_dark", height=450, margin=dict(l=0, r=0, t=30, b=0), font=dict(color="#ffffff"))
st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------
# DESGLOSE DE COSTOS
# ------------------------------------------------------------
st.markdown("## 💰 Desglose del Costo Anualizado (TAC)")
df_cost = pd.DataFrame({
    "Concepto": ["CAPEX Tubería", "CAPEX Compresores", "OPEX Energía"],
    "Monto (USD/año)": [costo_ducto * CRF_val, costo_compresores * CRF_val, OPEX]
})
fig_c = px.bar(df_cost, x="Concepto", y="Monto (USD/año)", text="Monto (USD/año)",
               color="Concepto", color_discrete_sequence=["#00aaff", "#ffaa00", "#44cc44"])
fig_c.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
fig_c.update_layout(template="plotly_dark", height=380, font=dict(color="#ffffff"), 
                    paper_bgcolor="#0a0c10", plot_bgcolor="#0a0c10", yaxis=dict(title="USD/año"))
st.plotly_chart(fig_c, use_container_width=True)

# ------------------------------------------------------------
# VALIDACIONES DE SEGURIDAD
# ------------------------------------------------------------
st.markdown("## ✅ Validaciones de Seguridad")
colA, colB = st.columns(2)
with colA:
    if P_RECEPCION > MAOP:
        st.error(f"⛔ MAOP superado: {P_RECEPCION} > {MAOP:.0f} psia")
    else:
        st.success(f"✅ MAOP OK: {P_RECEPCION} ≤ {MAOP:.0f} psia")
    if T_max_C > 65:
        st.error(f"⛔ Temperatura excede límite: {T_max_C:.1f}°C > 65°C")
    else:
        st.success(f"✅ Temperatura OK: {T_max_C:.1f}°C ≤ 65°C")
with colB:
    if P_final_real < P_MIN_ENTREGA:
        st.error(f"⛔ Presión final insuficiente: {P_final_real:.1f} < {P_MIN_ENTREGA} psia")
    else:
        st.success(f"✅ Entrega OK: {P_final_real:.1f} ≥ {P_MIN_ENTREGA} psia")

# Recomendaciones
recomendaciones = []
if P_final_real < P_MIN_ENTREGA:
    recomendaciones.append("🔹 Aumente el diámetro o el número de estaciones.")
if T_max_C > 65:
    recomendaciones.append("🔹 Reduzca la relación de compresión por etapa (aumente N) o añada enfriamiento.")
if P_RECEPCION > MAOP:
    recomendaciones.append("🔹 Cambie a un grado de acero superior (X60) o aumente el espesor de pared.")
if recomendaciones:
    st.markdown('<div class="recommendation-box"><strong>💡 Recomendaciones:</strong><br>' + "<br>".join(recomendaciones) + '</div>', unsafe_allow_html=True)

# Detalles técnicos
with st.expander("📐 Detalles técnicos y conversiones de unidades"):
    st.write(f"**Diámetro interno:** `{D_in:.3f} in` | **Espesor:** `{t_mm/25.4:.3f} in`")
    st.write(f"**MAOP (Barlow):** `{MAOP:.0f} psia` | **Peso molecular gas:** `{MW_GAS:.2f} lb/lbmol`")
    st.write(f"**Presión de descarga óptima:** `{P_desc_opt:.1f} psia`")
    st.write(f"**Potencia por estación:** " + ", ".join([f"{hp:.0f} HP" for hp in potencias]))

st.markdown("---")
st.markdown("<p style='text-align:center; color:#666;'>Proyecto Optimización de Procesos | Gemelo Digital Gasoducto Trans-Andino | 2026</p>", unsafe_allow_html=True)
