import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

st.title("📦 Solicitação de Materiais")

# 🔹 CACHE (performance)
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


# 🔹 FORMULÁRIO
with st.form("form_materiais"):
    solicitante = st.text_input("Nome do Solicitante")
    obra = st.text_input("Nome da Obra")
    quantidade = st.number_input("Quantidade", min_value=0.0, step=1.0)
    unidade = st.selectbox(
        "Unidade",
        ["metro", "m²", "m³", "kg", "sacos", "baldes", "unidade"]
    )
    descricao = st.text_area("Descrição do Material")

    enviar = st.form_submit_button("✅ Enviar")

    # 🔹 AQUI ACONTECE O ENVIO (SEM BOTÃO EXTRA)
    if enviar:

        # Validação
        if not solicitante or not descricao:
            st.warning("⚠️ Preencha pelo menos Solicitante e Material")

        else:
            try:
                data_envio = datetime.now().strftime("%d/%m/%Y %H:%M")

                sheet = conectar_sheet()

                sheet.append_row([
                    data_envio,
                    solicitante,
                    obra,
                    quantidade,
                    unidade,
                    descricao
                ])

                st.success("✅ Material registrado no Google Sheets!")

            except Exception as e:
                st.error(f"❌ Erro ao salvar: {e}")