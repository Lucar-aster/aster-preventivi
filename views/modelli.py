import streamlit as st
import pandas as pd

supabase = st.session_state["supabase"]

@st.cache_data(ttl=600)
def load_modelli():
    res = supabase.table("catalogo_modelli").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

st.title("🧱 Configurazione Modelli Standard")
st.markdown("Definisci i moduli standard di produzione con le relative dimensioni $STD$ e i consumi proporzionali teorici.")

with st.form("new_model", clear_on_submit=True):
    st.subheader("➕ Registra Nuovo Modulo Modello")
    c1, c2, c3 = st.columns(3)
    codice = c1.text_input("Codice Identificativo (es. B1A-60)")
    tipo = c2.selectbox("Macro Famiglia", ["Base", "Pensile", "Colonna", "Gola", "Zoccolo"])
    metodo = c3.selectbox("Metodo Calcolo", ["superficie", "lineare"])
    
    st.markdown("**Misure Standard di Fabbrica (mm)**")
    d1, d2, d3 = st.columns(3)
    l_std = d1.number_input("L Std", value=600)
    p_std = d2.number_input("P Std", value=560)
    h_std = d3.number_input("H Std", value=720)
    
    st.markdown("**Consumo Teorico Materiali a Misure Standard ($MQ$)**")
    m1, m2, m3 = st.columns(3)
    mq_c = m1.number_input("Cassa 18mm ($MQ$)", min_value=0.0, format="%.3f")
    mq_s = m2.number_input("Schiena 8mm ($MQ$)", min_value=0.0, format="%.3f")
    mq_a = m3.number_input("Ante ($MQ$)", min_value=0.0, format="%.3f")
    
    if st.form_submit_button("🚀 Pubblica Modulo in Libreria Master", type="primary"):
        if codice:
            supabase.table("catalogo_modelli").insert({
                "codice": codice, "tipo": tipo, "metodo_calcolo": metodo,
                "l_std": l_std, "p_std": p_std, "h_std": h_std,
                "mq_cassa_std": mq_c, "mq_schiena_std": mq_s, "mq_ante_std": mq_a
            }).execute()
            st.cache_data.clear()
            st.rerun()

df = load_modelli()
if not df.empty:
    st.subheader("📚 Libreria Moduli Abilitati")
    st.dataframe(df[['codice', 'tipo', 'metodo_calcolo', 'l_std', 'p_std', 'h_std', 'mq_cassa_std', 'mq_schiena_std', 'mq_ante_std']], hide_index=True, use_container_width=True)
