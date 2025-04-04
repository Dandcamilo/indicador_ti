import streamlit as st # type: ignore
import mysql.connector # type: ignore
import pandas as pd # type: ignore
import altair as alt # type: ignore
import numpy as np
from datetime import datetime
import sidetable as stb # type: ignore

def conectar_ao_banco():
    # (Seu código de conexão existente)
    return mysql.connector.connect(
        host=st.secrets["database"]["host"],
        port=st.secrets["database"]["port"],
        user=st.secrets["database"]["user"],
        password=st.secrets["database"]["password"],
        database=st.secrets["database"]["database"]
    )

def listar_tabelas(connection):
    # (Seu código existente)
    cursor = connection.cursor()
    cursor.execute("SHOW TABLES")
    tabelas = [tabela[0] for tabela in cursor.fetchall()]
    cursor.close()
    return tabelas

def buscar_dados(connection, tabela):
    # (Seu código existente)
    query = f"SELECT * FROM {tabela}"
    cursor = connection.cursor()
    cursor.execute(query)
    dados = cursor.fetchall()
    colunas = [i[0] for i in cursor.description]
    df = pd.DataFrame(dados, columns=colunas)
    cursor.close()
    return df

def page3():

    def criar_interface():


        st.markdown("<h1 style='text-align: center;'>Customizações 🛠</h1>", unsafe_allow_html=True)
        st.divider()
        conn = conectar_ao_banco()
        Tabela_custom = pd.merge(pd.DataFrame(buscar_dados(conn, 'SAC')), pd.DataFrame(buscar_dados(conectar_ao_banco(), 'SAC_ORCAMENTO')), on='numero', how='left')
        Tabela_custom['Dias Desde Abertura'] = (
            datetime.now() - pd.to_datetime(Tabela_custom['dt_solicitacao'])
        ).dt.days
        Tabela_custom['Dias Desde fechamento'] = (
            datetime.now() - pd.to_datetime(Tabela_custom['dt_encerramento'])
        ).dt.days
        Tabela_custom['Possui Data Finalização?'] = np.where(
            Tabela_custom['dt_encerramento'].isnull(),
            'NÃO',
            'SIM'
        )

        sla_mapping = {'Alta': 1, 'Critica': 1, 'Média': 4, 'Baixa': 8, 'Baixa Planejada': 8}
        Tabela_custom['SLA_map'] = Tabela_custom['criticidade'].map(sla_mapping)
        #Tabela_custom['SLA_map'] = Tabela_custom['SLA_map'].astype(int)
        # Comparando a diferença de dias com o SLA e criando a nova coluna
        Tabela_custom['Dias Abertura > SLA map'] = np.where(
            Tabela_custom['Dias Desde Abertura'] > Tabela_custom['SLA_map'],
            'SIM',
            'NÃO'
        )

        valor_1 = Tabela_custom['VL_PRIMEIRA_PARCELA'].sum()
        valor_2 = Tabela_custom['VL_SEGUNDA_PARCELA'].sum()
        valor_total = float(valor_1 + valor_2)

        custom = Tabela_custom[Tabela_custom['descricao_y'].notna()]
        Quant_custom = custom['numero'].count()
        Quant_custom_concluido = custom[custom['Possui Data Finalização?'] == 'SIM']['numero'].count()
        Quant_custom_nconcluido = custom[custom['Possui Data Finalização?'] == 'NÃO']['numero'].count()

        # Exibindo a tabela com as colunas relevantes
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Valor total", f'R$ {valor_total:,.2f}', border=True)
        col2.metric("Quantidade de Customizações", Quant_custom, border=True)
        col3.metric("Não Finalizados", Quant_custom_nconcluido, border=True)
        col4.metric("Finalizados", Quant_custom_concluido, border=True)

        st.dataframe(custom.reset_index(drop=True))

    # Conectar ao banco para carregar os números de SAC disponíveis
    try:
        conn = conectar_ao_banco()
        cursor = conn.cursor()
        cursor.execute("SELECT numero FROM SAC_ORCAMENTO")
        sac_numeros = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
    except Exception as e:
        st.error(f"Erro ao carregar números de SAC: {e}")
        sac_numeros = []

    # Formulário para atualizar valores
    with st.sidebar.form("form_atualizar_valor", clear_on_submit=True):
        st.subheader("Atualizar Registro Existente")
        numero = st.selectbox("Número do SAC", options=sac_numeros, help="Selecione o número do SAC para atualizar")
        descricao = st.text_input("Descrição", placeholder="Digite a nova descrição")
        vl_primeira_parcela = st.number_input("Novo Valor da Primeira Parcela", min_value=0.0, step=0.01)
        vl_segunda_parcela = st.number_input("Novo Valor da Segunda Parcela", min_value=0.0, step=0.01)
        submitted = st.form_submit_button("Atualizar Registro")

        if submitted:
            if numero:
                try:
                    # Conectar ao banco de dados
                    conn = conectar_ao_banco()
                    cursor = conn.cursor()

                    # Atualizar os dados no banco de dados
                    query = """
                        UPDATE SAC_ORCAMENTO
                        SET descricao = %s, VL_PRIMEIRA_PARCELA = %s, VL_SEGUNDA_PARCELA = %s
                        WHERE numero = %s
                    """
                    cursor.execute(query, (descricao, vl_primeira_parcela, vl_segunda_parcela, numero))
                    conn.commit()

                    if cursor.rowcount > 0:
                        st.success("Registro atualizado com sucesso!")
                    else:
                        st.warning("Nenhum registro encontrado com o número fornecido.")
                except Exception as e:
                    st.error(f"Erro ao atualizar registro: {e}")
                finally:
                    cursor.close()
                    conn.close()
            else:
                st.warning("Por favor, selecione um número do SAC.")
        
    criar_interface()

if __name__ == "__main__":
    page3()