import streamlit as st
import pandas as pd

# Recupero dell'istanza client Supabase dallo stato della sessione
supabase = st.session_state["supabase"]

st.title("🎨 Gestionale Catalogo Materiali e Finiture")
st.caption("Configura qui l'anagrafica master dei materiali, impostando tipologia, spessori e prezzi al metro quadro.")

# =========================================================================
# FUNZIONE DI CARICAMENTO DATI
# =========================================================================
def load_catalogo_materiali():
    try:
        # Seleziona tutti i campi della tabella delle finiture
        res = supabase.table("catalogo_finiture").select("*").order("nome").execute()
        return res.data if res.data else []
    except Exception as e:
        st.error(f"Errore nel caricamento della tabella 'catalogo_finiture': {str(e)}")
        return []

# Caricamento e normalizzazione dei dati in un DataFrame
materiali_esistenti = load_catalogo_materiali()
df_master = pd.DataFrame(materiali_esistenti)

# Definizione preventiva delle colonne attese nel DB per evitare eccezioni di struttura
colonne_richieste = ["id", "nome", "tipo", "spessore", "prezzo_mq"]
for col in colonne_richieste:
    if df_master.empty or col not in df_master.columns:
        df_master[col] = None

# Suddivisione dei dati caricati per popolare i due contesti operativi (Cassa e Anta)
df_cassa_init = df_master[df_master["tipo"] == "Cassa"].copy()
df_ante_init = df_master[df_master["tipo"] == "Anta"].copy()

# Garantisce la presenza delle colonne minime per i data_editor anche in caso di tabella vuota
if df_cassa_init.empty:
    df_cassa_init = pd.DataFrame(columns=["id", "nome", "spessore", "prezzo_mq"])
if df_ante_init.empty:
    df_ante_init = pd.DataFrame(columns=["id", "nome", "spessore", "prezzo_mq"])

# =========================================================================
# INTERFACCIA UTENTE: SUDDIVISIONE IN TAB
# =========================================================================
tab_cassa, tab_ante = st.tabs(["📦 Materiale Cassa", "🚪 Materiale Anta"])

with tab_cassa:
    st.subheader("Configurazione Finiture, Spessori e Prezzi Cassa")
    st.caption("Inserisci o modifica i materiali strutturali dedicati alle casse dei moduli.")
    
    ed_cassa = st.data_editor(
        df_cassa_init[["id", "nome", "spessore", "prezzo_mq"]],
        column_config={
            "id": st.column_config.TextColumn("ID Sistema", disabled=True, width="small"),
            "nome": st.column_config.TextColumn("Nome Materiale / Colore Cassa", required=True, width="large"),
            "spessore": st.column_config.NumberColumn("Spessore (mm)", min_value=1, default=18, format="%d", required=True, width="medium"),
            "prezzo_mq": st.column_config.NumberColumn("Prezzo al Mq (€)", min_value=0.0, default=0.0, format="€ %.2f", required=True, width="medium")
        },
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        key="griglia_materiali_cassa"
    )

with tab_ante:
    st.subheader("Configurazione Finiture, Spessori e Prezzi Ante")
    st.caption("Inserisci o modifica i materiali e le finiture estetiche dedicate ai frontali e alle ante.")
    
    ed_ante = st.data_editor(
        df_ante_init[["id", "nome", "spessore", "prezzo_mq"]],
        column_config={
            "id": st.column_config.TextColumn("ID Sistema", disabled=True, width="small"),
            "nome": st.column_config.TextColumn("Nome Materiale / Finitura Anta", required=True, width="large"),
            "spessore": st.column_config.NumberColumn("Spessore (mm)", min_value=1, default=22, format="%d", required=True, width="medium"),
            "prezzo_mq": st.column_config.NumberColumn("Prezzo al Mq (€)", min_value=0.0, default=0.0, format="€ %.2f", required=True, width="medium")
        },
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        key="griglia_materiali_ante"
    )

# =========================================================================
# CENTRALIZZAZIONE DEL SALVATAGGIO SU DATABASE
# =========================================================================
st.markdown("---")
if st.button("💾 SALVA MODIFICHE CATALOGO MATERIALI", type="primary", use_container_width=True):
    with st.spinner("Sincronizzazione tabelle materiali nel database..."):
        try:
            # Svuota in modo controllato la tabella master per riscrivere la nuova matrice aggiornata
            supabase.table("catalogo_finiture").delete().neq("nome", "").execute()
            
            batch_inserimento = []
            
            # 1. Parsing ed elaborazione dati dei materiali Cassa
            for _, r in ed_cassa.iterrows():
                nome_mat = str(r.get("nome")).strip() if pd.notna(r.get("nome")) else ""
                if nome_mat:
                    batch_inserimento.append({
                        "nome": nome_mat,
                        "tipo": "Cassa",
                        "spessore": int(r["spessore"]) if pd.notna(r.get("spessore")) else 18,
                        "prezzo_mq": float(r["prezzo_mq"]) if pd.notna(r.get("prezzo_mq")) else 0.0
                    })
            
            # 2. Parsing ed elaborazione dati dei materiali Ante
            for _, r in ed_ante.iterrows():
                nome_mat = str(r.get("nome")).strip() if pd.notna(r.get("nome")) else ""
                if nome_mat:
                    batch_inserimento.append({
                        "nome": nome_mat,
                        "tipo": "Anta",
                        "spessore": int(r["spessore"]) if pd.notna(r.get("spessore")) else 22,
                        "prezzo_mq": float(r["prezzo_mq"]) if pd.notna(r.get("prezzo_mq")) else 0.0
                    })
            
            # Esecuzione del batch insert se sono presenti righe valide
            if batch_inserimento:
                supabase.table("catalogo_finiture").insert(batch_inserimento).execute()
                st.success("🎉 Catalogo materiali, spessori e prezzi al mq allineati con successo nel database!")
            else:
                st.warning("Nessun materiale valido inserito nelle tabelle. Il catalogo è stato svuotato.")
                
            st.rerun()
            
        except Exception as e:
            st.error(f"Si è verificato un errore durante il salvataggio dei dati: {str(e)}")
