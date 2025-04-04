import streamlit as st # type: ignore
import mysql.connector # type: ignore
import pandas as pd # type: ignore
import altair as alt # type: ignore
import numpy as np
from datetime import datetime
import sidetable as stb # type: ignore

def conectar_ao_banco():
    return mysql.connector.connect(
        host=st.secrets["database"]["host"],
        port=st.secrets["database"]["port"],
        user=st.secrets["database"]["user"],
        password=st.secrets["database"]["password"],
        database=st.secrets["database"]["database"]
    )

def listar_tabelas(connection):
    cursor = connection.cursor()
    cursor.execute("SHOW TABLES")
    tabelas = [tabela[0] for tabela in cursor.fetchall()]
    cursor.close()
    return tabelas

def buscar_dados(connection, tabela):
    query = f"SELECT * FROM {tabela}"
    cursor = connection.cursor()
    cursor.execute(query)
    dados = cursor.fetchall()
    colunas = [i[0] for i in cursor.description]
    df = pd.DataFrame(dados, columns=colunas)
    cursor.close()
    return df

def page1():

    def criar_interface():
        hoje = (datetime.now().strftime('%d/%m/%Y'))
        st.markdown(f"<h1 style='text-align: center;'>SAC's em aberto até {hoje}</h1>", unsafe_allow_html=True)
        st.divider()
        Tabela_sac_top = pd.DataFrame(buscar_dados(conectar_ao_banco(), 'SAC'))
        Log_alteracao_fornecedor = pd.DataFrame(buscar_dados(conectar_ao_banco(), 'Log_alteracao_fornecedor'))
        Tabela_sac_top['Dias Desde Abertura'] = (
            datetime.now() - pd.to_datetime(Tabela_sac_top['dt_solicitacao'])
        ).dt.days
        Tabela_sac_top['Dias Desde fechamento'] = (
            datetime.now() - pd.to_datetime(Tabela_sac_top['dt_encerramento'])
        ).dt.days
        Tabela_sac_top['Possui Data Finalização?'] = np.where(
            Tabela_sac_top['dt_encerramento'].isnull(),
            'NÃO',
            'SIM'
        )

        sla_mapping = {'Alta': 1, 'Critica': 1, 'Média': 4, 'Baixa': 8, 'Baixa Planejada': 8}
        Tabela_sac_top['SLA_map'] = Tabela_sac_top['criticidade'].map(sla_mapping)
        #Tabela_sac_top['SLA_map'] = Tabela_sac_top['SLA_map'].astype(int)
        # Comparando a diferença de dias com o SLA e criando a nova coluna
        Tabela_sac_top['Dias Abertura > SLA map'] = np.where(
            Tabela_sac_top['Dias Desde Abertura'] > Tabela_sac_top['SLA_map'],
            'SIM',
            'NÃO'
        )


        # (Assumindo que Tabela_sac_top já foi carregada e processada como antes)

        col1, col2 = st.columns(2)

        with col1:
            # Filtra dados onde NÃO há data de finalização
            data_col1_abertos = Tabela_sac_top[Tabela_sac_top['Possui Data Finalização?'] == 'NÃO'].copy()
            # Agrupa por tipo e se os dias abertos já ultrapassaram o SLA mapeado
            grouped_data_abertos = data_col1_abertos.groupby(["tipo_solicitacao", 'Dias Abertura > SLA map']).agg(numero=('numero', 'nunique')).reset_index()

            # Verifica se há dados para plotar
            if not grouped_data_abertos.empty:
                bar_chart_abertos = alt.Chart(grouped_data_abertos).mark_bar().encode(
                    x=alt.X("tipo_solicitacao", title="Tipo de Solicitação"),
                    y=alt.Y('numero', title="Número de Solicitações Abertas"),
                    tooltip=['tipo_solicitacao', 'numero', 'Dias Abertura > SLA map'],
                    # --- MODIFICAÇÃO AQUI ---
                    color=alt.Color('Dias Abertura > SLA map',
                                    scale=alt.Scale(domain=['SIM', 'NÃO'], range=['#c21f05', '#03d300']), # Aplicando cores: SIM (ultrapassou) = Vermelho, NÃO (ainda não) = Verde
                                    legend=alt.Legend(title="Dias Abertos > SLA?"))
                    # --- FIM DA MODIFICAÇÃO ---
                ).properties(
                    title='Solicitações Abertas por Tipo e Situação de SLA', # Título ajustado
                    # width e height podem ser removidos se usar use_container_width=True
                )

                final_chart_abertos = bar_chart_abertos.interactive()
                st.altair_chart(final_chart_abertos, use_container_width=True)

                with st.expander("Ver dados do gráfico de Tipo (Abertos)"):
                    st.dataframe(grouped_data_abertos)
            else:
                st.warning("Não há dados de solicitações abertas para exibir no gráfico de barras por tipo.")


        with col2:
            # Filtra dados onde NÃO há data de finalização
            data_col2_abertos = Tabela_sac_top[Tabela_sac_top['Possui Data Finalização?'] == 'NÃO'].copy()
            # Agrupa apenas pela situação de SLA ('Dias Abertura > SLA map')
            # Garante que apenas 'SIM' e 'NÃO' sejam considerados
            grouped_data2_abertos = data_col2_abertos[data_col2_abertos['Dias Abertura > SLA map'].isin(['SIM', 'NÃO'])] \
                                    .groupby(['Dias Abertura > SLA map']).agg(numero=('numero', 'nunique')).reset_index()

            # Criar gráfico de pizza (arco/donut) - Usando uma função similar à anterior para consistência
            def criar_grafico_pizza_abertos(dados):
                if not dados.empty and dados['numero'].sum() > 0:
                    dados['Percentual'] = dados['numero'] / dados['numero'].sum() * 100
                else:
                    dados['Percentual'] = 0

                chart = alt.Chart(dados).mark_arc(outerRadius=120).encode(
                    theta=alt.Theta(field="Percentual", type="quantitative", stack=True),
                    # --- MODIFICAÇÃO AQUI ---
                    color=alt.Color(field='Dias Abertura > SLA map', type="nominal",
                                    scale=alt.Scale(domain=['SIM', 'NÃO'], range=['#c21f05', '#03d300']), # Aplicando cores: SIM (ultrapassou) = Vermelho, NÃO (ainda não) = Verde
                                    legend=alt.Legend(title="Dias Abertos > SLA?")),
                    # --- FIM DA MODIFICAÇÃO ---
                    order=alt.Order("Percentual", sort="descending"),
                    tooltip=['Dias Abertura > SLA map',
                            alt.Tooltip(field="numero", title="Contagem"),
                            alt.Tooltip(field="Percentual", format=".1f", title="%")]
                ).properties(
                    title="Percentual de Solicitações Abertas por Situação de SLA", # Título ajustado
                )
                # Adiciona texto (opcional, mas consistente com o outro gráfico)
                text = chart.mark_text(radius=140).encode(
                    text=alt.Text("Percentual", format=".1f"),
                    order=alt.Order("Percentual", sort="descending"),
                    color=alt.value("black")
                )
                return chart + text

            # Verifica se há dados antes de tentar criar o gráfico
            if not grouped_data2_abertos.empty:
                chart_abertos = criar_grafico_pizza_abertos(grouped_data2_abertos)
                st.altair_chart(chart_abertos, use_container_width=True)
            else:
                st.warning("Não há dados de solicitações abertas para exibir no gráfico de pizza por SLA.")

            with st.expander("Ver dados do gráfico de Situação SLA (Abertos)"):
                st.dataframe(grouped_data2_abertos)

        st.subheader('Tabela')
        st.dataframe(data_col1_abertos.reset_index(drop=True))


        with st.sidebar.container(height=450, border=False):
            st.markdown("")



    criar_interface() 

if __name__ == "__main__":
    page1()