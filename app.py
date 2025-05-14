import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import re
from datetime import datetime
import os
import altair as alt

st.set_page_config(page_title="Comparador de Valores - Catalisadores", layout="centered")
st.title("📊 Comparador de Valores - Planilha vs Nota Fiscal")

st.markdown("Compare o valor total da sua planilha Excel com a nota fiscal e descubra o lucro da operação.")

# Uploads
excel_file = st.file_uploader("📈 Envie a planilha Excel (.xlsx)", type="xlsx")
pdf_file = st.file_uploader("🧾 Envie a nota fiscal em PDF", type="pdf")

if excel_file and pdf_file:
    try:
        # Lê o Excel
        xls = pd.ExcelFile(excel_file)
        imput_df = xls.parse("Imput")

        # Identifica coluna "Preço Tt"
        col_preco_tt = None
        for col in imput_df.columns:
            if imput_df[col].astype(str).str.contains("Preço Tt").any():
                col_preco_tt = col
                break

        if col_preco_tt is None:
            st.error("Coluna 'Preço Tt' não encontrada.")
        else:
            # Soma valores válidos
            total_excel = imput_df[col_preco_tt].dropna()
            total_excel = total_excel[total_excel.apply(lambda x: isinstance(x, (int, float)))]
            valor_total_excel = total_excel.sum()

            st.success(f"📊 Valor total a receber (Excel): R$ {valor_total_excel:,.2f}")

            # Lê PDF e extrai valor da nota fiscal
            doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
            texto_pdf = "\n".join(page.get_text() for page in doc)

            match = re.search(r'Total Liquido:\s*([\d\.]+,\d{2})', texto_pdf)
            if not match:
                st.error("Não foi possível encontrar o valor total na nota fiscal.")
            else:
                valor_nf_str = match.group(1).replace(".", "").replace(",", ".")
                valor_nf = float(valor_nf_str)

                st.success(f"🧾 Valor registrado na nota fiscal: R$ {valor_nf:,.2f}")

                # Cálculo do ganho
                ganho = valor_total_excel - valor_nf

                if abs(ganho) < 0.01:
                    st.markdown("### ⚪ **Sem diferença entre os valores.**")
                elif ganho > 0:
                    st.markdown(f"### 🟢 **Ganho positivo: R$ {ganho:,.2f}**")
                else:
                    st.markdown(f"### 🔴 **Diferença negativa: R$ {ganho:,.2f}**")

                # Identificar data da análise
                data_analise = datetime.today().strftime("%Y-%m-%d")

                # Selecionar loja
                loja = st.selectbox("Selecione a loja:", ["Itaim", "Jaçanã"])

                # Relatório resumido
                resumo_df = pd.DataFrame([{
                    "Data": data_analise,
                    "Loja": loja,
                    "Valor Planilha": valor_total_excel,
                    "Valor Nota Fiscal": valor_nf,
                    "Ganho": ganho
                }])

                st.markdown("### 📄 Resumo:")
                st.dataframe(resumo_df)

                # Salvar histórico
                historico_path = "historico.csv"
                if os.path.exists(historico_path):
                    historico_df = pd.read_csv(historico_path)
                    historico_df = pd.concat([historico_df, resumo_df], ignore_index=True)
                else:
                    historico_df = resumo_df

                historico_df.to_csv(historico_path, index=False)

                # Exibir gráfico de ganhos por mês
                st.markdown("### 📈 Ganhos por Mês:")
                historico_df['Data'] = pd.to_datetime(historico_df['Data'])
                historico_df['Ano-Mês'] = historico_df['Data'].dt.to_period('M').astype(str)
                ganhos_mensais = historico_df.groupby(['Ano-Mês', 'Loja'])['Ganho'].sum().reset_index()

                chart = alt.Chart(ganhos_mensais).mark_bar().encode(
                    x='Ano-Mês',
                    y='Ganho',
                    color='Loja',
                    tooltip=['Ano-Mês', 'Loja', 'Ganho']
                ).properties(
                    width=700,
                    height=400
                )

                st.altair_chart(chart, use_container_width=True)

    except Exception as e:
        st.error(f"Ocorreu um erro: {e}")
