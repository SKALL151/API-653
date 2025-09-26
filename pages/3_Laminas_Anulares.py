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

# Tabla tmin (API 653 imagen)
TMAP_COL_BOUNDS = [24300, 27000, 29700, 32400]
TMAP_ROWS = [
    (Decimal("0.000"), Decimal("0.750"), [Decimal("0.170"), Decimal("0.200"), Decimal("0.230"), Decimal("0.300")]),
    (Decimal("0.750"), Decimal("1.000"), [Decimal("0.170"), Decimal("0.220"), Decimal("0.310"), Decimal("0.380")]),
    (Decimal("1.000"), Decimal("1.250"), [Decimal("0.170"), Decimal("0.260"), Decimal("0.380"), Decimal("0.430")]),
    (Decimal("1.250"), Decimal("1.500"), [Decimal("0.220"), Decimal("0.340"), Decimal("0.470"), Decimal("0.590")]),
    (Decimal("1.500"), Decimal("9.999"), [Decimal("0.270"), Decimal("0.400"), Decimal("0.530"), Decimal("0.680")]),
]  # [web:141][web:137]

def buscar_columna_por_esfuerzo(sigma: Decimal) -> int:
    for i, lim in enumerate(TMAP_COL_BOUNDS):
        if sigma < Decimal(lim): return i
    return len(TMAP_COL_BOUNDS) - 1

def buscar_fila_por_espesor_t1(t1: Decimal):
    for lo, hi, vals in TMAP_ROWS:
        if t1 <= Decimal("0.750") and hi == Decimal("0.750"): return (lo,hi,vals)
        if lo == Decimal("0.750") and t1 > lo and t1 <= hi: return (lo,hi,vals)
        if lo not in (Decimal("0.000"), Decimal("0.750")) and t1 > lo and t1 <= hi: return (lo,hi,vals)
    return TMAP_ROWS[-1]

def tmin_por_tabla(t1_in: Decimal, sigma_psi: Decimal) -> Decimal:
    lo,hi,vals = buscar_fila_por_espesor_t1(t1_in)
    col = buscar_columna_por_esfuerzo(sigma_psi)
    return vals[col]

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

# Defaults
DEFAULTS = {"C2": 2025, "C4": 2006, "C6": 2006, "C17": 10, "H_ft": 33.189, "D_ft": 44.63, "t1_in": 0.3125}
for k,v in DEFAULTS.items():
    if k not in st.session_state: st.session_state[k] = v

st.title("Láminas anulares")
left, right = st.columns([1,1.1], gap="large")

with left:
    tab_fechas, tab_calc, tab_datos = st.tabs(["Fechas", "Cálculo anular", "Datos"])

    # Fechas
    with tab_fechas:
        c1,c2 = st.columns(2)
        C2 = c1.number_input("Año de inspección", 1900, 2100, value=int(st.session_state["C2"]), key="C2")
        C4 = c2.number_input("Año de construcción", 1900, 2100, value=int(st.session_state["C4"]), key="C4")
        c3,c4 = st.columns(2)
        C6 = c3.number_input("Fecha última inspección interna", 1900, 2100, value=int(st.session_state["C6"]), key="C6")
        C17 = c4.number_input("Plazo próxima inspección (años)", 0, 50, value=int(st.session_state["C17"]), key="C17")

    # Cálculo anular con selector de unidades
    with tab_calc:
        ucA, ucB = st.columns(2)
        len_unit = ucA.selectbox("Unidad de altura/diámetro", ["ft","m"], index=0, key="len_unit")
        thick_unit = ucB.selectbox("Unidad de espesor Primer anillo", ["in","mm"], index=0, key="t1_unit")

        # Captura H y D en la unidad elegida y convertir a ft
        if len_unit == "ft":
            H_in = st.number_input("Altura máxima de llenado (ft)", min_value=0.0, value=float(st.session_state["H_ft"]), format="%.3f", key="H_ft_in")
            D_in = st.number_input("Diámetro del tanque", min_value=0.0, value=float(st.session_state["D_ft"]), format="%.3f", key="D_ft_in")
            H_ft = Decimal(str(H_in)); D_ft = Decimal(str(D_in))
        else:
            H_m = st.number_input("Altura máxima de llenado (m)", min_value=0.0, value=float(ft_to_m(st.session_state["H_ft"])), format="%.3f", key="H_m")
            D_m = st.number_input("Diámetro del tanque (m)", min_value=0.0, value=float(ft_to_m(st.session_state["D_ft"])), format="%.3f", key="D_m")
            H_ft = m_to_ft(Decimal(str(H_m))); D_ft = m_to_ft(Decimal(str(D_m)))

        # Captura t1 en la unidad elegida y convertir a in
        if thick_unit == "in":
            t1_val = st.number_input("Espesor primer Anillo (in)", min_value=0.001, value=float(st.session_state["t1_in"]), format="%.4f", key="t1_in_in")
            t1_in = Decimal(str(t1_val))
        else:
            t1_mm = st.number_input("Espesor primer curso (mm)", min_value=0.01, value=float(in_to_mm(st.session_state["t1_in"])), format="%.3f", key="t1_mm")
            t1_in = mm_to_in(Decimal(str(t1_mm)))

        sigma = q3(Decimal("2.34")*D_ft*(H_ft-Decimal("1"))/t1_in)
        st.markdown(f"<div class='section-card'><b>Esfuerzo primer curso</b>: {sigma:.3f} psi</div>", unsafe_allow_html=True)

        tmin_tabla = tmin_por_tabla(Decimal(str(t1_in)), sigma)
        st.markdown(
            f"<div class='section-card'><b>tmin por tabla</b>: {tmin_tabla:.3f} in "
            f"<span class='mm-text'>({in_to_mm(tmin_tabla):.3f} mm)</span></div>",
            unsafe_allow_html=True
        )

    # Datos de corrosión
    with tab_datos:
        b1,b2 = st.columns(2)
        if "unit_mode" not in st.session_state: st.session_state["unit_mode"] = "in"
        if "tuvo_insp_prev" not in st.session_state: st.session_state["tuvo_insp_prev"] = True
        if "C9_src" not in st.session_state: st.session_state["C9_src"] = 0.250
        if "C12_src" not in st.session_state: st.session_state["C12_src"] = 0.220

        prev = b1.radio("¿Tuvo inspecciones anteriores?", ["Sí","No"], index=0 if st.session_state["tuvo_insp_prev"] else 1, key="tuvo_insp_prev_radio")
        st.session_state["tuvo_insp_prev"] = (prev == "Sí")
        unit = b2.selectbox("Unidad de espesor (datos)", ["in","mm"], index=0 if st.session_state.get("unit_mode","in")=="in" else 1, key="unit_mode")

        if st.session_state["tuvo_insp_prev"]:
            if unit=="in":
                C12_in = st.number_input("tmin última inspección", min_value=0.0, format="%.4f", value=float(st.session_state["C12_src"]), key="C12_src")
            else:
                C12_mm = st.number_input("tmin última inspección (mm)", min_value=0.0, format="%.3f", key="C12_src_mm")
                st.session_state["C12_src"] = float(mm_to_in(C12_mm)); C12_in = st.session_state["C12_src"]
            C12 = Decimal(str(C12_in)); C9 = Decimal(str(C12_in))
        else:
            if unit=="in":
                C9_in = st.number_input("t nominal (lámina anular)", min_value=0.0, format="%.4f", value=float(st.session_state["C9_src"]), key="C9_src")
            else:
                C9_mm = st.number_input("t nominal (lámina anular) (mm)", min_value=0.0, format="%.3f", key="C9_src_mm")
                st.session_state["C9_src"] = float(mm_to_in(C9_mm)); C9_in = st.session_state["C9_src"]
            C9 = Decimal(str(C9_in)); C12 = Decimal(str(C9_in))

        C15 = tmin_tabla
        st.session_state["C9"] = float(C9); st.session_state["C12"] = float(C12)

        st.markdown(
            f"<div class='section-card'><b>tmin requerido por tabla</b>: {C15:.3f} in "
            f"<span class='mm-text'>({in_to_mm(C15):.3f} mm)</span></div>",
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
        if C2 <= C6 or C6 < C4 or Decimal(str(st.session_state.get("C9",0))) <= 0 or Decimal(str(st.session_state.get("C12",0))) <= 0 or Decimal(str(C15)) <= 0:
            st.error("Revisa los datos: años y espesores deben ser válidos.")
        else:
            C2d, C4d, C6d = Decimal(str(C2)), Decimal(str(C4)), Decimal(str(C6))
            C9d, C12d = Decimal(str(st.session_state["C9"])), Decimal(str(st.session_state["C12"]))
            C17d, C15d = Decimal(str(C17)), Decimal(str(C15))

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
            m2.markdown(f"<div class='result-card'><div class='result-title'>Espesor esperado a {int(C17)} años</div><div class='result-value'>{P12_q:.3f} in <span class='mm-text'>({in_to_mm(P12_q):.2f} mm)</span></div></div>", unsafe_allow_html=True)
            m3.markdown(f"<div class='result-card'><div class='result-title'>Veredicto</div><div class='result-value'>{cum_text} {'<span class=\"badge-ok\">OK</span>' if cum_text=='CUMPLE' else '<span class=\"badge-no\">ALERTA</span>'}</div></div>", unsafe_allow_html=True)

            st.markdown("#### Detalle de pérdidas y tasas")
            d1,d2 = st.columns(2)
            d1.markdown(f"<div class='result-card'><div class='result-title'>Porcentaje de pérdida C-Scan</div><div class='result-value'>{porc_Cscan:.0f} %</div></div>", unsafe_allow_html=True)
            d1.markdown(f"<div class='result-card'><div class='result-title'>Porcentaje de pérdida para validar MFL</div><div class='result-value'>{porc_MFL:.0f} %</div></div>", unsafe_allow_html=True)
            d2.markdown(f"<div class='result-card'><div class='result-title'>Componentes P</div><div class='result-sub'>P1: Últ. insp. → Construcción<br/>P2: Últ. insp. → Insp. actual<br/>P3: Construcción → Insp. actual</div><div class='result-value'>{P1:.3f} | {P2:.3f} | {P3:.3f} mpy</div></div>", unsafe_allow_html=True)
