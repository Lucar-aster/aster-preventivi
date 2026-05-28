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

def load_accessori_per_modello(modello_id):
    """Recupera gli accessori associati a un modello e li formatta per il data_editor."""
    try:
        res = (supabase.table("modelli_accessori_default")
               .select("quantita, catalogo_accessori(nome)")
               .eq("modello_id", modello_id)
               .execute())
        if res.data:
            righe = []
            for item in res.data:
                nome = item.get("catalogo_accessori", {}).get("nome")
                qta = item.get("quantita")
                if nome:
                    righe.append({"Nome Accessorio": nome, "Quantità": qta})
            return pd.DataFrame(righe)
        return pd.DataFrame(columns=["Nome Accessorio", "Quantità"])
    except Exception:
        return pd.DataFrame(columns=["Nome Accessorio", "Quantità"])

# =========================================================================
# CONFIGURAZIONE INTERFACCIA E TAB
# =========================================================================
st.title("🧱 Gestione Libreria Modelli Master")

df_modelli = load_modelli()
df_accessori = load_accessori()
lista_nomi_accessori = df_accessori['nome'].tolist() if not df_accessori.empty else []

# Configurazione riutilizzabile per le colonne dei due data editor
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

tab_crea, tab_modifica = st.tabs(["➕ Crea Nuovo Modulo", "✏️ Modifica Modulo Esistente"])

# =========================================================================
# TAB 1: CREAZIONE NUOVO MODELLO
# =========================================================================
with tab_crea:
    with st.form("form_creazione_modello_master", clear_on_submit=True):
        st.subheader("Registra Nuovo Modulo e Configura Accessori")
        
        col_a1, col_a2 = st.columns([1, 2])
        with col_a1:
            codice = st.text_input("Codice Identificativo (es. B2AN-60)")
        with col_a2:
            descrizione = st.text_input("Descrizione Modulo (es. Base 2 Ante)")
            
        c1, c2, c3 = st.columns(3)
        tipo = c2.selectbox("Macro Famiglia", ["Base", "Pensile", "Colonna", "Gola", "Zoccolo", "Accessorio"], key="tipo_crea")
        metodo = c3.selectbox("Metodo Calcolo Costo", ["superficie", "lineare"], key="metodo_crea")
        
        default_ripiani = 1 if tipo == "Base" else (2 if tipo == "Pensile" else (4 if tipo == "Colonna" else 0))
        with c1:
            n_ripiani = st.number_input("N. Ripiani di Default", min_value=0, value=default_ripiani, step=1, key="ripiani_crea")

        st.markdown("**Meccanica Cassetti**")
        cx1, cx2 = st.columns(2)
        n_cassetti = cx1.number_input("Numero di Cassetti (Sponda H120)", min_value=0, value=0, step=1, key="cassetti_crea")
        n_cestelli = cx2.number_input("Numero di Cestelli/Cestoni (Sponda H240)", min_value=0, value=0, step=1, key="cestelli_crea")

        # 🎯 Configurazione Schiena aggiornata con le nuove opzioni
        st.markdown("**Configurazione Strutturale**")
        tipo_schiena = st.selectbox(
            "Configurazione Schiena di Default", 
            ["Standard (8mm)", "Economica (3mm)", "Nessuna"], 
            key="schiena_crea"
        )

        st.markdown("**Misure Standard di Fabbrica (mm)**")
        d1, d2, d3, d4 = st.columns(4)
        l_std = d1.number_input("Larghezza Standard (L)", value=600, step=50, key="l_crea")
        p_std = d2.number_input("Profondità Standard (P)", value=560, step=10, key="p_crea")
        h_std = d3.number_input("Altezza Standard (H)", value=720, step=10, key="h_crea")
        h_eldom = d4.number_input("Spazio Elettrodomestico (H Eldom)", value=0, step=10, key="eldom_crea")
        
        st.markdown("---")
        st.markdown("### 🛠️ Tabella Accessori di Serie")
        griglia_accessori = st.data_editor(
            pd.DataFrame(columns=["Nome Accessorio", "Quantità"]),
            column_config=config_colonne,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_accessori_nuovo"
        )
        
        if st.form_submit_button("🚀 Pubblica Modulo in Libreria Master", type="primary"):
            if codice:
                try:
                    res_modello = supabase.table("catalogo_modelli").insert({
                        "codice": codice, "descrizione": descrizione, "tipo": tipo, "metodo_calcolo": metodo,
                        "n_ripiani": int(n_ripiani), "n_cassetti": int(n_cassetti), "n_cestelli": int(n_cestelli),
                        "h_eldom": int(h_eldom), "l_std": l_std, "p_std": p_std, "h_std": h_std,
                        "mq_cassa_std": 0.0, "mq_schiena_std": 0.0, "mq_ante_std": 0.0,
                        "tipo_schiena": tipo_schiena
                    }).execute()
                    
                    if res_modello.data and griglia_accessori is not None and not griglia_accessori.empty:
                        nuovo_id = res_modello.data[0]['id']
                        batch = []
                        for _, row in griglia_accessori.iterrows():
                            n_acc = row.get("Nome Accessorio")
                            qta = row.get("Quantità")
                            if n_acc and qta:
                                m_acc = df_accessori[df_accessori['nome'] == n_acc]
                                if not m_acc.empty:
                                    batch.append({"modello_id": nuovo_id, "accessorio_id": m_acc.iloc[0]['id'], "quantita": int(qta)})
                        if batch:
                            supabase.table("modelli_accessori_default").insert(batch).execute()
                    
                    st.cache_data.clear()
                    st.success("Nuovo modello inserito!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {str(e)}")

# =========================================================================
# TAB 2: MODIFICA MODELLO ESISTENTE
# =========================================================================
with tab_modifica:
    if df_modelli.empty:
        st.info("Nessun modello disponibile per la modifica.")
    else:
        lista_codici = df_modelli['codice'].tolist()
        blocco_scelto = st.selectbox("🎯 Seleziona il Modulo Master da modificare", lista_codici, key="select_blocco_edit")
        
        dati_blocco = df_modelli[df_modelli['codice'] == blocco_scelto].iloc[0].to_dict()
        m_id = dati_blocco['id']
        
        df_acc_esistenti = load_accessori_per_modello(m_id)
        
        with st.form(f"form_modifica_{m_id}"):
            st.subheader(f"✏️ Modifica Scheda Tecnica: {blocco_scelto}")
            
            col_e1, col_e2 = st.columns([1, 2])
            with col_e1:
                codice_edit = st.text_input("Codice Identificativo", value=dati_blocco['codice'], key=f"cod_{m_id}")
            with col_e2:
                descrizione_edit = st.text_input("Descrizione Modulo", value=dati_blocco.get('descrizione', ''), key=f"desc_{m_id}")
                
            c_e1, c_e2, c_e3 = st.columns(3)
            
            famiglie = ["Base", "Pensile", "Colonna", "Gola", "Zoccolo", "Accessorio"]
            idx_fam = famiglie.index(dati_blocco['tipo']) if dati_blocco['tipo'] in famiglie else 0
            tipo_edit = c_e2.selectbox("Macro Famiglia", famiglie, index=idx_fam, key=f"tipo_{m_id}")
            
            metodi = ["superficie", "lineare"]
            idx_met = metodi.index(dati_blocco['metodo_calcolo']) if dati_blocco['metodo_calcolo'] in metodi else 0
            metodo_edit = c_e3.selectbox("Metodo Calcolo Costo", metodi, index=idx_met, key=f"met_{m_id}")
            
            with c_e1:
                n_ripiani_edit = st.number_input("N. Ripiani di Default", min_value=0, value=int(dati_blocco.get('n_ripiani', 0)), step=1, key=f"rip_{m_id}")
                
            st.markdown("**Meccanica Cassetti**")
            cx_e1, cx_e2 = st.columns(2)
            n_cassetti_edit = cx_e1.number_input("Numero di Cassetti (Sponda H120)", min_value=0, value=int(dati_blocco.get('n_cassetti', 0)), step=1, key=f"cas_{m_id}")
            n_cestelli_edit = cx_e2.number_input("Numero di Cestelli/Cestoni (Sponda H240)", min_value=0, value=int(dati_blocco.get('n_cestelli', 0)), step=1, key=f"ces_{m_id}")

            # 🎯 Configurazione Schiena aggiornata nel modulo di modifica con fallback su 'Standard (8mm)'
            st.markdown("**Configurazione Strutturale**")
            opzioni_schiena = ["Standard (8mm)", "Economica (3mm)", "Nessuna"]
            val_attuale_schiena = dati_blocco.get('tipo_schiena', 'Standard (8mm)')
            idx_schiena = opzioni_schiena.index(val_attuale_schiena) if val_attuale_schiena in opzioni_schiena else 0
            tipo_schiena_edit = st.selectbox("Configurazione Schiena", opzioni_schiena, index=idx_schiena, key=f"schiena_{m_id}")

            st.markdown("**Misure Standard di Fabbrica (mm)**")
            d_e1, d_e2, d_e3, d_e4 = st.columns(4)
            l_std_edit = d_e1.number_input("Larghezza Standard (L)", value=int(dati_blocco.get('l_std', 600)), step=50, key=f"l_{m_id}")
            p_std_edit = d_e2.number_input("Profondità Standard (P)", value=int(dati_blocco.get('p_std', 560)), step=10, key=f"p_{m_id}")
            h_std_edit = d_e3.number_input("Altezza Standard (H)", value=int(dati_blocco.get('h_std', 720)), step=10, key=f"h_{m_id}")
            h_eldom_edit = d_e4.number_input("Spazio Elettrodomestico (H Eldom)", value=int(dati_blocco.get('h_eldom', 0)), step=10, key=f"eld_{m_id}")
            
            st.markdown("---")
            st.markdown("### 🛠️ Modifica Accessori di Serie per questo Modulo")
            st.caption("Puoi modificare le quantità, aggiungere nuove righe in fondo o eliminarle selezionandole e premendo Canc.")
            
            griglia_accessori_edit = st.data_editor(
                df_acc_esistenti,
                column_config=config_colonne,
                num_rows="dynamic",
                use_container_width=True,
                key=f"editor_edit_{m_id}"
            )
            
            st.markdown("---")
            if st.form_submit_button("💾 Salva Modifiche Modulo Master", type="primary"):
                try:
                    # 1. Aggiornamento dati principali sul database
                    supabase.table("catalogo_modelli").update({
                        "codice": codice_edit, "descrizione": descrizione_edit, "tipo": tipo_edit, "metodo_calcolo": metodo_edit,
                        "n_ripiani": int(n_ripiani_edit), "n_cassetti": int(n_cassetti_edit), "n_cestelli": int(n_cestelli_edit),
                        "h_eldom": int(h_eldom_edit), "l_std": l_std_edit, "p_std": p_std_edit, "h_std": h_std_edit,
                        "tipo_schiena": tipo_schiena_edit
                    }).eq("id", m_id).execute()
                    
                    # 2. Sincronizzazione degli Accessori (Rapporto 1-a-Molti)
                    supabase.table("modelli_accessori_default").delete().eq("modello_id", m_id).execute()
                    
                    if griglia_accessori_edit is not None and not griglia_accessori_edit.empty:
                        batch_edit = []
                        for _, row in griglia_accessori_edit.iterrows():
                            n_acc = row.get("Nome Accessorio")
                            qta = row.get("Quantità")
                            if n_acc and qta:
                                m_acc = df_accessori[df_accessori['nome'] == n_acc]
                                if not m_acc.empty:
                                    batch_edit.append({
                                        "modello_id": m_id,
                                        "accessorio_id": m_acc.iloc[0]['id'],
                                        "quantita": int(qta)
                                    })
                        if batch_edit:
                            supabase.table("modelli_accessori_default").insert(batch_edit).execute()
                            
                    st.cache_data.clear()
                    st.success(f"Modulo '{codice_edit}' aggiornato correttamente in libreria!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore durante l'aggiornamento: {str(e)}")

# =========================================================================
# RIEPILOGO GENERALE
# =========================================================================
if not df_modelli.empty:
    st.markdown("---")
    st.subheader("📚 Moduli Attualmente a Catalogo")
    
    if "tipo_schiena" not in df_modelli.columns:
        df_modelli["tipo_schiena"] = "Standard (8mm)"
        
    st.dataframe(
        df_modelli[['codice', 'descrizione', 'tipo', 'tipo_schiena', 'n_ripiani', 'n_cassetti', 'n_cestelli', 'h_eldom', 'l_std', 'p_std', 'h_std']], 
        hide_index=True, 
        use_container_width=True
    )
