import streamlit as st
import pandas as pd

supabase = st.session_state["supabase"]

# =========================================================================
# FUNCTIONS: CARICAMENTO E COSTRUZIONE DATI
# =========================================================================
def load_progetti():
    # 🔄 Aggiornato: usa "nome_progetti"
    res = supabase.table("progetti").select("id, nome_progetti").order("created_at", desc=True).execute()
    return res.data if res.data else []

def load_tipologie(progetto_id):
    # 🔄 Aggiornato: ordina per "nome_cucina"
    res = supabase.table("tipologie_cucine").select("*").eq("progetto_id", progetto_id).order("nome_cucina").execute()
    return res.data if res.data else []

def load_catalogo_modelli():
    res = supabase.table("catalogo_modelli").select("*").order("codice").execute()
    return res.data if res.data else []

def load_catalogo_accessori():
    res = supabase.table("catalogo_accessori").select("id, nome, prezzo").order("nome").execute()
    return res.data if res.data else []

def load_istanze_blocchi(tipologia_id):
    """Carica i moduli inseriti nell'ambiente corrente includendo i dati del catalogo master"""
    res = (supabase.table("istanze_blocchi")
           .select("id, modello_id, larghezza, profondita, altezza, quantita, note, catalogo_modelli(*)")
           .eq("tipologia_id", tipologia_id)
           .execute())
    return res.data if res.data else []

def load_accessori_istanza(istanza_blocco_id):
    res = (supabase.table("istanze_blocchi_accessori")
           .select("id, accessorio_id, quantita, catalogo_accessori(nome, prezzo)")
           .eq("istanza_blocco_id", istanza_blocco_id)
           .execute())
    return res.data if res.data else []

# =========================================================================
# ENGINE: LOGICA DI CLONAZIONE AMBIENTE (TIPOLOGIA)
# =========================================================================
def clonare_tipologia(tipologia_sorgente_id, progetto_id, nuovo_nome):
    try:
        # 1. Crea la nuova tipologia (🔄 Aggiornato: colonna nome_cucina)
        res_tip = supabase.table("tipologie_cucine").insert({
            "progetto_id": progetto_id,
            "nome_cucina": nuovo_nome
        }).execute()
        
        if not res_tip.data:
            return False
        nuova_tipologia_id = res_tip.data[0]['id']
        
        # 2. Recupera i blocchi della tipologia sorgente
        blocchi_vecchi = supabase.table("istanze_blocchi").select("*").eq("tipologia_id", tipologia_sorgente_id).execute()
        
        for blocco in blocchi_vecchi.data:
            vecchio_blocco_id = blocco['id']
            # Inserisce il blocco clonato
            res_blocco = supabase.table("istanze_blocchi").insert({
                "tipologia_id": nuova_tipologia_id,
                "modello_id": blocco['modello_id'],
                "larghezza": blocco['larghezza'],
                "profondita": blocco['profondita'],
                "altezza": blocco['altezza'],
                "quantita": blocco['quantita'],
                "note": blocco.get('note', '')
            }).execute()
            
            if res_blocco.data:
                nuovo_blocco_id = res_blocco.data[0]['id']
                # 3. Recupera e clona gli accessori di quel blocco
                acc_vecchi = supabase.table("istanze_blocchi_accessori").select("*").eq("istanza_blocco_id", vecchio_blocco_id).execute()
                batch_acc = []
                for acc in acc_vecchi.data:
                    batch_acc.append({
                        "istanza_blocco_id": nuovo_blocco_id,
                        "accessorio_id": acc['accessorio_id'],
                        "quantita": acc['quantita']
                    })
                if batch_acc:
                    supabase.table("istanze_blocchi_accessori").insert(batch_acc).execute()
        return True
    except Exception as e:
        st.error(f"Errore clonazione: {str(e)}")
        return False

# =========================================================================
# INTERFACCIA UTENTE (UI)
# =========================================================================
st.title("📊 Preventivatore Avanzato")

# 1. SELEZIONE PROGETTO GENERALIZZATO
progetti = load_progetti()
if not progetti:
    st.info("👋 Nessun progetto presente nel sistema. Creane uno rapido per iniziare:")
    nuovo_p_nome = st.text_input("Nome Nuova Commessa / Cliente")
    if st.button("➕ Crea Progetto"):
        if nuovo_p_nome:
            # 🔄 Aggiornato: colonna nome_progetti
            supabase.table("progetti").insert({"nome_progetti": nuovo_p_nome}).execute()
            st.rerun()
    st.stop()

col_p1, col_p2 = st.columns([2, 1])
# 🔄 Aggiornato: legge p['nome_progetti']
list_nomi_prog = [p['nome_progetti'] for p in progetti]
proj_scelto_nome = col_p1.selectbox("📂 Seleziona la Commessa / Cliente", list_nomi_prog)
prog_id = next(p['id'] for p in progetti if p['nome_progetti'] == proj_scelto_nome)

# Carica tipologie associate
tipologie = load_tipologie(prog_id)

# 2. PANNELLO GESTIONE TIPOLOGIE (AMBIENTI)
with st.sidebar:
    st.header("🏢 Stanze / Tipologie")
    
    # Creazione Nuova Tipologia
    with st.expander("➕ Nuova Tipologia", expanded=False):
        nome_nuova_tip = st.text_input("Nome (es. Cucina Isola, Kitchenette)")
        if st.button("Salva Stanza", use_container_width=True):
            if nome_nuova_tip:
                # 🔄 Aggiornato: colonna nome_cucina
                supabase.table("tipologie_cucine").insert({"progetto_id": prog_id, "nome_cucina": nome_nuova_tip}).execute()
                st.rerun()
                
    # Clonazione Tipologia Esistente
    if tipologie:
        with st.expander("👯 Clona Ambiente", expanded=False):
            # 🔄 Aggiornato: legge t['nome_cucina']
            tip_da_clonare = st.selectbox("Sorgente", [t['nome_cucina'] for t in tipologie], key="src_clone")
            nome_clone = st.text_input("Nome Clona", value=f"Copia di {tip_da_clonare}")
            if st.button("Esegui Clonazione", use_container_width=True):
                id_src = next(t['id'] for t in tipologie if t['nome_cucina'] == tip_da_clonare)
                if clonare_tipologia(id_src, prog_id, nome_clone):
                    st.success("Ambiente duplicato!")
                    st.rerun()

        # Eliminazione Ambiente
        with st.expander("🗑️ Elimina Ambiente", expanded=False):
            # 🔄 Aggiornato: legge t['nome_cucina']
            tip_da_del = st.selectbox("Seleziona da rimuovere", [t['nome_cucina'] for t in tipologie], key="src_del")
            if st.button("⚠️ Elimina Definitivamente", type="primary", use_container_width=True):
                id_del = next(t['id'] for t in tipologie if t['nome_cucina'] == tip_da_del)
                supabase.table("tipologie_cucine").delete().eq("id", id_del).execute()
                st.rerun()

if not tipologie:
    st.warning("Crea almeno una Tipologia/Stanza nel menu laterale per iniziare a comporre il preventivo.")
    st.stop()

# Selezione della tipologia attiva sul piano di lavoro
# 🔄 Aggiornato: legge t['nome_cucina']
lista_nomi_tip = [t['nome_cucina'] for t in tipologie]
tip_scelta_nome = st.segmented_control("📍 Ambiente di lavoro attivo:", lista_nomi_tip, default=lista_nomi_tip[0])
tip_id = next(t['id'] for t in tipologie if t['nome_cucina'] == tip_scelta_nome)

# =========================================================================
# 3. AREA DI COMPOSIZIONE: INSERIMENTO E COMPUTO BLOCCHI
# =========================================================================
catalogo_master = load_catalogo_modelli()
catalogo_master_df = pd.DataFrame(catalogo_master)

st.markdown("---")
st.subheader(f"🧱 Computo Moduli Elementari: {tip_scelta_nome}")

if catalogo_master_df.empty:
    st.warning("La libreria dei Modelli Master è vuota. Vai nella pagina di configurazione modelli per caricarli.")
else:
    # Form rapido inserimento blocco nel computo
    with st.expander("➕ Inserisci Modulo da Libreria Master", expanded=True):
        c_add1, c_add2, c_add3 = st.columns([2, 1, 1])
        modello_cod_scelto = c_add1.selectbox("Scegli Modulo Master", catalogo_master_df['codice'].tolist())
        row_master = catalogo_master_df[catalogo_master_df['codice'] == modello_cod_scelto].iloc[0]
        
        qta_add = c_add2.number_input("Quantità", min_value=1, value=1)
        note_add = c_add3.text_input("Note di produzione / Posizione")
        
        if st.button("📥 Aggiungi al Computo Metrico", type="primary"):
            # Inserisce l'istanza del blocco ereditando le misure standard
            res_ins_blocco = supabase.table("istanze_blocchi").insert({
                "tipologia_id": tip_id,
                "modello_id": row_master['id'],
                "larghezza": int(row_master['l_std']),
                "profondita": int(row_master['p_std']),
                "altezza": int(row_master['h_std']),
                "quantita": int(qta_add),
                "note": note_add
            }).execute()
            
            # Se il modello master ha accessori preimpostati, li agganciamo all'istanza
            if res_ins_blocco.data:
                inst_id = res_ins_blocco.data[0]['id']
                res_acc_def = supabase.table("modelli_accessori_default").select("*").eq("modello_id", row_master['id']).execute()
                if res_acc_def.data:
                    batch_acc_inst = [
                        {"istanza_blocco_id": inst_id, "accessorio_id": a['accessorio_id'], "quantita": a['quantita'] * int(qta_add)}
                        for a in res_acc_def.data
                    ]
                    supabase.table("istanze_blocchi_accessori").insert(batch_acc_inst).execute()
            st.rerun()

# 4. TABELLA DI MODIFICA DIMENSIONI IN REAL-TIME
istanze_caricate = load_istanze_blocchi(tip_id)

if istanze_caricate:
    # Costruiamo un dataframe per visualizzare e modificare le varianti dimensionali fuori standard
    righe_computo = []
    for inst in istanze_caricate:
        righe_computo.append({
            "ID Istanza": inst['id'],
            "Codice Modulo": inst['catalogo_modelli']['codice'],
            "Descrizione": inst['catalogo_modelli']['descrizione'], # 🔄 Nota: usa già 'descrizione' correttamente
            "Larghezza (L)": inst['larghezza'],
            "Profondità (P)": inst['profondita'],
            "Altezza (H)": inst['altezza'],
            "Q.tà": inst['quantita'],
            "Note/Posizione": inst.get('note', '')
        })
    df_computo = pd.DataFrame(righe_computo)
    
    st.markdown("#### 📏 Distinta Vetrinata ed Editor Fuori Misura")
    st.caption("Modifica le misure o le quantità direttamente nella tabella sotto per applicare variazioni sartoriali.")
    
    griglia_computo = st.data_editor(
        df_computo,
        column_config={
            "ID Istanza": st.column_config.TextColumn("ID", disabled=True, width="small"),
            "Codice Modulo": st.column_config.TextColumn("Codice", disabled=True),
            "Descrizione": st.column_config.TextColumn("Descrizione", disabled=True, width="large"),
            "Larghezza (L)": st.column_config.NumberColumn("L (mm)", min_value=50, step=1),
            "Profondità (P)": st.column_config.NumberColumn("P (mm)", min_value=50, step=1),
            "Altezza (H)": st.column_config.NumberColumn("H (mm)", min_value=50, step=1),
            "Q.tà": st.column_config.NumberColumn("Quantità", min_value=1, step=1),
            "Note/Posizione": st.column_config.TextColumn("Note Disegno")
        },
        hide_index=True,
        use_container_width=True,
        key="editor_computo_preventivatore"
    )
    
    # Pulsanti di salvataggio/rimozione elementi dal computo
    col_btn1, col_btn2 = st.columns([1, 4])
    if col_btn1.button("💾 Salva Variazioni Misure"):
        for _, r in griglia_computo.iterrows():
            supabase.table("istanze_blocchi").update({
                "larghezza": int(r["Larghezza (L)"]),
                "profondita": int(r["Profondità (P)"]),
                "altezza": int(r["Altezza (H)"]),
                "quantita": int(r["Q.tà"]),
                "note": r["Note/Posizione"]
            }).eq("id", r["ID Istanza"]).execute()
        st.success("Computo aggiornato!")
        st.rerun()
        
    # Rimozione di un modulo dal computo metrico
    id_da_eliminare = col_btn2.selectbox(
        "Rimuovi elemento dal computo:", 
        df_computo['ID Istanza'].tolist(), 
        format_func=lambda x: f"ID {x} - {df_computo[df_computo['ID Istanza']==x]['Codice Modulo'].values[0]}"
    )
    if st.button("❌ Elimina Modulo Selezionato"):
        supabase.table("istanze_blocchi").delete().eq("id", id_da_eliminare).execute()
        st.rerun()

    # =========================================================================
    # 5. PERSONALIZZAZIONE COMPONENTI INTERNI PER SINGOLO BLOCCO
    # =========================================================================
    st.markdown("---")
    st.subheader("🛠️ Dettaglio Ferramenta & Interni Blocco")
    
    blocco_target_id = st.selectbox(
        "Scegli un modulo dall'elenco sopra per ispezionare/modificare i suoi accessori interni:",
        df_computo['ID Istanza'].tolist(),
        format_func=lambda x: f"Modulo {df_computo[df_computo['ID Istanza']==x]['Codice Modulo'].values[0]} (Posizione: {df_computo[df_computo['ID Istanza']==x]['Note/Posizione'].values[0]})"
    )
    
    acc_caricati = load_accessori_istanza(blocco_target_id)
    cat_accessori = load_catalogo_accessori()
    cat_accessori_df = pd.DataFrame(cat_accessori)
    
    righe_acc = []
    for ac in acc_caricati:
        righe_acc.append({
            "ID Relazione": ac['id'],
            "Nome Componente": ac['catalogo_accessori']['nome'],
            "Quantità": ac['quantita'],
            "Prezzo Unitario (€)": ac['catalogo_accessori']['prezzo']
        })
    df_acc_istanza = pd.DataFrame(righe_acc) if righe_acc else pd.DataFrame(columns=["ID Relazione", "Nome Componente", "Quantità", "Prezzo Unitario (€)"])
    
    griglia_acc_istanza = st.data_editor(
        df_acc_istanza,
        column_config={
            "ID Relazione": st.column_config.TextColumn("ID", disabled=True),
            "Nome Componente": st.column_config.SelectboxColumn("Componente", options=cat_accessori_df['nome'].tolist() if not cat_accessori_df.empty else [], required=True, width="large"),
            "Quantità": st.column_config.NumberColumn("Q.tà Effettiva", min_value=0, step=1),
            "Prezzo Unitario (€)": st.column_config.NumberColumn("Cad. (€)", disabled=True)
        },
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        key=f"editor_acc_istanza_{blocco_target_id}"
    )
    
    if st.button("💾 Sincronizza Componenti Interni"):
        # 1. Pulisce la vecchia ferramenta di quella specifica istanza
        supabase.table("istanze_blocchi_accessori").delete().eq("istanza_blocco_id", blocco_target_id).execute()
        # 2. Reinserisce le righe valide configurate a schermo
        batch_new_acc = []
        for _, r in griglia_acc_istanza.iterrows():
            nome_c = r.get("Nome Componente")
            qta_c = r.get("Quantità")
            if nome_c and qta_c > 0:
                match_id = cat_accessori_df[cat_accessori_df['nome'] == nome_c].iloc[0]['id']
                batch_new_acc.append({
                    "istanza_blocco_id": blocco_target_id,
                    "accessorio_id": match_id,
                    "quantita": int(qta_c)
                })
        if batch_new_acc:
            supabase.table("istanze_blocchi_accessori").insert(batch_new_acc).execute()
        st.success("Ferramenta interna aggiornata con successo per questo modulo!")
        st.rerun()

else:
    st.info("Questo ambiente è attualmente vuoto. Util
