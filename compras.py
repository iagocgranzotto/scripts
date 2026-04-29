import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.title("📦 Solicitação de Materiais")

# 🔹 CACHE (melhoria de performance) — FICA NO TOPO
@st.cache_resource
def conectar_sheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], scope
    )

    client = gspread.authorize(creds)
    return client.open("ControleMateriais").sheet1


# 🔹 CONTROLE DE ENVIO DUPLICADO — FICA NO TOPO
if "enviado" not in st.session_state:
    st.session_state.enviado = False


# Formulário
with st.form("form_materiais"):
    solicitante = st.text_input("Nome do Solicitante")
    obra = st.text_input("Nome da Obra")
    quantidade = st.number_input("Quantidade", min_value=0.0, step=1.0)
    unidade = st.selectbox(
        "Unidade",
        ["metro", "m²", "m³", "kg", "sacos", "baldes", "unidade"]
    )
    descricao = st.text_area("Descrição do Material")

    submitted = st.form_submit_button("Revisar")


# Revisão
if submitted:
    st.subheader("🔎 Revisão")
    st.write(f"**Solicitante:** {solicitante}")
    st.write(f"**Obra:** {obra}")
    st.write(f"**Quantidade:** {quantidade}")
    st.write(f"**Unidade:** {unidade}")
    st.write(f"**Material:** {descricao}")

    # 🔹 VALIDAÇÃO (entra aqui, antes de enviar)
    if not solicitante or not descricao:
        st.warning("⚠️ Preencha pelo menos Solicitante e Material")
    
    else:
        # 🔹 BOTÃO DE CONFIRMAÇÃO
        if st.button("✅ Confirmar envio") and not st.session_state.enviado:

            sheet = conectar_sheet()

            sheet.append_row([
                solicitante,
                obra,
                quantidade,
                unidade,
                descricao
            ])

            st.session_state.enviado = True  # 🔹 trava duplicidade

            st.success("✅ Material registrado no Google Sheets!")


# 🔹 RESET OPCIONAL (permite novo envio sem recarregar página)
if st.session_state.enviado:
    if st.button("➕ Novo envio"):
        st.session_state.enviado = False