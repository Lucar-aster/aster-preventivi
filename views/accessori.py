import streamlit as st
import pandas as pd

supabase = st.session_state["supabase"]

@st.cache_data(ttl=600)
def load_accessori():
    res = supabase.table("catalogo_accessori").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

st.title("🛠️ Catalogo Ferramenta e Accessori")
st.markdown("Gestisci gli articoli di ferramenta commerciale (guide, cerniere, illuminazione, estraibili).")

with st.expander("➕ Inserisci Nuovo Elemento Meccanico"):
    with st.form("new_acc", clear_on_submit=True):
        nome = st.text_input("Descrizione / Codice Fornitore")
        cat = st.text_input("Famiglia Elemento (es. Cerniere, Guide)", value="Generico")
        prezzo = st.number_input("Costo Unitario d'Acquisto (€)", min_value=0.0, step=0.05)
        
        if st.form_submit_button("Salva Elemento"):
            if nome:
                supabase.table("catalogo_accessori").insert({"nome": nome, "categoria_accessorio": cat, "prezzo": prezzo}).execute()
                st.cache_data.clear()
                st.rerun()

df = load_accessori()
if not df.empty:
    df_edit = df[['id', 'nome', 'categoria_accessorio', 'prezzo']].copy()
    cambiamenti = st.data_editor(df_edit, disabled=["id"], hide_index=True, use_container_width=True)
    
    if st.button("💾 Salva Modifiche Ferramenta", type="primary"):
        for idx, riga in cambiamenti.iterrows():
            orig = df[df['id'] == riga['id']].iloc[0]
            if riga['nome'] != orig['nome'] or riga['categoria_accessorio'] != orig['categoria_accessorio'] or float(riga['prezzo']) != float(orig['prezzo']):
                supabase.table("catalogo_accessori").update({
                    "nome": riga['nome'], "categoria_accessorio": riga['categoria_accessorio'], "prezzo": float(riga['prezzo'])
                }).eq("id", riga['id']).execute()
        st.cache_data.clear()
        st.rerun()
