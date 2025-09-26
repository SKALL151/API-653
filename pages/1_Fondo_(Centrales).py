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

def q3(x): 
    return Decimal(str(x)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

def in_to_mm(v): 
    return q3(Decimal(v) * Decimal("25.4"))

def mm_to_in(v): 
    return q3(Decimal(v) / Decimal("25.4"))

DEFAULTS = {"C2": 2025, "C4": 2005, "C6": 2015, "C9": 0.250, "C12": 0.220, "C15": 0.100, "C17": 10}
for k,v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Estados UI
if "unit_mode" not in st.session_state:
    st.session_state["unit_mode"] = "in"
if "tuvo_insp_prev" not in st.session_state:
    st.session_state["tuvo_insp_prev"] = True
if "C9_src" not in st.session_state:
    st.session_state["C9_src"] = float(st.session_state.get("C9", 0.250))
if "C12_src" not in st.session_state:
    st.session_state["C12_src"] = float(st.session_state.get("C12", 0.220))

def fila_P(C2, C4, C6, C9, C12, L4):
    C2, C4, C6, C9, C12, L4 = map(Decimal, [C2, C4, C6, C9, C12, L4])
    P1 = (C12 - C9) / (C6 - C4) * 1000 if (C6 - C4) != 0 else Decimal("0")
    P2 = (C9 - L4) / (C2 - C6) * 1000 if (C2 - C6) != 0 else Decimal("0")
    P3 = (C12 - L4) / (C2 - C4) * 1000 if (C2 - C4) != 0 else Decimal("0")
    return P1, P2, P3, max(P1, P2, P3, Decimal("0"))

def calcular_L4_iterativo_objetivo(C2, C4, C6, C9, C12, C15, C17):
    target_q, lo, hi, step = q3(C15), Decimal("0.0"), Decimal(str(C12)), Decimal("0.0001")
    L4_val, last_ok = hi, None
    for _ in range(int((hi - lo) / step) + 2):
        _, _, _, L2_iter = fila_P(C2, C4, C6, C9, C12, L4_val)
        P12i_q = q3(L4_val - (L2_iter / 1000 * Decimal(C17)))
        if P12i_q >= target_q:
            last_ok, L4_val = L4_val, L4_val - step
            if L4_val < lo:
                break
        else:
            break
    return last_ok if last_ok is not None else L4_val

st.title("Fondo Láminas centrales")
left, right = st.columns([1,1.1], gap="large")

with left:

    tab_fechas, tab_datos = st.tabs(["Fechas", "Datos"])

    with tab_fechas:
        r1c1, r1c2 = st.columns(2)
        C2 = r1c1.number_input("Año inspección actual", 1900, 2100, key="C2")
        C4 = r1c2.number_input("Año construcción", 1900, 2100, key="C4")
        r1c3, r1c4 = st.columns(2)
        C6 = r1c3.number_input("Año última inspección", 1900, 2100, key="C6")
        C17 = r1c4.number_input("Plazo próxima inspección (años)", 0, 50, key="C17")

    with tab_datos:
        # Cabecera compacta sin franja vacía

        # Unidad y fuente de espesor
        r2c1, r2c2 = st.columns([1,1])
        unit = r2c1.selectbox(
            "Unidad de espesor",
            options=["in", "mm"],
            index=0 if st.session_state["unit_mode"] == "in" else 1,
            key="unit_mode",
            help="La unidad elegida aplica a los campos de espesor visibles."
        )
        prev = r2c2.radio(
            "¿Tuvo inspecciones anteriores?",
            options=["Sí", "No"],
            index=0 if st.session_state["tuvo_insp_prev"] else 1,
            key="tuvo_insp_prev_radio"
        )
        st.session_state["tuvo_insp_prev"] = (prev == "Sí")

        # Etiquetas dinámicas
        lbl_tmin = "Tmin última inspección (in)" if unit == "in" else "Tmin última inspección (mm)"
        lbl_tnom = "Tnominal fondo (in)" if unit == "in" else "Tnominal fondo (mm)"
        lbl_req  = "Tmin requerido (in)" if unit == "in" else "Tmin requerido (mm)"

        # Entradas condicionales
        if st.session_state["tuvo_insp_prev"]:
            if unit == "in":
                C12_in = st.number_input(lbl_tmin, min_value=0.0, format="%.3f", value=float(st.session_state["C12_src"]), key="C12_src")
            else:
                C12_mm = st.number_input(lbl_tmin, min_value=0.0, format="%.3f", key="C12_src_mm")
                st.session_state["C12_src"] = float(mm_to_in(C12_mm))
                C12_in = st.session_state["C12_src"]
            C12 = Decimal(str(C12_in))
            C9  = Decimal(str(C12_in))
        else:
            if unit == "in":
                C9_in = st.number_input(lbl_tnom, min_value=0.0, format="%.3f", value=float(st.session_state["C9_src"]), key="C9_src")
            else:
                C9_mm = st.number_input(lbl_tnom, min_value=0.0, format="%.3f", key="C9_src_mm")
                st.session_state["C9_src"] = float(mm_to_in(C9_mm))
                C9_in = st.session_state["C9_src"]
            C9  = Decimal(str(C9_in))
            C12 = Decimal(str(C9_in))

        st.session_state["C9"]  = float(C9)
        st.session_state["C12"] = float(C12)

        # tmin requerido
        if unit == "in":
            C15_in = st.number_input(lbl_req, 0.0, format="%.3f", key="C15_in")
            C15 = Decimal(str(C15_in))
        else:
            C15_mm = st.number_input(lbl_req, 0.0, format="%.3f", key="C15_mm")
            C15 = Decimal(str(mm_to_in(C15_mm)))

    st.divider()
    b1, b2 = st.columns(2)
    calcular = b1.button("Calcular", use_container_width=True)
    if b2.button("🧹 Limpiar", type="secondary", use_container_width=True):
        st.session_state.clear()
        for k,v in DEFAULTS.items():
            st.session_state[k] = v
        st.rerun()

with right:
    st.markdown("### Resultados")
    if calcular:
        if C2 <= C6 or C6 < C4 or st.session_state.get("C9", 0) <= 0 or st.session_state.get("C12", 0) <= 0 or C15 <= 0:
            st.error("Revisa los datos: años y espesores deben ser válidos.")
        else:
            C2d = Decimal(str(C2))
            C4d = Decimal(str(C4))
            C6d = Decimal(str(C6))
            C9d = Decimal(str(st.session_state["C9"]))
            C12d = Decimal(str(st.session_state["C12"]))
            C17d = Decimal(str(C17))
            C15d = Decimal(str(C15))

            L4 = calcular_L4_iterativo_objetivo(C2d, C4d, C6d, C9d, C12d, C15d, C17d)
            P1, P2, P3, L2 = fila_P(C2d, C4d, C6d, C9d, C12d, L4)
            P6 = q3((L2/1000*C17d) + C15d)
            P12_q = q3(Decimal(L4) - (L2/1000*C17d))
            cum_text = "CUMPLE" if P12_q >= q3(C15d) else "NO CUMPLE"
            porc_Cscan = q3(Decimal(100) - (Decimal(L4) * Decimal(100) / C12d))
            porc_MFL = q3(porc_Cscan - Decimal(10))

            st.markdown(
                f"<div class='result-card'><div class='result-title'>Tasa de corrosión</div>"
                f"<div class='result-value'>{q3(L2):.3f} mpy</div></div>",
                unsafe_allow_html=True
            )
            m1, m2, m3 = st.columns(3)
            m1.markdown(
                f"<div class='result-card'><div class='result-title'>Tmin antes de parche</div>"
                f"<div class='result-value'>{P6:.3f} in <span class='mm-text'>({in_to_mm(P6):.2f} mm)</span></div></div>",
                unsafe_allow_html=True
            )
            m2.markdown(
                f"<div class='result-card'><div class='result-title'>Espesor esperado a {int(C17)} años</div>"
                f"<div class='result-value'>{P12_q:.3f} in <span class='mm-text'>({in_to_mm(P12_q):.2f} mm)</span></div></div>",
                unsafe_allow_html=True
            )
            m3.markdown(
                f"<div class='result-card'><div class='result-title'>Veredicto</div>"
                f"<div class='result-value'>{cum_text} "
                f"{'<span class=\"badge-ok\">OK</span>' if cum_text=='CUMPLE' else '<span class=\"badge-no\">ALERTA</span>'}"
                f"</div></div>",
                unsafe_allow_html=True
            )

            st.markdown("#### Detalle de pérdidas y tasas")
            d1, d2 = st.columns(2)
            d1.markdown(
                f"<div class='result-card'><div class='result-title'>Porcentaje de pérdida C-Scan (Antes de parche)</div>"
                f"<div class='result-value'>{porc_Cscan:.0f} %</div></div>",
                unsafe_allow_html=True
            )
            d1.markdown(
                f"<div class='result-card'><div class='result-title'>Porcentaje de pérdida para validar MFL</div>"
                f"<div class='result-value'>{porc_MFL:.0f} %</div></div>",
                unsafe_allow_html=True
            )
            d2.markdown(
                f"<div class='result-card'><div class='result-title'>Componentes P</div>"
                f"<div class='result-sub'>P1: Últ. insp. → Construcción<br/>P2: Últ. insp. → Insp. actual<br/>P3: Construcción → Insp. actual</div>"
                f"<div class='result-value'>{P1:.3f} | {P2:.3f} | {P3:.3f} mpy</div></div>",
                unsafe_allow_html=True
            )
