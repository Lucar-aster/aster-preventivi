import streamlit as st
import pandas as pd

supabase = st.session_state["supabase"]

# =========================================================================
# CARICAMENTO DATI CON CACHING
# =========================================================================
@st.cache_data(ttl=600)
def load_modelli():
    try:
        res = supabase.table("catalogo_modelli").select("*").order("codice").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=600)
def load_accessori():
    try:
        res = supabase.table("catalogo_accessori").select("id, nome, prezzo").order("nome").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# =========================================================================
# INTERFACCIA UTENTE
# =========================================================================
st.title("🧱 Configurazione Modelli Standard")
st.markdown("Definisci i moduli master di produzione e associa i relativi accessori direttamente dalla griglia interna.")

df_accessori = load_accessori()
lista_nomi_accessori = df_accessori['nome'].tolist() if not df_accessori.empty else []

# FORM UNIFICATO DI REGISTRAZIONE
with st.form("form_creazione_modello_master", clear_on_submit=True):
    st.subheader("➕ Registra Nuovo Modulo e Configura Accessori")
    
    # Riga 1: Codice e Descrizione
    col_a1, col_a2 = st.columns([1, 2])
    with col_a1:
        codice = st.text_input("Codice Identificativo (es. B2AN-60, B_LAVELLO)")
    with col_a2:
        descrizione = st.text_input("Descrizione Modulo (es. Base 2 Ante, Base Lavello con Bidoni)")
        
    # Riga 2: Famiglia, Calcolo e Ripiani
    c1, c2, c3 = st.columns(3)
    tipo = c2.selectbox("Macro Famiglia", ["Base", "Pensile", "Colonna", "Gola", "Zoccolo", "Accessorio"])
    metodo = c3.selectbox("Metodo Calcolo Costo", ["superficie", "lineare"])
    
    # Assegnazione dinamica dei ripiani teorici di partenza
    default_ripiani = 1 if tipo == "Base" else (2 if tipo == "Pensile" else (4 if tipo == "Colonna" else 0))
    with c1:
        n_ripiani = st.number_input("N. Ripiani di Default", min_value=0, value=default_ripiani, step=1)

    # Riga 3: Cassetti e Cestelli
    st.markdown("**Meccanica Cassetti**")
    cx1, cx2 = st.columns(2)
    n_cassetti = cx1.number_input("Numero di Cassetti (Sponda H120)", min_value=0, value=0, step=1)
    n_cestelli = cx2.number_input("Numero di Cestelli/Cestoni (Sponda H240)", min_value=0, value=0, step=1)

    # Riga 4: Dimensioni Standard
    st.markdown("**Misure Standard di Fabbrica (mm)**")
    d1, d2, d3, d4 = st.columns(4)
    l_std = d1.number_input("Larghezza Standard (L)", value=600, step=50)
    p_std = d2.number_input("Profondità Standard (P)", value=560, step=10)
    h_std = d3.number_input("Altezza Standard (H)", value=720, step=10)
    h_eldom = d4.number_input("Spazio Elettrodomestico (H Eldom)", value=0, step=10)
    
    # ---------------------------------------------------------------------
    # SEZIONE TABELLARE INTERNA: COMPONENTI E FERRAMENTA DI SERIE
    # ---------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 🛠️ Tabella Accessori di Serie per questo Modulo")
    st.caption("Usa l'ultima riga vuota contrassegnata con `+` per inserire uno o più componenti ferramentistici.")
    
    # Prepariamo la struttura dati vuota per la tabella interattiva
    df_struttura_vuota = pd.DataFrame(columns=["Nome Accessorio", "Quantità"])
    
    # Configurazione avanzata delle colonne del data_editor
    config_colonne = {
        "Nome Accessorio": st.column_config.SelectboxColumn(
            "Seleziona Articolo da Catalogo",
            options=lista_nomi_accessori,
            required=True,
            width="large"
        ),
        "Quantità": st.column_config.NumberColumn(
            "Q.tà Inclusa",
            min_value=1,
            default=1,
            required=True,
            width="small"
        )
    }
    
    # Renderizziamo il Data Editor dentro il form
    griglia_accessori = st.data_editor(
        df_struttura_vuota,
        column_config=config_colonne,
        num_rows="dynamic",  # Abilita i tasti + e - per aggiungere/rimuovere righe
        use_container_width=True,
        key="editor_accessori_nuovo_modello"
    )
    
    st.markdown("---")
    # INVIO FORM
    if st.form_submit_button("🚀 Pubblica Modulo Completo in Libreria Master", type="primary"):
        if codice:
            try:
                # 1. Inserimento del Modello Master
                res_modello = supabase.table("catalogo_modelli").insert({
                    "codice": codice, "descrizione": descrizione, "tipo": tipo, "metodo_calcolo": metodo,
                    "n_ripiani": int(n_ripiani), "n_cassetti": int(n_cassetti), "n_cestelli": int(n_cestelli),
                    "h_eldom": int(h_eldom), "l_std": l_std, "p_std": p_std, "h_std": h_std,
                    "mq_cassa_std": 0.0, "mq_schiena_std": 0.0, "mq_ante_std": 0.0
                }).execute()
                
                # Recuperiamo l'ID UUID generato automaticamente dal database
                if res_modello.data:
                    nuovo_modello_id = res_modello.data[0]['id']
                    
                    # 2. Elaborazione e inserimento batch degli accessori presenti in tabella
                    if griglia_accessori is not None and not griglia_accessori.empty:
                        batch_accessori = []
                        
                        for _, row in griglia_accessori.iterrows():
                            nome_selezionato = row.get("Nome Accessorio")
                            qta = row.get("Quantità")
                            
                            if nome_selezionato and qta:
                                # Trova l'ID corrispondente partendo dal nome selezionato
                                match_acc = df_accessori[df_accessori['nome'] == nome_selezionato]
                                if not match_acc.empty:
                                    acc_id = match_acc.iloc[0]['id']
                                    batch_accessori.append({
                                        "modello_id": nuovo_modello_id,
                                        "accessorio_id": acc_id,
                                        "quantita": int(qta)
                                    })
                        
                        # Se ci sono accessori validi inseriti, spariamo la query batch su Supabase
                        if batch_accessori:
                            supabase.table("modelli_accessori_default").insert(batch_accessori).execute()
                    
                    st.cache_data.clear()
                    st.success(f"Modulo '{codice}' e relativi accessori di serie salvati con successo!")
                    st.rerun()
            except Exception as e:
                st.error(f"Errore durante il salvataggio: {str(e)}")
        else:
            st.error("Il codice modulo è un campo identificativo obbligatorio.")

# VISUALIZZAZIONE DATABASE DI RIEPILOGO
df_modelli = load_modelli()
if not df_modelli.empty:
    st.markdown("---")
    st.subheader("📚 Moduli Abilitati a Catalogo")
    st.dataframe(
        df_modelli[['codice', 'descrizione', 'tipo', 'n_ripiani', 'n_cassetti', 'n_cestelli', 'h_eldom', 'l_std', 'p_std', 'h_std']], 
        hide_index=True, 
        use_container_width=True
    )
