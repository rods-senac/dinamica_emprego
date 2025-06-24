import pandas as pd
import plotly.express as px
import json
import ast
import re
import unicodedata
import os
import requests
import streamlit as st

# === Layout e CSS personalizados ===
st.set_page_config(layout="wide")

st.markdown("""
    <style>
        /* Cor de fundo da barra lateral */
        [data-testid="stSidebar"] {
            background-color: #00794A;
            color: white;
        }

        /* Texto e componentes da barra lateral */
        [data-testid="stSidebar"] .css-ng1t4o,
        [data-testid="stSidebar"] .css-1cpxqw2,
        [data-testid="stSidebar"] .stSelectbox > div {
            color: white !important;
        }

        /* Remover cor de fundo da aba ativa */
        .stTabs [data-baseweb="tab"] {
            background-color: transparent !important;
        }

        .block-container {
            padding: 1rem 1rem 1rem 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# === Dados ===
df = pd.read_csv("aux_adm_com_spans.csv", encoding="utf-8-sig")
df.columns = df.columns.str.strip().str.lower()
df["publication_date_normalized"] = pd.to_datetime(df["publication_date_normalized"], errors="coerce")

for col in ["habilidades", "conhecimentos", "atitudes_valores"]:
    df[col] = df[col].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) and x.startswith("[") else [])

# === GeoJSON ===
geojson_path = "brasil_estados.geojson"
if not os.path.exists(geojson_path):
    url = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson"
    with open(geojson_path, "w", encoding="utf-8") as f:
        f.write(requests.get(url).text)
with open(geojson_path, encoding="utf-8") as f:
    geojson_br = json.load(f)

def remover_acentos(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", errors="ignore").decode("utf-8")

df["estado_normalizado"] = df["location_state"].apply(remover_acentos)

# === Menu Lateral ===
st.sidebar.image("logo_dinamica.png",  use_container_width=True)
st.sidebar.title("📍 Estado")
estados_disponiveis = sorted(df["location_state"].dropna().unique())
estado_selecionado = st.sidebar.selectbox("", ["Todos"] + estados_disponiveis)

if estado_selecionado != "Todos":
    df = df[df["location_state"] == estado_selecionado]

# === Tabs ===
st.title("📊 Painel Vagas - Auxiliar Administrativo")
aba1, aba2, aba3 = st.tabs(["🗺️ Mapa + Top Competências", "📈 Análises Gerais", "📌 Competências por UF"])

# === Aba 1 ===
with aba1:
    st.subheader("🗺️ Mapa de Vagas por Estado")
    df_estados_geo = pd.DataFrame([f["properties"]["name"] for f in geojson_br["features"]], columns=["estado"])
    df_estados_geo["estado_normalizado"] = df_estados_geo["estado"].apply(remover_acentos)
    vagas_estado = df["estado_normalizado"].value_counts().reset_index()
    vagas_estado.columns = ["estado_normalizado", "vagas"]
    df_mapa = pd.merge(df_estados_geo, vagas_estado, on="estado_normalizado", how="left").fillna(0)

    fig = px.choropleth(
        df_mapa,
        geojson=geojson_br,
        locations="estado",
        featureidkey="properties.name",
        color="vagas",
            color_continuous_scale=[[0, "#D9F3EA"], [1, "#00794A"]],
        title="Número de Vagas por Estado",
        scope="south america"
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(height=550)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🏆 Top 10 Competências")
    col1, col2, col3 = st.columns(3)
    with col1:
        top_hab = df.explode("habilidades")["habilidades"].value_counts().nlargest(10).reset_index()
        top_hab.columns = ["habilidade", "frequencia"]
        fig_hab = px.bar(top_hab, x="habilidade", y="frequencia", title="Top Habilidades", color_discrete_sequence=["#00794A"])
        st.plotly_chart(fig_hab, use_container_width=True)
    with col2:
        top_conh = df.explode("conhecimentos")["conhecimentos"].value_counts().nlargest(10).reset_index()
        top_conh.columns = ["conhecimento", "frequencia"]
        fig_conh = px.bar(top_conh, x="conhecimento", y="frequencia", title="Top Conhecimentos", color_discrete_sequence=["#00794A"])
        st.plotly_chart(fig_conh, use_container_width=True)
    with col3:
        def remover_financeiro(lista):
            return [item for item in lista if not re.search(r'\bfinanceir[ao]s?\b', item, re.IGNORECASE)]
        df["atitudes_valores"] = df["atitudes_valores"].apply(remover_financeiro)
        top_ati = df.explode("atitudes_valores")["atitudes_valores"].value_counts().nlargest(10).reset_index()
        top_ati.columns = ["atitude_valor", "frequencia"]
        fig_ati = px.bar(top_ati, x="atitude_valor", y="frequencia", title="Top Atitudes e Valores", color_discrete_sequence=["#00794A"])
        st.plotly_chart(fig_ati, use_container_width=True)

# === Aba 2 ===
with aba2:
    st.subheader("📆 Evolução de Vagas")
    df_valid = df.dropna(subset=["publication_date_normalized"])
    df_valid["mes"] = df_valid["publication_date_normalized"].dt.to_period("M").astype(str)
    d_mes = df_valid["mes"].value_counts().sort_index()
    df_mes = d_mes.reset_index()
    df_mes.columns = ["mes", "vagas"]
    fig_linha = px.line(df_mes, x="mes", y="vagas", title="Vagas por Mês", color_discrete_sequence=["#00794A"])
    st.plotly_chart(fig_linha, use_container_width=True)

    st.subheader("📊 Competências por Tipo")
    contagem = {
        "Habilidades": sum(len(x) for x in df["habilidades"]),
        "Conhecimentos": sum(len(x) for x in df["conhecimentos"]),
        "Atitudes_Valores": sum(len(x) for x in df["atitudes_valores"])
    }
    df_comp = pd.DataFrame(list(contagem.items()), columns=["Tipo", "Total"])
    fig_tipo = px.bar(df_comp, x="Tipo", y="Total", title="Distribuição por Tipo", color_discrete_sequence=["#00794A"])
    st.plotly_chart(fig_tipo, use_container_width=True)

    st.subheader("📈 Evolução Mensal de Vagas por Estado")
    df_linha_uf = df_valid.groupby(["mes", "location_state"]).size().reset_index(name="vagas")
    fig_estado_linha = px.line(df_linha_uf, x="mes", y="vagas", color="location_state", markers=True,
                                title="Evolução Mensal de Vagas por UF",
                                labels={"location_state": "Estado", "vagas": "Nº de Vagas", "mes": "Mês"})
    fig_estado_linha.update_layout(xaxis=dict(tickangle=45))
    st.plotly_chart(fig_estado_linha, use_container_width=True)

# === Aba 3 ===
with aba3:
    st.subheader("📌 Principais Competências por UF (com mais de 10 vagas)")
    vagas_por_estado = df["location_state"].value_counts()
    estados_filtrados = vagas_por_estado[vagas_por_estado > 10].index.tolist()

    for estado in sorted(estados_filtrados):
        st.markdown(f"### 📍 {estado}")
        df_uf = df[df["location_state"] == estado]
        col1, col2, col3 = st.columns(3)

        with col1:
            top = df_uf.explode("habilidades")["habilidades"].value_counts().nlargest(5).reset_index()
            top.columns = ["habilidade", "frequencia"]
            st.plotly_chart(px.bar(top, x="habilidade", y="frequencia", title="Habilidades", color_discrete_sequence=["#00794A"]), use_container_width=True)

        with col2:
            top = df_uf.explode("conhecimentos")["conhecimentos"].value_counts().nlargest(5).reset_index()
            top.columns = ["conhecimento", "frequencia"]
            st.plotly_chart(px.bar(top, x="conhecimento", y="frequencia", title="Conhecimentos", color_discrete_sequence=["#00794A"]), use_container_width=True)

        with col3:
            top = df_uf.explode("atitudes_valores")["atitudes_valores"].value_counts().nlargest(5).reset_index()
            top.columns = ["atitude_valor", "frequencia"]
            st.plotly_chart(px.bar(top, x="atitude_valor", y="frequencia", title="Atitudes e Valores", color_discrete_sequence=["#00794A"]), use_container_width=True)