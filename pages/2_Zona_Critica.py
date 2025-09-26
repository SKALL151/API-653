import streamlit as st
from decimal import Decimal, ROUND_HALF_UP, getcontext

st.set_page_config(page_title="Fondo (Suelo) - API 653", page_icon="🛢️", layout="wide")

# Guard: si la portada no se ha mostrado en esta sesión, regresar a Portada
if not st.session_state.get("saw_home", False):
    st.switch_page("API_653.py")

CARD_BG = "rgba(11, 19, 43, 0.25)"
st.markdown(f"""
<style>
.block-container {{ padding-top: 0.8rem !important; }}
.section-card {{ background: rgba(148,163,184,0.08); border: 1px solid #334155; border-radius: 10px; padding: 0.8rem 1rem; margin-bottom: 0.8rem; }}
.result-card {{ background: {CARD_BG}; border: 1px solid #334155; border-radius: 10px; padding: 1rem 1.2rem; margin-bottom: 0.8rem; }}
.result-title {{ font-weight:700; font-size: 0.95rem; margin-bottom:0.35rem; }}
.result-value {{ font-size: 1.35rem; font-weight: 800; }}
.mm-text {{ font-size: 0.8em; color: #E2E8F0; margin-left: 4px; }}
.badge-ok {{ background: #14532D; color: #86EFAC; border: 1px solid #22C55E; padding: 0.15rem 0.5rem; border-radius: 6px; font-weight: 700; }}
.badge-no {{ background: #450A0A; color: #FCA5A5; border: 1px solid #F87171; padding: 0.15rem 0.5rem; border-radius: 6px; font-weight: 700; }}
.result-sub {{ font-size: 0.8rem; color: #CBD5E1; margin-bottom: 0.25rem; }}
.small-help {{ font-size: 0.85rem; color: #94A3B8; }}
</style>
""", unsafe_allow_html=True)

def q3(x): return Decimal(str(x)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
def in_to_mm(v): return q3(Decimal(v) * Decimal("25.4"))
def mm_to_in(v): return q3(Decimal(v) / Decimal("25.4"))

FT_PER_M = Decimal("3.280839895")
def m_to_ft(v): return q3(Decimal(v) * FT_PER_M)
def ft_to_m(v): return q3(Decimal(v) / FT_PER_M)

DEFAULTS = {
    "C2": 2025, "C4": 2006, "C6": 2006, "C17": 10,
    "I2": 41.38, "I4": 53.47, "I8": 24900.0, "I12": 1.0,
    "C9": 0.3125, "C12": 0.3125
}
for k,v in DEFAULTS.items():
    if k not in st.session_state: st.session_state[k] = v

if "unit_mode" not in st.session_state: st.session_state["unit_mode"] = "in"
if "tuvo_insp_prev" not in st.session_state: st.session_state["tuvo_insp_prev"] = True
if "C9_src" not in st.session_state: st.session_state["C9_src"] = float(st.session_state.get("C9", 0.3125))
if "C12_src" not in st.session_state: st.session_state["C12_src"] = float(st.session_state.get("C12", 0.3125))
if "ring_len_unit" not in st.session_state: st.session_state["ring_len_unit"] = "ft"

# Catálogo GE
GE_OPTIONS = {
    "Agua": 1.00, "Gasolina (nafta)": 0.75, "Kerosene (Jet Fuel)": 0.80,
    "Diésel": 0.84, "Aceite lubricante (mineral)": 0.89, "Petróleo crudo ligero": 0.84,
    "Petróleo crudo pesado": 0.93, "GLP (propano–butano líquido)": 0.54,
    "Etanol": 0.79, "Metanol": 0.80, "Personalizada": None
}

# Catálogo de tensión admisible (psi)
SIGMA_ALLOW = {
    "Desconocido": 23600,
    "A 283–C": 23600, "A285–C": 23600, "A36": 24900, "A131–A,B,CS": 24900, "A131–EH36": 30500,
    "A573–58": 24900, "A573–65": 27900, "A573–70": 30000,
    "A516–55": 23600, "A516–60": 25600, "A516–65": 27900, "A516–70": 30000,
    "A662–B": 29000, "A662–C": 30000,
    "A537–Cl1": 30000, "A537–Cl2": 34300, "A633–C,D": 30000, "A678–A": 30000, "A678–B": 30000,
    "A737–B": 30000, "A841": 30000, "A10": 23600, "A7": 25700,
    "A442–55": 23600, "A442–60": 25600, "G40.21–38W": 25700, "G40.21–44W": 27900,
    "G40.21–44WT": 27400, "G40.21–50W": 27900, "G40.21–50WT": 30000,
    "Personalizado": -1
}

def fila_P(C2, C4, C6, C9, C12, L4):
    C2,C4,C6,C9,C12,L4 = map(Decimal,[C2,C4,C6,C9,C12,L4])
    P1 = (C12 - C9)/(C6 - C4)*1000 if (C6-C4)!=0 else Decimal("0")
    P2 = (C9 - L4)/(C2 - C6)*1000 if (C2-C6)!=0 else Decimal("0")
    P3 = (C12 - L4)/(C2 - C4)*1000 if (C2-C4)!=0 else Decimal("0")
    return P1,P2,P3,max(P1,P2,P3,Decimal("0"))

def calcular_L4_iterativo_objetivo(C2, C4, C6, C9, C12, C15, C17):
    target_q, lo, hi, step = q3(C15), Decimal("0.0"), Decimal(str(C12)), Decimal("0.0001")
    L4_val, last_ok = hi, None
    for _ in range(int((hi-lo)/step)+2):
        _,_,_,L2_iter = fila_P(C2,C4,C6,C9,C12,L4_val)
        P12i_q = q3(L4_val - (L2_iter/1000*Decimal(C17)))
        if P12i_q >= target_q:
            last_ok, L4_val = L4_val, L4_val - step
            if L4_val < lo: break
        else: break
    return last_ok if last_ok is not None else L4_val

st.title("Zona crítica")
left, right = st.columns([1,1.1], gap="large")

with left:
    tab_fechas, tab_tmin, tab_datos = st.tabs(["Fechas", "Cálculo Tmin primer anillo", "Datos"])

    # Fechas
    with tab_fechas:
        c1,c2 = st.columns(2)
        C2 = c1.number_input("Año de inspección", 1900, 2100, value=int(st.session_state["C2"]), key="C2")
        C4 = c2.number_input("Año de construcción", 1900, 2100, value=int(st.session_state["C4"]), key="C4")
        c3,c4 = st.columns(2)
        C6 = c3.number_input("Fecha última inspección interna", 1900, 2100, value=int(st.session_state["C6"]), key="C6")
        C17 = c4.number_input("Plazo próxima inspección (años)", 0, 50, value=int(st.session_state["C17"]), key="C17")

    # Cálculo Tmin primer anillo
    with tab_tmin:
        uc1, uc2 = st.columns([1,1])
        ring_unit = uc1.selectbox("Unidad de longitud", ["ft","m"], index=0 if st.session_state["ring_len_unit"]=="ft" else 1, key="ring_len_unit")

        if ring_unit == "ft":
            I2_in = st.number_input("Altura máxima de llenado (ft)", 0.0, value=float(st.session_state["I2"]), format="%.3f", key="I2")
            I4_in = st.number_input("Diámetro del tanque (ft)", 0.0, value=float(st.session_state["I4"]), format="%.3f", key="I4")
            altura_ft = Decimal(str(I2_in)); diam_ft = Decimal(str(I4_in))
        else:
            I2_m = st.number_input("Altura máxima de llenado (m)", 0.0, value=float(ft_to_m(st.session_state["I2"])), format="%.3f", key="I2_m")
            I4_m = st.number_input("Diámetro del tanque (m)", 0.0, value=float(ft_to_m(st.session_state["I4"])), format="%.3f", key="I4_m")
            altura_ft = m_to_ft(Decimal(str(I2_m))); diam_ft = m_to_ft(Decimal(str(I4_m)))

        # Gravedad específica
        gcol1, gcol2 = st.columns([1,1])
        ge_choice = gcol1.selectbox("Producto (gravedad específica)", list(GE_OPTIONS.keys()), index=list(GE_OPTIONS.keys()).index("Agua"))
        ge_from_list = GE_OPTIONS[ge_choice]
        if ge_from_list is None:
            GE_val = gcol2.number_input("Gravedad específica (valor)", 0.0, 2.0, value=float(st.session_state.get("I6", 0.85)), format="%.3f", key="I6_custom")
        else:
            GE_val = ge_from_list
            gcol2.number_input("Gravedad específica (valor)", 0.0, 2.0, value=float(GE_val), format="%.3f", disabled=True, key="I6_display")

        # Tensión admisible
        scol1, scol2 = st.columns([1,1])
        sigma_choice = scol1.selectbox("Material (tensión admisible)", list(SIGMA_ALLOW.keys()), index=0)
        sigma_sel = SIGMA_ALLOW[sigma_choice]
        if sigma_sel is None:
            I8_val = float(st.session_state.get("I8", 23600.0))
            scol2.number_input("Tensión admisible (psi)", min_value=0.0, value=I8_val, format="%.0f", disabled=True, key="I8_unknown")
            st.caption("Material desconocido: use el valor por defecto o seleccione 'Personalizado' para editar.")
        elif sigma_sel == -1:
            I8_val = scol2.number_input("Tensión admisible (psi)", min_value=0.0, value=float(st.session_state.get("I8", 24900.0)), format="%.0f", key="I8_custom")
        else:
            I8_val = float(sigma_sel)
            scol2.number_input("Tensión admisible (psi)", min_value=0.0, value=I8_val, format="%.0f", disabled=True, key="I8_catalog")

        I12 = st.number_input("Eficiencia de la junta", 0.0, 1.0, value=float(st.session_state["I12"]), key="I12")

        tmin_primer_anillo = q3((Decimal("2.6")*(altura_ft-Decimal("1"))*diam_ft*Decimal(GE_val))/(Decimal(I8_val)*Decimal(I12)))
        if tmin_primer_anillo < Decimal("0.1"): tmin_primer_anillo = Decimal("0.1")

        st.markdown(
            f"<div class='section-card'><b>Tmin primer anillo</b>: {tmin_primer_anillo:.3f} in "
            f"<span class='mm-text'>({in_to_mm(tmin_primer_anillo):.3f} mm)</span></div>",
            unsafe_allow_html=True
        )

    # Datos
    with tab_datos:
        b1,b2 = st.columns(2)
        prev = b1.radio("¿Tuvo inspecciones anteriores?", ["Sí","No"], index=0 if st.session_state["tuvo_insp_prev"] else 1, key="tuvo_insp_prev_radio")
        st.session_state["tuvo_insp_prev"] = (prev == "Sí")
        unit = b2.selectbox("Unidad de espesor", ["in","mm"], index=0 if st.session_state.get("unit_mode","in")=="in" else 1, key="unit_mode")

        lbl_tmin = "tmin última inspección (in)" if unit=="in" else "tmin última inspección (mm)"
        lbl_tnom = "t nominal fondo (in)" if unit=="in" else "t nominal fondo (mm)"

        if st.session_state["tuvo_insp_prev"]:
            if unit=="in":
                C12_in = st.number_input(lbl_tmin, min_value=0.0, format="%.4f", value=float(st.session_state["C12_src"]), key="C12_src")
            else:
                C12_mm = st.number_input(lbl_tmin, min_value=0.0, format="%.3f", key="C12_src_mm")
                st.session_state["C12_src"] = float(mm_to_in(C12_mm)); C12_in = st.session_state["C12_src"]
            C12 = Decimal(str(C12_in)); C9 = Decimal(str(C12_in))
            st.session_state["C12"] = float(C12); st.session_state["C9"] = float(C9)
        else:
            if unit=="in":
                C9_in = st.number_input(lbl_tnom, min_value=0.0, format="%.4f", value=float(st.session_state["C9_src"]), key="C9_src")
            else:
                C9_mm = st.number_input(lbl_tnom, min_value=0.0, format="%.3f", key="C9_src_mm")
                st.session_state["C9_src"] = float(mm_to_in(C9_mm)); C9_in = st.session_state["C9_src"]
            C9 = Decimal(str(C9_in)); C12 = Decimal(str(C9_in))
            st.session_state["C9"] = float(C9); st.session_state["C12"] = float(C12)

        # tmin requerido (derivado)
        half = q3(tmin_primer_anillo*Decimal("0.5"))
        if half < Decimal("0.118"):
            tmp = q3(tmin_primer_anillo*Decimal("0.5"))
            tmin_requerido = tmp if tmp > Decimal("0.1") else Decimal("0.1")
        else:
            tmin_requerido = Decimal("0.118")

        st.markdown(
            f"<div class='section-card'><b>tmin requerido (cálculo)</b>: {tmin_requerido:.3f} in "
            f"<span class='mm-text'>({in_to_mm(tmin_requerido):.3f} mm)</span></div>",
            unsafe_allow_html=True
        )

    st.divider()
    col1,col2 = st.columns(2)
    calcular = col1.button("Calcular", use_container_width=True)
    if col2.button("🧹 Limpiar", type="secondary", use_container_width=True):
        st.session_state.clear()
        for k,v in DEFAULTS.items(): st.session_state[k] = v
        st.rerun()

with right:
    st.markdown("### Resultados")
    if calcular:
        if C2 <= C6 or C6 < C4 or st.session_state.get("C9",0)<=0 or st.session_state.get("C12",0)<=0 or tmin_requerido<=0:
            st.error("Revisa los datos: años y espesores deben ser válidos.")
        else:
            C2d, C4d, C6d = Decimal(str(C2)), Decimal(str(C4)), Decimal(str(C6))
            C9d, C12d = Decimal(str(st.session_state["C9"])), Decimal(str(st.session_state["C12"]))
            C17d, C15d = Decimal(str(C17)), Decimal(str(tmin_requerido))

            L4 = calcular_L4_iterativo_objetivo(C2d,C4d,C6d,C9d,C12d,C15d,C17d)
            P1,P2,P3,L2 = fila_P(C2d,C4d,C6d,C9d,C12d,L4)
            P6 = q3((L2/1000*C17d) + C15d)
            P12_q = q3(Decimal(L4) - (L2/1000*C17d))
            cum_text = "CUMPLE" if P12_q >= q3(C15d) else "NO CUMPLE"
            porc_Cscan = q3(Decimal(100) - (Decimal(L4)*Decimal(100)/C12d))
            porc_MFL = q3(porc_Cscan - Decimal(10))

            st.markdown(f"<div class='result-card'><div class='result-title'>Tasa de corrosión</div><div class='result-value'>{q3(L2):.3f} mpy</div></div>", unsafe_allow_html=True)
            m1,m2,m3 = st.columns(3)
            m1.markdown(f"<div class='result-card'><div class='result-title'>Tmin antes de parche</div><div class='result-value'>{P6:.3f} in <span class='mm-text'>({in_to_mm(P6):.2f} mm)</span></div></div>", unsafe_allow_html=True)
            m2.markdown(f"<div class='result-card'><div class='result-title'>Espesor esperado a {int(C17)} años </div><div class='result-value'>{P12_q:.3f} in <span class='mm-text'>({in_to_mm(P12_q):.2f} mm)</span></div></div>", unsafe_allow_html=True)
            m3.markdown(
                f"<div class='result-card'><div class='result-title'>Veredicto</div>"
                f"<div class='result-value'>{cum_text} "
                f"{'<span class=\"badge-ok\">OK</span>' if cum_text=='CUMPLE' else '<span class=\"badge-no\">ALERTA</span>'}"
                f"</div></div>",
                unsafe_allow_html=True
            )

            st.markdown("#### Detalle de pérdidas y tasas")
            d1,d2 = st.columns(2)
            d1.markdown(f"<div class='result-card'><div class='result-title'>Porcentaje de pérdida C-Scan (Aparchar)</div><div class='result-value'>{porc_Cscan:.0f} %</div></div>", unsafe_allow_html=True)
            d1.markdown(f"<div class='result-card'><div class='result-title'>Porcentaje de pérdida para validar MFL</div><div class='result-value'>{porc_MFL:.0f} %</div></div>", unsafe_allow_html=True)
            d2.markdown(f"<div class='result-card'><div class='result-title'>Componentes P</div><div class='result-sub'>P1: Últ. insp. → Construcción<br/>P2: Últ. insp. → Insp. actual<br/>P3: Construcción → Insp. actual</div><div class='result-value'>{P1:.3f} | {P2:.3f} | {P3:.3f} mpy</div></div>", unsafe_allow_html=True)
