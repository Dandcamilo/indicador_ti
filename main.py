import streamlit as st # type: ignore
from views.page1 import page1
from views.page2 import page2
from views.page3 import page3

from PIL import Image

def main():
    
    st.set_page_config(page_title="Indicadores - TI", page_icon=r'', layout="wide")
    st.sidebar.image(Image.open(r'logo_unimed.jpeg'))

    pages = {
        "❌ Não Finalizados": page1,
        "✅ Finalizados": page2,
        "🛠 Customização": page3,
    }

    page = st.sidebar.selectbox("Selecione:", list(pages.keys()))

    if page == "❌ Não Finalizados":
        pages[page]()
    elif page == "✅ Finalizados":
        pages[page]()
    elif page == "🛠 Customização":
        pages[page]()
    # --- 8. Footer Implementation ---
    with open('static/footer.html', 'r') as f:
        footer_html = f.read()
    st.sidebar.markdown(footer_html, unsafe_allow_html=True)

if __name__ == '__main__':
    main()