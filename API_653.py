import streamlit as st

st.set_page_config(page_title="API 653 - Inicio", page_icon="🛢️", layout="centered")

# Flag de sesión: ya se vio la portada
st.session_state["saw_home"] = True

st.title("🛢️ Suite de Cálculos API 653")
st.info(
    "**Bienvenido.**\n\n"
    "Utiliza el menú de navegación a la izquierda para seleccionar el tipo de cálculo:\n\n"
    "- Fondo (Centrales)\n"
    "- Zona Crítica\n"
    "- Láminas Anulares\n"
)

st.markdown("---")
st.write("Creado por Jonathan Gámez.")


