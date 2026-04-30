import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def normalizar_codigo(codigo):
    return str(codigo).strip().zfill(5)

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
    # Normaliza códigos
    produtos["codigo"] = produtos["codigo"].astype(str).str.strip().str.zfill(5)

    if mov.empty:
        produtos["quantidade"] = 0
        produtos["ultima_mov"] = None
        return produtos

    mov["codigo"] = mov["codigo"].astype(str).str.strip().str.zfill(5)

    # Calcula entrada/saida
    mov["quantidade_calc"] = mov.apply(
        lambda x: x["quantidade"] if x["tipo"] == "entrada" else -x["quantidade"],
        axis=1
    )

    estoque = mov.groupby("codigo", as_index=False)["quantidade_calc"].sum()

    ultima = (
        mov.sort_values("data")
        .groupby("codigo", as_index=False)
        .last()[["codigo", "data"]]
        .rename(columns={"data": "ultima_mov"})
    )

    # Merge seguro
    resultado = produtos.merge(estoque, on="codigo", how="left")
    resultado = resultado.merge(ultima, on="codigo", how="left")

    # Limpeza
    resultado["quantidade_calc"] = resultado["quantidade_calc"].fillna(0)

    # Remove possíveis duplicadas (blindagem)
    resultado = resultado.loc[:, ~resultado.columns.duplicated()]

    # Renomeia
    resultado = resultado.rename(columns={"quantidade_calc": "quantidade"})

    return resultado


# =========================
# CARREGAR DADOS
# =========================
produtos, movimentacoes, produtos_ws, mov_ws = carregar_dados()

produtos = produtos.loc[:, ~produtos.columns.duplicated()]
movimentacoes = movimentacoes.loc[:, ~movimentacoes.columns.duplicated()]

# =========================
# ABAS
# =========================
aba1, aba2, aba3 = st.tabs(["📋 Cadastro", "🔄 Movimentação", "📊 Estoque"])

# =========================
# CADASTRO
# =========================
with aba1:
    st.subheader("Cadastro de Produto")

    # NORMALIZA BASE
    if not produtos.empty:
        produtos["codigo"] = produtos["codigo"].astype(str).str.strip().str.zfill(5)

    modo = st.radio("Modo", ["Cadastrar", "Editar"])

    # =========================
    # CADASTRAR
    # =========================
    if modo == "Cadastrar":
        codigo = st.text_input("Código (até 5 dígitos)")
        nome = st.text_input("Nome")
        descricao = st.text_area("Descrição")
        preco = st.number_input("Preço", min_value=0.0, format="%.2f")

        if st.button("Cadastrar"):
            codigo_formatado = normalizar_codigo(codigo)

            codigos_existentes = produtos["codigo"].astype(str).values

            if not codigo.isdigit() or len(codigo) > 5:
                st.error("Código inválido")

            elif codigo_formatado in codigos_existentes:
                st.error("Código já existe")

            elif nome.strip() == "":
                st.error("Nome é obrigatório")

            else:
                novo = pd.DataFrame([{
                    "codigo": codigo_formatado,
                    "nome": nome.strip(),
                    "descricao": descricao.strip(),
                    "preco": preco
                }])

                produtos = pd.concat([produtos, novo], ignore_index=True)
                salvar_produtos(produtos, produtos_ws)
                st.success("Produto cadastrado")

    # =========================
    # EDITAR
    # =========================
    else:
        if produtos.empty:
            st.warning("Nenhum produto cadastrado")
        else:
            lista_produtos = produtos["codigo"] + " - " + produtos["nome"]
            selecionado = st.selectbox("Selecione o produto", lista_produtos)

            codigo_sel = selecionado.split(" - ")[0]
            produto = produtos[produtos["codigo"] == codigo_sel].iloc[0]

            novo_nome = st.text_input("Nome", value=produto["nome"])
            nova_desc = st.text_area("Descrição", value=produto["descricao"])
            novo_preco = st.number_input("Preço", value=float(produto["preco"]), format="%.2f")

            if st.button("Atualizar Produto"):
                idx = produtos[produtos["codigo"] == codigo_sel].index[0]

                produtos.loc[idx, "nome"] = novo_nome.strip()
                produtos.loc[idx, "descricao"] = nova_desc.strip()
                produtos.loc[idx, "preco"] = novo_preco

                salvar_produtos(produtos, produtos_ws)
                st.success("Produto atualizado com sucesso")

# =========================
# MOVIMENTAÇÃO
# =========================
with aba2:
    st.subheader("Movimentação")

    cod = normalizar_codigo(st.text_input("Código do produto"))
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
        codigos_existentes = produtos["codigo"].astype(str).str.strip().str.zfill(5)

        if cod not in codigos_existentes.values:
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
    
    estoque = estoque.loc[:, ~estoque.columns.duplicated()]
    
    st.dataframe(estoque, use_container_width=True)