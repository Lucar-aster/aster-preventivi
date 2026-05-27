import streamlit as st
import pandas as pd

supabase = st.session_state["supabase"]

@st.cache_data(ttl=600)
def load_materiali():
    res = supabase.table("materiali").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

st.title("🪵 Archivio e Listino Materiali")
st.markdown("Gestisci i materiali di capitolato e i relativi prezzi al metro quadro ($MQ$) o metro lineare ($ML$).")

# Form inserimento
with st.expander("➕ Inserisci Nuovo Materiale nel Database", expanded=False):
    with st.form("new_material", clear_on_submit=True):
        nome = st.text_input("Nome Finitura / Materiale")
        cat = st.selectbox("Categoria", ["cassa", "anta", "lineare"])
        c1, c2 = st.columns(2)
        p_mq = c1.number_input("Prezzo al MQ (€)", min_value=0.0, step=0.1)
        p_ml = c2.number_input("Prezzo al ML (€) - Solo per Gole/Zoccoli", min_value=0.0, step=0.1)
        
        if st.form_submit_button("Salva Riga Listino", type="primary"):
            if nome:
                supabase.table("materiali").insert({"nome": nome, "categoria": cat, "prezzo_mq": p_mq, "prezzo_ml": p_ml}).execute()
                st.cache_data.clear()
                st.success("Materiale inserito!")
                st.rerun()

# Editor Tabellare di modifica rapida
df = load_materiali()
if not df.empty:
    df_edit = df[['id', 'nome', 'categoria', 'prezzo_mq', 'prezzo_ml']].copy()
    cambiamenti = st.data_editor(df_edit, disabled=["id", "categoria"], hide_index=True, use_container_width=True)
    
    if st.button("💾 Applica e Salva Modifiche Listino", type="primary"):
        for idx, riga in cambiamenti.iterrows():
            orig = df[df['id'] == riga['id']].iloc[0]
            if riga['nome'] != orig['nome'] or float(riga['prezzo_mq']) != float(orig['prezzo_mq']) or float(riga['prezzo_ml']) != float(orig['prezzo_ml']):
                supabase.table("materiali").update({
                    "nome": riga['nome'], "prezzo_mq": float(riga['prezzo_mq']), "prezzo_ml": float(riga['prezzo_ml'])
                }).eq("id", riga['id']).execute()
        st.cache_data.clear()
        st.success("Listino Database Aggiornato!")
        st.rerun()
