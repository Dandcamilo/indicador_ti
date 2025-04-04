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

def page2():

    def criar_interface():

        st.markdown("<h1 style='text-align: center;'>SAC's Finalizados</h1>", unsafe_allow_html=True)
        st.divider()
        conn = conectar_ao_banco() 
        Tabela_sac_top = pd.DataFrame(buscar_dados(conn, 'SAC'))
        
        # Garante que a coluna 'dt_encerramento' seja datetime
        Tabela_sac_top['dt_encerramento'] = pd.to_datetime(Tabela_sac_top['dt_encerramento'], errors='coerce')

        # Remove valores NaT para encontrar os limites reais
        datas_validas = Tabela_sac_top['dt_encerramento'].dropna()

        if not datas_validas.empty:
            data_minima = datas_validas.min().to_pydatetime()
            data_maxima = datas_validas.max().to_pydatetime()

            # Cria o slider de data
            data_inicial_slider, data_final_slider = st.slider(
                "Selecione intervalo de Finalização:",
                min_value=data_minima,
                max_value=data_maxima,
                value=(data_minima, data_maxima),  # Define o valor inicial como o intervalo completo
                format="DD/MM/YYYY"
            )

            # Converte as datas do slider de volta para datetime do pandas para o filtro
            data_inicial_filtro = pd.to_datetime(data_inicial_slider)
            data_final_filtro = pd.to_datetime(data_final_slider)

            # Aplica o filtro usando as datas do slider
            Tabela_sac_top = Tabela_sac_top[
                (Tabela_sac_top['dt_encerramento'] >= data_inicial_filtro) &
                (Tabela_sac_top['dt_encerramento'] <= data_final_filtro)
            ]

            st.write(f"Mostrando dados de: {data_inicial_slider.strftime('%d/%m/%Y')} até {data_final_slider.strftime('%d/%m/%Y')}")


        else:
            st.warning("Não há datas válidas para criar o filtro.")
        st.divider()
        Log_alteracao_fornecedor = pd.DataFrame(buscar_dados(conn, 'Log_alteracao_fornecedor'))
        conn.close() 

        # --- Processamento do DataFrame ---
        Tabela_sac_top['dt_solicitacao'] = pd.to_datetime(Tabela_sac_top['dt_solicitacao'], errors='coerce')
        Tabela_sac_top['dt_encerramento'] = pd.to_datetime(Tabela_sac_top['dt_encerramento'], errors='coerce')

        now = datetime.now()
        Tabela_sac_top['Dias Desde Abertura'] = Tabela_sac_top['dt_solicitacao'].apply(
            lambda x: (now - x).days if pd.notna(x) else None
        )
        Tabela_sac_top['Dias Desde fechamento'] = Tabela_sac_top['dt_encerramento'].apply(
            lambda x: (now - x).days if pd.notna(x) else None
        )

        Tabela_sac_top['Possui Data Finalização?'] = np.where(
            Tabela_sac_top['dt_encerramento'].isnull(),
            'NÃO',
            'SIM'
        )

        # Calcular Quantidade_dias_Aberto apenas se ambas as datas existirem
        Tabela_sac_top['Quantidade_dias_Aberto'] = (
            Tabela_sac_top['dt_encerramento'] - Tabela_sac_top['dt_solicitacao']
        ).dt.days
        Tabela_sac_top.loc[Tabela_sac_top['dt_encerramento'].isnull() | Tabela_sac_top['dt_solicitacao'].isnull(), 'Quantidade_dias_Aberto'] = None


        sla_mapping = {'Alta': 1, 'Critica': 1, 'Média': 4, 'Baixa': 8, 'Baixa Planejada': 8}
        Tabela_sac_top['SLA_map'] = Tabela_sac_top['criticidade'].map(sla_mapping)
        Tabela_sac_top['SLA_map'] = Tabela_sac_top['SLA_map'].fillna(-1).astype(int) 

        Tabela_sac_top['Dias Abertura > SLA map'] = 'NÃO' 
        mask_abertura_sla = Tabela_sac_top['Dias Desde Abertura'].notna() & (Tabela_sac_top['SLA_map'] != -1)
        Tabela_sac_top.loc[mask_abertura_sla & (Tabela_sac_top['Dias Desde Abertura'] >= Tabela_sac_top['SLA_map']), 'Dias Abertura > SLA map'] = 'SIM'

        # Comparando Quantidade_dias_Aberto com SLA
        Tabela_sac_top['Fechado dentro do SLA'] = 'NÃO' # Default
        mask_fechado_sla = Tabela_sac_top['Quantidade_dias_Aberto'].notna() & (Tabela_sac_top['SLA_map'] != -1)
        Tabela_sac_top.loc[mask_fechado_sla & (Tabela_sac_top['Quantidade_dias_Aberto'] <= Tabela_sac_top['SLA_map']), 'Fechado dentro do SLA'] = 'SIM'
        Tabela_sac_top.loc[Tabela_sac_top['Possui Data Finalização?'] == 'NÃO', 'Fechado dentro do SLA'] = 'NÃO APLICÁVEL' 

        col1, col2 = st.columns(2)

        with col1:

            data_col1 = Tabela_sac_top[Tabela_sac_top['Possui Data Finalização?'] == 'SIM'].copy()
            grouped_data = data_col1.groupby(["tipo_solicitacao", 'Fechado dentro do SLA']).agg(numero=('numero', 'nunique')).reset_index()

            bar_chart = alt.Chart(grouped_data).mark_bar().encode(
                x=alt.X("tipo_solicitacao", title="Tipo de Solicitação"),
                y=alt.Y('numero', title="Número de Solicitações"),
                tooltip=['tipo_solicitacao', 'numero', 'Fechado dentro do SLA'],
                color=alt.Color('Fechado dentro do SLA',
                                scale=alt.Scale(domain=['SIM', 'NÃO'], range=['#03d300', '#c21f05']), 
                                legend=alt.Legend(title="Fechado Dentro do SLA?")) 
            ).properties(
                title='Número de Solicitações Fechadas por Tipo e SLA', 
                width=400,
                height=450
            )
            final_chart = bar_chart.interactive() 

            st.altair_chart(final_chart, use_container_width=True)

            with st.expander("Ver dados do gráfico de Tipo de Solicitação"):
                st.dataframe(grouped_data)

        with col2:

            data_col2 = Tabela_sac_top[Tabela_sac_top['Possui Data Finalização?'] == 'SIM'].copy()

            grouped_data2 = data_col2[data_col2['Fechado dentro do SLA'].isin(['SIM', 'NÃO'])] \
                              .groupby(['Fechado dentro do SLA']).agg(numero=('numero', 'nunique')).reset_index()

            def criar_grafico_pizza(dados):

                if not dados.empty and dados['numero'].sum() > 0:
                     dados['Percentual'] = dados['numero'] / dados['numero'].sum() * 100
                else:
                     dados['Percentual'] = 0

                chart = alt.Chart(dados).mark_arc(outerRadius=120).encode( 
                    theta=alt.Theta(field="Percentual", type="quantitative", stack=True),
                    color=alt.Color(field='Fechado dentro do SLA', type="nominal",
                                    scale=alt.Scale(domain=['SIM', 'NÃO'], range=['#03d300', '#c21f05']),
                                    legend=alt.Legend(title="Dentro do SLA?")), 
                    order=alt.Order("Percentual", sort="descending"), 
                    tooltip=['Fechado dentro do SLA',
                             alt.Tooltip(field="numero", title="Contagem"),
                             alt.Tooltip(field="Percentual", format=".1f", title="%")]
                ).properties(
                    title="Percentual de Solicitações Fechadas Dentro/Fora do SLA", 
                    width=400,
                    height=450
                )
                text = chart.mark_text(radius=140).encode(
                    text=alt.Text("Percentual", format=".1f"),
                    order=alt.Order("Percentual", sort="descending"),
                    color=alt.value("black") 
                )
                return chart + text 

            if not grouped_data2.empty:
                chart = criar_grafico_pizza(grouped_data2)
                st.altair_chart(chart, use_container_width=True)
            else:
                st.warning("Não há dados de solicitações fechadas para exibir no gráfico de pizza.")


            with st.expander("Ver dados do gráfico de SLA"):
                st.dataframe(grouped_data2)

        st.subheader('Tabela Completa SAC')
        st.dataframe(Tabela_sac_top[~Tabela_sac_top['Fechado dentro do SLA'].isin(['NÃO APLICÁVEL'])].reset_index(drop=True))
        with st.sidebar.container(height=450, border=False):
            st.markdown("")
    criar_interface()

if __name__ == "__main__":
    page2()