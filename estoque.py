import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Controle de Estoque", layout="wide")

EMPRESA = "Controle de Estoque"
SITE = "Cadastro de produtos, Controle de Entrada e Saída e Visão Geral"

st.title(f"📦 {EMPRESA}")
st.subheader(SITE)

# =========================
# GOOGLE SHEETS CONEXÃO
# =========================

def conectar_gsheets():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], scope
    )

    client = gspread.authorize(creds)
    return client.open("controle_estoque")


def carregar_dados():
    sheet = conectar_gsheets()

    produtos_ws = sheet.worksheet("produtos")
    mov_ws = sheet.worksheet("movimentacoes")

    produtos_raw = produtos_ws.get_all_records()
    mov_raw = mov_ws.get_all_records()

    # Garante estrutura mesmo vazio
    if produtos_raw:
        produtos = pd.DataFrame(produtos_raw)
    else:
        produtos = pd.DataFrame(columns=["codigo", "nome", "descricao", "preco"])

    if mov_raw:
        mov = pd.DataFrame(mov_raw)
    else:
        mov = pd.DataFrame(columns=["codigo", "quantidade", "tipo", "obs", "data"])

    return produtos, mov, produtos_ws, mov_ws


def salvar_produtos(df, worksheet):
    worksheet.clear()
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())


def salvar_mov(df, worksheet):
    worksheet.clear()
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())


def calcular_estoque(produtos, mov):
    if mov.empty:
        produtos["quantidade"] = 0
        produtos["ultima_mov"] = None
        return produtos

    mov["quantidade_calc"] = mov.apply(
        lambda x: x["quantidade"] if x["tipo"] == "entrada" else -x["quantidade"],
        axis=1
    )

    estoque = mov.groupby("codigo")["quantidade_calc"].sum().reset_index()

    ultima = mov.sort_values("data").groupby("codigo").last().reset_index()
    ultima = ultima[["codigo", "data"]].rename(columns={"data": "ultima_mov"})

    resultado = produtos.merge(estoque, on="codigo", how="left")
    resultado = resultado.merge(ultima, on="codigo", how="left")

    resultado["quantidade_calc"] = resultado["quantidade_calc"].fillna(0)
    resultado = resultado.rename(columns={"quantidade_calc": "quantidade"})

    return resultado


# =========================
# CARREGAR DADOS
# =========================
produtos, movimentacoes, produtos_ws, mov_ws = carregar_dados()

# =========================
# ABAS
# =========================
aba1, aba2, aba3 = st.tabs(["📋 Cadastro", "🔄 Movimentação", "📊 Estoque"])

# =========================
# CADASTRO
# =========================
with aba1:
    st.subheader("Cadastro de Produto")

    codigo = st.text_input("Código (até 5 dígitos)")
    nome = st.text_input("Nome")
    descricao = st.text_area("Descrição")
    preco = st.number_input("Preço", min_value=0.0, format="%.2f")

    if st.button("Cadastrar"):
        if not codigo.isdigit() or len(codigo) > 5:
            st.error("Código inválido")
        elif codigo in produtos["codigo"].astype(str).values:
            st.error("Código já existe")
        else:
            novo = pd.DataFrame([{
                "codigo": codigo,
                "nome": nome,
                "descricao": descricao,
                "preco": preco
            }])

            produtos = pd.concat([produtos, novo], ignore_index=True)
            salvar_produtos(produtos, produtos_ws)
            st.success("Produto cadastrado")

# =========================
# MOVIMENTAÇÃO
# =========================
with aba2:
    st.subheader("Movimentação")

    cod = st.text_input("Código do produto")
    qtd = st.number_input("Quantidade", min_value=1)
    obs = st.text_input("Observação")

    estoque = calcular_estoque(produtos, movimentacoes)

    if st.button("Entrada"):
        if cod not in produtos["codigo"].astype(str).values:
            st.error("Produto não encontrado")
        else:
            nova = pd.DataFrame([{
                "codigo": cod,
                "quantidade": qtd,
                "tipo": "entrada",
                "obs": obs,
                "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }])

            movimentacoes = pd.concat([movimentacoes, nova], ignore_index=True)
            salvar_mov(movimentacoes, mov_ws)
            st.success("Entrada registrada")

    if st.button("Saída"):
        if cod not in produtos["codigo"].astype(str).values:
            st.error("Produto não encontrado")
        else:
            qtd_atual = estoque.loc[estoque["codigo"] == cod, "quantidade"]

            if qtd_atual.empty or qtd_atual.values[0] < qtd:
                st.error("Estoque insuficiente")
            else:
                nova = pd.DataFrame([{
                    "codigo": cod,
                    "quantidade": qtd,
                    "tipo": "saida",
                    "obs": obs,
                    "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }])

                movimentacoes = pd.concat([movimentacoes, nova], ignore_index=True)
                salvar_mov(movimentacoes, mov_ws)
                st.success("Saída registrada")

# =========================
# ESTOQUE
# =========================
with aba3:
    st.subheader("Estoque Atual")

    estoque = calcular_estoque(produtos, movimentacoes)

    filtro = st.text_input("Filtro (código ou nome)")

    if filtro:
        estoque = estoque[
            estoque["codigo"].astype(str).str.contains(filtro, case=False) |
            estoque["nome"].str.contains(filtro, case=False)
        ]

    st.dataframe(estoque, use_container_width=True)