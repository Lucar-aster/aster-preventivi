import streamlit as st
import pandas as pd

supabase = st.session_state["supabase"]

# Caricamento tabelle per le associazioni
@st.cache_data(ttl=600)
def load_modelli():
    res = supabase.table("catalogo_modelli").select("*").order("codice").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

@st.cache_data(ttl=600)
def load_accessori():
    res = supabase.table("catalogo_accessori").select("*").order("nome").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

def load_accessori_associati(modello_id):
    res = supabase.table("modelli_accessori_default")\
        .select("id, quantita, catalogo_accessori(id, nome, prezzo)")\
        .eq("modello_id", modello_id).execute()
    return res.data if res.data else []

st.title("🧱 Configurazione Modelli Standard")

# FORM DI REGISTRAZIONE NUOVO MODELLO
with st.form("new_model", clear_on_submit=True):
    st.subheader("➕ Registra Nuovo Modulo Modello Master")
    
    col_a1, col_a2 = st.columns([1, 2])
    with col_a1:
        codice = st.text_input("Codice Identificativo (es. B3C-60, B_LAVELLO)")
    with col_a2:
        descrizione = st.text_input("Descrizione Modulo (es. Base 3 Cassetti, Base Lavello 2 Ante)")
        
    c1, c2, c3 = st.columns(3)
    tipo = c2.selectbox("Macro Famiglia", ["Base", "Pensile", "Colonna", "Gola", "Zoccolo", "Accessorio"])
    metodo = c3.selectbox("Metodo Calcolo Costo", ["superficie", "lineare"])
    
    # Defaults intelligenti per i ripiani
    default_ripiani = 1 if tipo == "Base" else (2 if tipo == "Pensile" else (4 if tipo == "Colonna" else 0))
    with c1:
        n_ripiani = st.number_input("N. Ripiani di Default", min_value=0, value=default_ripiani, step=1)

    st.markdown("**Meccanica Interna (Cassetti e Cestoni)**")
    cx1, cx2 = st.columns(2)
    n_cassetti = cx1.number_input("Numero di Cassetti (Sponda H120)", min_value=0, value=0, step=1)
    n_cestelli = cx2.number_input("Numero di Cestelli/Cestoni (Sponda H240)", min_value=0, value=0, step=1)

    st.markdown("**Misure Standard di Fabbrica (mm)**")
    d1, d2, d3, d4 = st.columns(4)
    l_std = d1.number_input("Larghezza Standard (L)", value=600, step=50)
    p_std = d2.number_input("Profondità Standard (P)", value=560, step=10)
    h_std = d3.number_input("Altezza Standard (H)", value=720, step=10)
    h_eldom = d4.number_input("Spazio Elettrodomestico (H Eldom)", value=0, step=10)
    
    if st.form_submit_button("🚀 Pubblica Modulo in Libreria Master", type="primary"):
        if codice:
            supabase.table("catalogo_modelli").insert({
                "codice": codice, "descrizione": descrizione, "tipo": tipo, "metodo_calcolo": metodo,
                "n_ripiani": int(n_ripiani), "n_cassetti": int(n_cassetti), "n_cestelli": int(n_cestelli),
                "h_eldom": int(h_eldom), "l_std": l_std, "p_std": p_std, "h_std": h_std,
                "mq_cassa_std": 0.0, "mq_schiena_std": 0.0, "mq_ante_std": 0.0
            }).execute()
            st.cache_data.clear()
            st.success(f"Modulo '{codice}' aggiunto!")
            st.rerun()

# SEZIONE TABELLARE: ASSOCIAZIONE ACCESSORI DI DEFAULT
st.markdown("---")
st.subheader("🛠️ Associa Accessori Meccanici di Default ai Modelli")
df_modelli = load_modelli()
df_accessori = load_accessori()

if not df_modelli.empty and not df_accessori.empty:
    col_sel1, col_sel2 = st.columns([2, 1])
    with col_sel1:
        modello_scelto = st.selectbox("1. Scegli il Modello Master da mappare", df_modelli['codice'].tolist(), key="sel_mod_acc")
    
    modello_id = df_modelli[df_modelli['codice'] == modello_scelto].iloc[0]['id']
    
    # Mostra accessori attualmente associati
    acc_associati = load_accessori_associati(modello_id)
    if acc_associati:
        st.markdown("**Accessori inclusi di default in questo modello:**")
        for a in acc_associati:
            acc_data = a['catalogo_accessori']
            st.caption(f"• {acc_data['nome']} (Q.tà: {a['quantita']}) - € {acc_data['prezzo']} cad. [ID Link: {a['id']}]")
    else:
        st.info("Nessun accessorio ancora associato a questo modello standard.")
        
    # Form per aggiungere un accessorio alla tabella di giunzione
    with st.popover("➕ Associa Nuovo Accessorio a questo Modello"):
        sub_acc = st.selectbox("Seleziona Articolo Ferramenta", df_accessori['nome'].tolist())
        sub_qta = st.number_input("Quantità da includere", min_value=1, value=1)
        if st.button("Conferma Legame Modello-Accessorio"):
            acc_id = df_accessori[df_accessori['nome'] == sub_acc].iloc[0]['id']
            supabase.table("modelli_accessori_default").insert({
                "modello_id": modello_id, "accessorio_id": acc_id, "quantita": int(sub_qta)
            }).execute()
            st.success("Associazione salvata nel database!")
            st.rerun()

if not df_modelli.empty:
    st.markdown("---")
    st.subheader("📚 Riepilogo Libreria Master")
    st.dataframe(df_modelli[['codice', 'descrizione', 'tipo', 'n_ripiani', 'n_cassetti', 'n_cestelli', 'h_eldom', 'l_std', 'p_std', 'h_std']], hide_index=True, use_container_width=True)
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
