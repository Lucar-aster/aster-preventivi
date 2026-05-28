import streamlit as st
import pandas as pd

supabase = st.session_state["supabase"]

# Helper per estrarre in modo sicuro il nome del cliente a seconda di come si chiama la colonna nel DB
def get_cliente_name(cliente_dict):
    if not cliente_dict:
        return "N/D"
    return cliente_dict.get("nome") or cliente_dict.get("ragione_sociale") or cliente_dict.get("denominazione") or str(list(cliente_dict.values())[0])

# =========================================================================
# FUNCTIONS: CARICAMENTO DATI DA DATABASE
# =========================================================================
def load_clienti():
    """Carica l'elenco completo dei clienti registrati"""
    try:
        res = supabase.table("clienti").select("*").execute()
        return res.data if res.data else []
    except Exception:
        return []

def load_progetti():
    """Esegue un JOIN relazionale implicito tirando dentro la tabella clienti collegata"""
    try:
        res = supabase.table("progetti").select("id, nome_progetto, cliente_id, clienti(*)").order("creato_il", desc=True).execute()
        return res.data if res.data else []
    except Exception:
        res = supabase.table("progetti").select("id, nome_progetto, cliente_id").order("creato_il", desc=True).execute()
        return res.data if res.data else []

def load_tipologie(progetto_id):
    res = supabase.table("tipologie_cucine").select("*").eq("progetto_id", proyecto_id).order("nome_cucina").execute()
    return res.data if res.data else []

def load_catalogo_modelli():
    res = supabase.table("catalogo_modelli").select("*").order("codice").execute()
    return res.data if res.data else []

def load_catalogo_accessori():
    res = supabase.table("catalogo_accessori").select("id, nome, prezzo").order("nome").execute()
    return res.data if res.data else []

def load_finiture():
    """Recupera l'elenco unico di tutte le finiture disponibili a catalogo"""
    try:
        res = supabase.table("materiali").select("nome").order("nome").execute()
        if res.data:
            return sorted(list(set([m['nome'] for m in res.data if m.get('nome')])))
        return []
    except Exception:
        return []

def load_istanze_blocchi(tipologia_id):
    res = (supabase.table("istanze_blocchi")
           .select("id, modello_id, l, p, h, quantita, finitura_cassa, finitura_anta, escludi_schiena, catalogo_modelli(*)")
           .eq("tipologia_id", tipologia_id)
           .execute())
    return res.data if res.data else []

def load_all_accessori_ambiente(tipologia_id):
    res_blocchi = supabase.table("istanze_blocchi").select("id").eq("tipologia_id", tipologia_id).execute()
    if not res_blocchi.data:
        return []
    ids_blocchi = [b['id'] for b in res_blocchi.data]
    
    res_acc = (supabase.table("istanze_blocchi_accessori")
               .select("id, istanza_blocco_id, accessorio_id, quantita, catalogo_accessori(nome, prezzo)")
               .in_("istanza_blocco_id", ids_blocchi)
               .execute())
    return res_acc.data if res_acc.data else []

# =========================================================================
# PANNELLO DI CONTROLLO LATERALE (SIDEBAR - SOLO ANAGRAFICA MACRO)
# =========================================================================
with st.sidebar:
    st.header("⚙️ Anagrafica Generale")
    st.caption("Seleziona o crea qui la pratica del cliente su cui vuoi lavorare.")
    st.markdown("---")
    
    st.subheader("📁 1. Clienti & Commesse")
    progetti = load_progetti()
    clienti = load_clienti()
    
    if progetti:
        list_labels_prog = []
        for p in progetti:
            c_data = p.get("clienti")
            c_name = get_cliente_name(c_data) if c_data else "Nessun Cliente"
            list_labels_prog.append(f"👤 {c_name} | 📁 {p['nome_progetto']}")
            
        proj_scelto_label = st.selectbox("Seleziona Pratica Attiva", list_labels_prog, key="sb_progetto_attivo")
        
        idx_selezionato = list_labels_prog.index(proj_scelto_label)
        prog_id = progetti[idx_selezionato]['id']
        proj_scelto_nome = progetti[idx_selezionato]['nome_progetto']
        cliente_dict = progetti[idx_selezionato].get("clienti")
        cliente_scelto_nome = get_cliente_name(cliente_dict) if cliente_dict else "Nessun Cliente"
        
        with st.expander("📝 Modifica / ❌ Elimina Commessa"):
            nuovo_nome_prog = st.text_input("Rinomina Commessa", value=proj_scelto_nome)
            
            if clienti:
                list_nomi_clienti = [get_cliente_name(c) for c in clienti]
                current_c_idx = 0
                if cliente_dict:
                    try:
                        current_c_idx = [c['id'] for c in clienti].index(cliente_dict['id'])
                    except ValueError:
                        current_c_idx = 0
                scelto_c_mod = st.selectbox("Sposta su Cliente", list_nomi_clienti, index=current_c_idx, key="mod_cambia_c")
                nuovo_cliente_id = clienti[list_nomi_clienti.index(scelto_c_mod)]['id']
            else:
                nuovo_cliente_id = progetti[idx_selezionato].get('cliente_id')

            if st.button("💾 Aggiorna Dati Commessa", use_container_width=True):
                if nuovo_nome_prog:
                    supabase.table("progetti").update({
                        "nome_progetto": nuovo_nome_prog,
                        "cliente_id": nuovo_cliente_id
                    }).eq("id", prog_id).execute()
                    st.success("Dati commessa salvati!")
                    st.rerun()
            
            st.markdown("---")
            if st.button("🗑️ ELIMINA QUESTA COMMESSA", type="primary", use_container_width=True):
                supabase.table("progetti").delete().eq("id", prog_id).execute()
                st.warning("Commessa rimossa.")
                st.rerun()
    else:
        st.info("Nessuna commessa attiva nel sistema.")
        prog_id = None
        cliente_scelto_nome = ""
        proj_scelto_nome = ""

    with st.expander("➕ Nuova Commessa (Progetto)"):
        if clienti:
            list_nomi_clienti_add = [get_cliente_name(c) for c in clienti]
            cliente_selezionato_add = st.selectbox("Seleziona Cliente per la Commessa", list_nomi_clienti_add, key="add_prog_c")
            c_id_add = clienti[list_nomi_clienti_add.index(cliente_selezionato_add)]['id']
            nuovo_p_nome_input = st.text_input("Nome Nuova Commessa", key="new_proj_input")
            
            if st.button("➕ Crea Nuova Commessa", use_container_width=True):
                if nuovo_p_nome_input:
                    supabase.table("progetti").insert({
                        "cliente_id": c_id_add,
                        "nome_progetto": nuovo_p_nome_input
                    }).execute()
                    st.success("Nuova commessa registrata!")
                    st.rerun()
        else:
            st.warning("⚠️ Non ci sono clienti in anagrafica. Creane uno qui sotto.")

    with st.expander("👤 ➕ Registra Nuovo Cliente"):
        nuovo_cliente_nome = st.text_input("Nome / Ragione Sociale Cliente", key="new_cliente_nome_input")
        if st.button("➕ Registra Cliente", use_container_width=True):
            if nuovo_cliente_nome:
                supabase.table("clienti").insert({"nome": nuovo_cliente_nome}).execute()
                st.success("Nuovo cliente aggiunto!")
                st.rerun()

# =========================================================================
# AREA PRINCIPALE: CONFIGURAZIONE & MATRICI EDITABILI
# =========================================================================
if not prog_id:
    st.title("📊 Preventivatore Computo Metrico")
    st.info("👈 Per iniziare, seleziona o crea un Cliente e una Commessa nel pannello laterale sinistro.")
    st.stop()

# Intestazione della pratica attiva
st.title("📊 Preventivatore Computo Metrico")
st.markdown(f"#### 👤 Cliente: `{cliente_scelto_nome}` | 📁 Commessa: `{proj_scelto_nome}`")

# ---------------------------------------------------------------------
# 🏢 SEZIONE REFACTORING: GESTIONE STANZE E TIPOLOGIE NELL'AREA PRINCIPALE
# ---------------------------------------------------------------------
st.markdown("---")
st.markdown("### 🏢 Gestione Stanze / Ambienti Relativi alla Commessa")

tipologie = load_tipologie(prog_id)

# Dividiamo lo schermo in due colonne: sinistra sceglie, destra fa manutenzione/aggiunge
col_select, col_actions = st.columns([2, 1])

with col_select:
    if tipologie:
        lista_nomi_tip = [t['nome_cucina'] for t in tipologie]
        tip_scelta_nome = st.selectbox("📍 Seleziona l'Ambiente di lavoro attivo:", lista_nomi_tip, key="main_stanza_attiva")
        tip_id = next(t['id'] for t in tipologie if t['nome_cucina'] == tip_scelta_nome)
    else:
        st.warning("⚠️ Nessun ambiente inserito per questa commessa. Utilizza il pannello a destra per crearne uno.")
        tip_id = None
        tip_scelta_nome = None

with col_actions:
    with st.expander("🛠️ Azioni Struttura Ambiente", expanded=not tipologie):
        # Se c'è una stanza attiva permettiamo modifica/eliminazione
        if tip_id:
            nuovo_nome_tip = st.text_input("Rinomina stanza selezionata", value=tip_scelta_nome)
            if st.button("💾 Applica Ridenominazione", use_container_width=True):
                if nuovo_nome_tip and nuovo_nome_tip != tip_scelta_nome:
                    supabase.table("tipologie_cucine").update({"nome_cucina": nuovo_nome_tip}).eq("id", tip_id).execute()
                    st.success("Stanza rinominata correttamente!")
                    st.rerun()
            
            if st.button("🗑️ RUMUOVI QUESTA STANZA", type="primary", use_container_width=True):
                supabase.table("tipologie_cucine").delete().eq("id", tip_id).execute()
                st.warning("Stanza eliminata definitivamente.")
                st.rerun()
            
            st.markdown("---")
        
        # Form di inserimento nuova stanza sempre accessibile
        nome_nuova_tip = st.text_input("➕ Aggiungi Nuova Stanza (es. Bagno, Cucina)", key="main_new_tip_input")
        if st.button("➕ Crea Ambiente", use_container_width=True):
            if nome_nuova_tip:
                supabase.table("tipologie_cucine").insert({"progetto_id": prog_id, "nome_cucina": nome_nuova_tip}).execute()
                st.success("Nuovo ambiente registrato!")
                st.rerun()

# Se l'utente non ha ancora creato alcuna stanza o non ne ha selezionata una, fermiamo l'applicazione qui
if not tip_id:
    st.info("💡 Crea una nuova stanza nel box sopra per sbloccare la griglia del computo metrico e dei materiali.")
    st.stop()

st.markdown(f"### 🛠️ Area di Lavoro: `{tip_scelta_nome}`")

# ---------------------------------------------------------------------
# PANNELLO GESTIONE MATERIALI E FINITURE DI DEFAULT
# ---------------------------------------------------------------------
opzioni_finiture = load_finiture()

with st.expander("🎨 PANNELLO FINITURE E GESTIONALE MATERIALI DI DEFAULT", expanded=False):
    st.caption("Imposta i materiali, le finiture e gli spessori generali per questa stanza.")
    
    c_fin1, c_fin2, c_fin3 = st.columns(3)
    fin_cassa_def = c_fin1.selectbox("Materiale/Finitura Cassa", opzioni_finiture, key="df_fin_cassa")
    fin_anta_def = c_fin2.selectbox("Materiale/Finitura Anta", opzioni_finiture, key="df_fin_anta")
    fin_top_def = c_fin3.selectbox("Materiale Top / Piano di Lavoro", opzioni_finiture, key="df_fin_top")
    
    st.markdown("##### 📏 Spessori Materiale Configurazione")
    c_sp1, c_sp2 = st.columns(2)
    spessore_cassa = c_sp1.number_input("Spessore Materiale Cassa (mm)", min_value=1, value=18, step=1, key="df_sp_cassa")
    spessore_anta = c_sp2.number_input("Spessore Materiale Anta (mm)", min_value=1, value=22, step=1, key="df_sp_anta")
    
    st.session_state["default_finitura_cassa"] = fin_cassa_def
    st.session_state["default_finitura_anta"] = fin_anta_def
    st.session_state["default_finitura_top"] = fin_top_def
    st.session_state["default_spessore_cassa"] = spessore_cassa
    st.session_state["default_spessore_anta"] = spessore_anta

# =========================================================================
# SMISTAMENTO CATALOGO MASTER ED ELEMENTI ESISTENTI
# =========================================================================
keywords_lineari = ['gola', 'zoccolo', 'lineare', 'profilo', 'alzatina', 'battiscopa', 'maggiorazione']

modelli_master = load_catalogo_modelli()
opzioni_moduli = []
opzioni_lineari = []
mappa_modelli = {}

for m in modelli_master:
    label = f"{m['codice']} | {m['descrizione'] if m['descrizione'] else ''}"
    mappa_modelli[label] = m
    if any(k in label.lower() for k in keywords_lineari):
        opzioni_lineari.append(label)
    else:
        opzioni_moduli.append(label)

catalogo_acc = load_catalogo_accessori()
opzioni_acc = [f"{a['nome']} | €{a['prezzo']}" for a in catalogo_acc]
mappa_accessori = {f"{a['nome']} | €{a['prezzo']}": a for a in catalogo_acc}

# Carica istanze attuelles dal DB
istanze_caricate = load_istanze_blocchi(tip_id)
righe_moduli_esistenti = []
righe_lineari_esistenti = []

for inst in istanze_caricate:
    m = inst['catalogo_modelli']
    label = f"{m['codice']} | {m['descrizione'] if m['descrizione'] else ''}"
    
    fin_cassa_corr = inst.get('finitura_cassa') if inst.get('finitura_cassa') else st.session_state.get("default_finitura_cassa")
    fin_anta_corr = inst.get('finitura_anta') if inst.get('finitura_anta') else st.session_state.get("default_finitura_anta")
    escludi_schiena_corr = inst.get('escludi_schiena') if inst.get('escludi_schiena') is not None else False
    
    riga = {
        "ID_DB": inst['id'],
        "Elemento": label,
        "L (mm)": inst['l'],
        "P / Spessore (mm)": inst['p'],  
        "H (mm)": inst['h'],
        "Finitura Cassa": fin_cassa_corr,
        "Finitura Anta": fin_anta_corr,
        "Escludi Schiena": escludi_schiena_corr,  
        "Quantità": inst['quantita']
    }
    if any(k in label.lower() for k in keywords_lineari):
        righe_lineari_esistenti.append(riga)
    else:
        righe_moduli_esistenti.append(riga)

df_moduli_init = pd.DataFrame(righe_moduli_esistenti) if righe_moduli_esistenti else pd.DataFrame(columns=["ID_DB", "Elemento", "L (mm)", "P / Spessore (mm)", "H (mm)", "Finitura Cassa", "Finitura Anta", "Escludi Schiena", "Quantità"])
df_lineari_init = pd.DataFrame(righe_lineari_esistenti) if righe_lineari_esistenti else pd.DataFrame(columns=["ID_DB", "Elemento", "L (mm)", "P / Spessore (mm)", "H (mm)", "Quantità"])

# =========================================================================
# RENDERING MATRICI EDITABILI IN TEMPO REALE
# =========================================================================
st.markdown("---")
st.caption("💡 Fai clic su **`+ Add row`** in fondo a ciascuna griglia per aggiungere elementi al preventivo.")

# --- TABELLA 1: MODULI ---
st.subheader("🧱 1. Matrice Computo Moduli / Scocche")
ed_moduli = st.data_editor(
    df_moduli_init,
    column_config={
        "ID_DB": st.column_config.TextColumn("ID", disabled=True, width="small"),
        "Elemento": st.column_config.SelectboxColumn("Seleziona Modello da Catalogo", options=opzioni_moduli, required=True, width="large"),
        "L (mm)": st.column_config.NumberColumn("L", min_value=0, format="%d"),
        "P / Spessore (mm)": st.column_config.NumberColumn("P (Profondità/Spessore Standard)", min_value=0, format="%d"), 
        "H (mm)": st.column_config.NumberColumn("H", min_value=0, format="%d"),
        "Finitura Cassa": st.column_config.SelectboxColumn("Finitura Cassa", options=opzioni_finiture, default=st.session_state.get("default_finitura_cassa"), width="medium"),
        "Finitura Anta": st.column_config.SelectboxColumn("Finitura Anta", options=opzioni_finiture, default=st.session_state.get("default_finitura_anta"), width="medium"),
        "Escludi Schiena": st.column_config.CheckboxColumn("Escludi Schiena", default=False), 
        "Quantità": st.column_config.NumberColumn("Q.tà", min_value=1, default=1, format="%d")
    },
    num_rows="dynamic",
    hide_index=True,
    use_container_width=True,
    key=f"matrice_moduli_{tip_id}"
)

# Generazione riferimenti dinamici per associare gli accessori
opzioni_destinazione_accessori = []
for idx, row in ed_moduli.iterrows():
    if pd.notna(row.get("Elemento")):
        opzioni_destinazione_accessori.append(f"Tab 1 - Riga {idx+1} ({str(row['Elemento']).split('|')[0].strip()})")

# --- TABELLA 2: GOLE / ZOCCOLI / LINEARI ---
st.subheader("📏 2. Matrice Gole, Zoccoli ed Elementi Lineari")
ed_lineari = st.data_editor(
    df_lineari_init,
    column_config={
        "ID_DB": st.column_config.TextColumn("ID", disabled=True, width="small"),
        "Elemento": st.column_config.SelectboxColumn("Seleziona Profilo / Lineare", options=opzioni_lineari, required=True, width="large"),
        "L (mm)": st.column_config.NumberColumn("Lunghezza / Taglio", min_value=0, format="%d"),
        "P / Spessore (mm)": st.column_config.NumberColumn("P (Profondità/Spessore Standard)", min_value=0, format="%d"), 
        "H (mm)": st.column_config.NumberColumn("H", min_value=0, format="%d"),
        "Quantità": st.column_config.NumberColumn("Q.tà", min_value=1, default=1, format="%d")
    },
    num_rows="dynamic",
    hide_index=True,
    use_container_width=True,
    key=f"matrice_lineari_{tip_id}"
)

for idx, row in ed_lineari.iterrows():
    if pd.notna(row.get("Elemento")):
        opzioni_destinazione_accessori.append(f"Tab 2 - Riga {idx+1} ({str(row['Elemento']).split('|')[0].strip()})")

# --- TABELLA 3: ACCESSORI ---
accessori_esistenti = load_all_accessori_ambiente(tip_id)
righe_accessori_init = []

for ae in accessori_esistenti:
    label_acc = f"{ae['catalogo_accessori']['nome']} | €{ae['catalogo_accessori']['prezzo']}"
    label_destinazione = ""
    
    if not df_moduli_init.empty and ae['istanza_blocco_id'] in df_moduli_init['ID_DB'].values:
        idx = df_moduli_init[df_moduli_init['ID_DB'] == ae['istanza_blocco_id']].index[0]
        if idx < len(ed_moduli):
            label_destinazione = f"Tab 1 - Riga {idx+1} ({str(df_moduli_init.loc[idx, 'Elemento']).split('|')[0].strip()})"
            
    elif not df_lineari_init.empty and ae['istanza_blocco_id'] in df_lineari_init['ID_DB'].values:
        idx = df_lineari_init[df_lineari_init['ID_DB'] == ae['istanza_blocco_id']].index[0]
        if idx < len(ed_lineari):
            label_destinazione = f"Tab 2 - Riga {idx+1} ({str(df_lineari_init.loc[idx, 'Elemento']).split('|')[0].strip()})"

    if label_destinazione:
        righe_accessori_init.append({
            "Accessorio": label_acc,
            "Quantità": ae['quantita'],
            "Destinato a Modulo": label_destinazione
        })

df_accessori_init = pd.DataFrame(righe_accessori_init) if righe_accessori_init else pd.DataFrame(columns=["Accessorio", "Quantità", "Destinato a Modulo"])

st.subheader("🛠️ 3. Matrice Ferramenta, Accessori e Componenti Interni")
if not opzioni_destinazione_accessori:
    st.info("Aggiungi almeno un modulo o elemento lineare sopra per poter associare gli accessori.")
else:
    ed_accessori = st.data_editor(
        df_accessori_init,
        column_config={
            "Accessorio": st.column_config.SelectboxColumn("Seleziona Ferramenta / Interno", options=opzioni_acc, required=True, width="large"),
            "Quantità": st.column_config.NumberColumn("Q.tà Effettiva", min_value=1, default=1, format="%d"),
            "Destinato a Modulo": st.column_config.SelectboxColumn("Associa al Modulo Posizionato", options=opzioni_destinazione_accessori, required=True, width="medium")
        },
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        key=f"matrice_accessori_{tip_id}"
    )

# =========================================================================
# CENTRALE DI SALVATAGGIO & SINCRONIZZAZIONE DB COERENTE
# =========================================================================
st.markdown("---")
if st.button("💾 SALVA CONFIGURAZIONE E CALCOLA PREVENTIVO", type="primary", use_container_width=True):
    with st.spinner("Sincronizzazione matrici nel database in corso..."):
        try:
            if righe_moduli_esistenti or righe_lineari_esistenti:
                vecchi_ids = [b['ID_DB'] for b in righe_moduli_esistenti] + [l['ID_DB'] for l in righe_lineari_esistenti]
                supabase.table("istanze_blocchi_accessori").delete().in_("istanza_blocco_id", vecchi_ids).execute()
                supabase.table("istanze_blocchi").delete().eq("tipologia_id", tip_id).execute()

            mappa_indici_nuovi_ids = {}

            # Registrazione Moduli
            for idx, r in ed_moduli.iterrows():
                if pd.isna(r.get("Elemento")): continue
                master = mappa_modelli[r["Elemento"]]
                l_val = int(r["L (mm)"]) if pd.notna(r["L (mm)"]) and r["L (mm)"] > 0 else int(master['l_std'])
                p_val = int(r["P / Spessore (mm)"]) if pd.notna(r["P / Spessore (mm)"]) and r["P / Spessore (mm)"] > 0 else int(master['p_std'])
                h_val = int(r["H (mm)"]) if pd.notna(r["H (mm)"]) and r["H (mm)"] > 0 else int(master['h_std'])
                qta = int(r["Quantità"]) if pd.notna(r["Quantità"]) else 1
                
                fin_cassa = r.get("Finitura Cassa") if pd.notna(r.get("Finitura Cassa")) else st.session_state.get("default_finitura_cassa")
                fin_anta = r.get("Finitura Anta") if pd.notna(r.get("Finitura Anta")) else st.session_state.get("default_finitura_anta")
                escludi_s = bool(r.get("Escludi Schiena")) if pd.notna(r.get("Escludi Schiena")) else False
                
                res = supabase.table("istanze_blocchi").insert({
                    "tipologia_id": tip_id, 
                    "modello_id": master['id'], 
                    "l": l_val, 
                    "p": p_val, 
                    "h": h_val, 
                    "finitura_cassa": fin_cassa,
                    "finitura_anta": fin_anta,
                    "escludi_schiena": escludi_s,
                    "quantita": qta
                }).execute()
                if res.data:
                    mappa_indici_nuovi_ids[f"Tab 1 - Riga {idx+1}"] = res.data[0]['id']

            # Registrazione Lineari
            for idx, r in ed_lineari.iterrows():
                if pd.isna(r.get("Elemento")): continue
                master = mappa_modelli[r["Elemento"]]
                l_val = int(r["L (mm)"]) if pd.notna(r["L (mm)"]) and r["L (mm)"] > 0 else int(master['l_std'])
                p_val = int(r["P / Spessore (mm)"]) if pd.notna(r["P / Spessore (mm)"]) and r["P / Spessore (mm)"] > 0 else int(master['p_std'])
                h_val = int(r["H (mm)"]) if pd.notna(r["H (mm)"]) and r["H (mm)"] > 0 else int(master['h_std'])
                qta = int(r["Quantità"]) if pd.notna(r["Quantità"]) else 1
                
                res = supabase.table("istanze_blocchi").insert({
                    "tipologia_id": tip_id, "modello_id": master['id'], "l": l_val, "p": p_val, "h": h_val, "quantita": qta
                }).execute()
                if res.data:
                    mappa_indici_nuovi_ids[f"Tab 2 - Riga {idx+1}"] = res.data[0]['id']

            # Registrazione Accessori
            if 'ed_accessori' in locals() and not ed_accessori.empty:
                batch_accessori = []
                for _, r in ed_accessori.iterrows():
                    if pd.isna(r.get("Accessorio")) or pd.isna(r.get("Destinato a Modulo")): continue
                    master_acc = mappa_accessori[r["Accessorio"]]
                    stringa_dest = r["Destinato a Modulo"]
                    chiave_riga = " - ".join(stringa_dest.split(" - ")[:2])
                    
                    blocco_id_collegato = mappa_indici_nuovi_ids.get(chiave_riga)
                    if blocco_id_collegato:
                        batch_accessori.append({
                            "istanza_blocco_id": blocco_id_collegato,
                            "accessorio_id": master_acc['id'],
                            "quantita": int(r["Quantità"]) if pd.notna(r["Quantità"]) else 1
                        })
                if batch_accessori:
                    supabase.table("istanze_blocchi_accessori").insert(batch_accessori).execute()

            st.success("🎉 Configurazione salvata con successo!")
            st.rerun()
        except Exception as e:
            st.error(f"Errore durante il salvataggio: {str(e)}")

# =========================================================================
# 📊 ENGINE DI CALCOLO DINAMICO MQ SCHIENE (SP. 8MM)
# =========================================================================
st.markdown("---")
st.subheader("📐 Calcolo Superfici e Sviluppo Schiene (8mm)")

if "quota_heldom" not in st.session_state:
    st.session_state["quota_heldom"] = 60  

heldom = st.number_input("Quota Heldom da detrarre (mm):", min_value=0, value=st.session_state["quota_heldom"], step=1, key="sb_heldom")
st.session_state["quota_heldom"] = heldom

totale_mq_schiene = 0.0
righe_sviluppo_schiene = []

for idx, r in ed_moduli.iterrows():
    if pd.isna(r.get("Elemento")): 
        continue
    
    if r.get("Escludi Schiena") == True:
        continue
        
    l_val = float(r["L (mm)"]) if pd.notna(r["L (mm)"]) else 0.0
    h_val = float(r["H (mm)"]) if pd.notna(r["H (mm)"]) else 0.0
    qta = float(r["Quantità"]) if pd.notna(r["Quantità"]) else 1.0
    
    altezza_utile_schiena = h_val - heldom
    if altezza_utile_schiena < 0:
        altezza_utile_schiena = 0.0
        
    mq_singolo = (l_val * altezza_utile_schiena) / 1_000_000.0
    mq_totali_riga = mq_singolo * qta
    totale_mq_schiene += mq_totali_riga
    
    codice_mod = str(r["Elemento"]).split('|')[0].strip()
    righe_sviluppo_schiene.append({
        "Modulo Origine": f"Tab 1 - Riga {idx+1} ({codice_mod})",
        "Larghezza L (mm)": int(l_val),
        "H Utile (H - Heldom) (mm)": int(altezza_utile_schiena),
        "Q.tà": int(qta),
        "Superficie Totale (mq)": round(mq_totali_riga, 3)
    })

if righe_sviluppo_schiene:
    df_schiene_calc = pd.DataFrame(righe_sviluppo_schiene)
    st.dataframe(df_schiene_calc, use_container_width=True, hide_index=True)
    st.metric(label="📊 Superficie Totale Schiene Sviluppate (Sp. 8mm)", value=f"{totale_mq_schiene:.3f} mq")
else:
    st.info("Nessuna schiena inserita nel calcolo attuale (tutti gli elementi sono stati esclusi o la matrice è vuota).")
