import streamlit as st
import pandas as pd

supabase = st.session_state["supabase"]

@st.cache_data(ttl=600)
def load_modelli():
    try:
        res = supabase.table("catalogo_modelli").select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

st.title("🧱 Configurazione Modelli Standard")
st.markdown("Definisci i moduli master di produzione. Il sistema calcolerà automaticamente i consumi reali di materiale ($MQ$) in base alla struttura geometrica.")

with st.form("new_model", clear_on_submit=True):
    st.subheader("➕ Registra Nuovo Modulo Modello")
    
    col_a1, col_a2 = st.columns([1, 2])
    with col_a1:
        codice = st.text_input("Codice Identificativo (es. B2AN-60, C-FRIGO)")
    with col_a2:
        descrizione = st.text_input("Descrizione Modulo (es. Base 2 Ante Scorrevoli, Colonna Frigo)")
        
    c1, c2, c3 = st.columns(3)
    tipo = c2.selectbox("Macro Famiglia", ["Base", "Pensile", "Colonna", "Gola", "Zoccolo", "Accessorio"])
    metodo = c3.selectbox("Metodo Calcolo Costo", ["superficie", "lineare"])
    
    # Logica di assegnazione dinamica dei ripiani di default
    if tipo == "Base":
        default_ripiani = 1
    elif tipo == "Pensile":
        default_ripiani = 2
    elif tipo == "Colonna":
        default_ripiani = 4
    else:
        default_ripiani = 0
        
    with c1:
        n_ripiani = st.number_input("N. Ripiani di Default", min_value=0, value=default_ripiani, step=1)

    st.markdown("**Misure Standard di Fabbrica (mm)**")
    d1, d2, d3, d4 = st.columns(4)
    l_std = d1.number_input("Larghezza Standard (L)", value=600, step=50)
    p_std = d2.number_input("Profondità Standard (P)", value=560, step=10)
    h_std = d3.number_input("Altezza Standard (H)", value=720, step=10)
    h_eldom = d4.number_input("Spazio Elettrodomestico (H Eldom)", value=0, step=10, help="Altezza in mm occupata da forno, frigo, ecc. Verrà sottratta dal calcolo dell'anta.")
    
    if st.form_submit_button("🚀 Pubblica Modulo in Libreria Master", type="primary"):
        if codice:
            supabase.table("catalogo_modelli").insert({
                "codice": codice, 
                "descrizione": descrizione,
                "tipo": tipo, 
                "metodo_calcolo": metodo,
                "n_ripiani": int(n_ripiani),
                "h_eldom": int(h_eldom),
                "l_std": l_std, 
                "p_std": p_std, 
                "h_std": h_std,
                # Impostiamo a 0 i vecchi campi manuali MQ poiché ora usiamo le formule geometriche stabili
                "mq_cassa_std": 0.0, "mq_schiena_std": 0.0, "mq_ante_std": 0.0
            }).execute()
            st.cache_data.clear()
            st.success(f"Modulo '{codice}' aggiunto con successo alla libreria master!")
            st.rerun()
        else:
            st.error("Il codice modulo è un campo identificativo obbligatorio.")

df = load_modelli()
if not df.empty:
    st.subheader("📚 Libreria Moduli Abilitati a Catalogo")
    # Ordiniamo le colonne per una lettura pulita
    colonne_visibili = ['codice', 'descrizione', 'tipo', 'metodo_calcolo', 'n_ripiani', 'h_eldom', 'l_std', 'p_std', 'h_std']
    # Controllo di sicurezza se alcune colonne vecchie mancano nel df specchio
    colonne_presenti = [c for c in colonne_visibili if c in df.columns]
    st.dataframe(df[colonne_presenti], hide_index=True, use_container_width=True)
