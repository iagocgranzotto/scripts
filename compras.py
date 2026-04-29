import streamlit as st
import pandas as pd
import os
import sqlite3

# Nome do arquivo
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
arquivo_excel = os.path.join(BASE_DIR, "materiais.xlsx")
#arquivo_excel = "Z:/AUTOMATIZAÇÃO/Compras/materiais.xlsx"

st.title("📦 Solicitação de Materiais")

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

# Revisão antes de salvar
if submitted:
    st.subheader("🔎 Revisão")
    st.write(f"**Solicitante:** {solicitante}")
    st.write(f"**Obra:** {obra}")
    st.write(f"**Quantidade:** {quantidade}")
    st.write(f"**Unidade:** {unidade}")
    st.write(f"**Material:** {descricao}")

    confirmar = st.button("✅ Confirmar envio")

    if confirmar:
        novo_dado = pd.DataFrame([{
            "Solicitante": solicitante,
            "Obra": obra,
            "Quantidade": quantidade,
            "Unidade": unidade,
            "Material": descricao
        }])

        # Se arquivo existe → append
        if os.path.exists(arquivo_excel):
            df_existente = pd.read_excel(arquivo_excel)
            df_final = pd.concat([df_existente, novo_dado], ignore_index=True)
        else:
            df_final = novo_dado

        df_final.to_excel(arquivo_excel, index=False)

        #Enviar para base sqlite
        #conn = sqlite3.connect("Z:/AUTOMATIZAÇÃO/Compras/compras.db")
        conn = sqlite3.connect(os.path.join(BASE_DIR, "compras.db"))
        novo_dado.to_sql("compras_obras", conn, if_exists="append", index=False)
        conn.close()

        st.success("✅ Material registrado com sucesso!")