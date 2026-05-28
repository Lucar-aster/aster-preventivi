import streamlit as st
import pandas as pd

supabase = st.session_state["supabase"]

# =========================================================================
# FUNCTIONS: CARICAMENTO DATI DA DATABASE
# =========================================================================
def load_progetti():
    res = supabase.table("progetti").select("id, nome_progetto").order("creato_il", desc=True).execute()
    return res.data if res.data else []

def load_tipologie(progetto_id):
    res = supabase.table("tipologie_cucine").select("*").eq("progetto_id", progetto_id).order("nome_cucina").execute()
    return res.data if res.data else []

def load_catalogo_modelli():
    res = supabase.table("catalogo_modelli").select("*").order("codice").execute()
    return res.data if res.data else []

def load_catalogo_accessori():
    res = supabase.table("catalogo_accessori").select("id, nome, prezzo").order("nome").execute()
    return res.data if res.data else []

# 🎯 RISOLTO: Aggiunta la funzione mancante richiesta a riga 150
def load_finiture():
    """Recupera l'elenco unico e ordinato di tutte le finiture/materiali presenti a catalogo."""
    try:
        res = supabase.table("materiali").select("nome").order("nome").execute()
        if res.data:
            return sorted(list(set([item['nome'] for item in res.data if item.get('nome')])))
        return []
    except Exception:
        return []

def load_finiture_cassa():
    res = supabase.table("materiali").select("nome, sp, prezzo_mq").eq("categoria", "Cassa").order("nome").execute()
    return res.data if res.data else []

def load_finiture_anta():
    res = supabase.table("materiali").select("nome, sp, prezzo_mq").eq("categoria", "Anta").order("nome").execute()
    return res.data if res.data else []

def load_istanze_blocchi(tipologia_id):
    # 🎯 Aggiornato: seleziona 'tipo_schiena' al posto di 'escludi_schiena'
    res = (supabase.table("istanze_blocchi")
           .select("id, modello_id, l, p, h, quantita, finitura_cassa, finitura_anta, tipo_schiena, catalogo_modelli(*)")
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
# PANNELLO DI CONTROLLO LATERALE (SIDEBAR - CRUD STRUTTURA)
# =========================================================================
with st.sidebar:
    st.header("⚙️ Pannello Struttura")
    st.caption("Gestisci qui i dati anagrafici di commesse e stanze.")
    st.markdown("---")
    
    # GESTIONE PROGETTI (COMMESSE / CLIENTI)
    st.subheader("📁 1. Commesse & Clienti")
    progetti = load_progetti()
    
    if progetti:
        list_nomi_prog = [p['nome_progetto'] for p in progetti]
        proj_scelto_nome = st.selectbox("Seleziona Cliente Attivo", list_nomi_prog, key="sb_progetto_attivo")
        prog_id = next(p['id'] for p in progetti if p['nome_progetto'] == proj_scelto_nome)
        
        with st.expander("📝 Rinomina / ❌ Elimina Commessa"):
            nuovo_nome_prog = st.text_input("Nuovo nome commessa", value=proj_scelto_nome)
            if st.button("💾 Rinomina Commessa", use_container_width=True):
                if nuovo_nome_prog and nuovo_nome_prog != proj_scelto_nome:
                    supabase.table("progetti").update({"nome_progetto": nuovo_nome_prog}).eq("id", prog_id).execute()
                    st.success("Commessa rinominata!")
                    st.rerun()
            
            st.markdown("---")
            if st.button("🗑️ ELIMINA TUTTA LA COMMESSA", type="primary", use_container_width=True):
                supabase.table("progetti").delete().eq("id", prog_id).execute()
                st.warning("Commessa rimossa.")
                st.rerun()
    else:
        st.info("Nessuna commessa nel sistema.")
        prog_id = None

    with st.expander("➕ Nuova Commessa / Cliente", expanded=not progetti):
        nuovo_p_nome = st.text_input("Nome Nuovo Cliente / Commessa", key="new_proj_input")
        if st.button("➕ Crea Nuova Commessa", use_container_width=True):
            if nuovo_p_nome:
                supabase.table("progetti").insert({"nome_progetto": nuovo_p_nome}).execute()
                st.success("Nuova commessa creata!")
                st.rerun()

    st.markdown("---")
    
    # GESTIONE TIPOLOGIE (STANZE / AMBIENTI)
    st.subheader("🏢 2. Stanze & Tipologie")
    if prog_id:
        tipologie = load_tipologie(prog_id)
        
        if tipologie:
            lista_nomi_tip = [t['nome_cucina'] for t in tipologie]
            tip_scelta_nome = st.selectbox("Seleziona Stanza di Lavoro", lista_nomi_tip, key="sb_stanza_attiva")
            tip_id = next(t['id'] for t in tipologie if t['nome_cucina'] == tip_scelta_nome)
            
            with st.expander("📝 Rinomina / ❌ Elimina Stanza"):
                nuovo_nome_tip = st.text_input("Nuovo nome stanza", value=tip_scelta_nome)
                if st.button("💾 Rinomina Stanza", use_container_width=True):
                    if nuovo_nome_tip and nuovo_nome_tip != tip_scelta_nome:
                        supabase.table("tipologie_cucine").update({"nome_cucina": nuovo_nome_tip}).eq("id", tip_id).execute()
                        st.success("Stanza rinominata!")
                        st.rerun()
                
                st.markdown("---")
                if st.button("🗑️ ELIMINA QUESTA STANZA", type="primary", use_container_width=True):
                    supabase.table("tipologie_cucine").delete().eq("id", tip_id).execute()
                    st.warning("Stanza rimossa con successo.")
                    st.rerun()
        else:
            st.warning("Nessuna stanza creata per questa commessa.")
            tip_id = None
            tip_scelta_nome = None

        with st.expander("➕ Nuova Stanza / Ambiente", expanded=not tipologie):
            nome_nuova_tip = st.text_input("Nome Stanza (es. Cucina Principale)", key="new_tip_input")
            if st.button("➕ Aggiungi Stanza", use_container_width=True):
                if nome_nuova_tip:
                    supabase.table("tipologie_cucine").insert({"progetto_id": prog_id, "nome_cucina": nome_nuova_tip}).execute()
                    st.success("Stanza aggiunta!")
                    st.rerun()
    else:
        st.caption("Crea una commessa per abilitare la gestione delle stanze.")
        tip_id = None
        tip_scelta_nome = None

# =========================================================================
# AREA PRINCIPALE: CONFIGURAZIONE & MATRICI EDITABILI
# =========================================================================
if not prog_id or not tip_id:
    st.title("📊 Preventivatore a Matrice")
    st.info("👈 Utilizza il pannello laterale per selezionare o creare un Cliente ed una Stanza su cui lavorare.")
    st.stop()

st.title(f"📊 Preventivatore Matrice: {proj_scelto_nome}")
st.subheader(f"📍 Ambiente Attivo: {tip_scelta_nome}")

# ---------------------------------------------------------------------
# PANNELLO GESTIONE MATERIALI E FINITURE DI DEFAULT
# ---------------------------------------------------------------------
opzioni_finiture = load_finiture()

with st.expander("🎨 PANNELLO FINITURE E GESTIONALE MATERIALI DI DEFAULT", expanded=True):
    st.caption("Imposta i materiali, le finiture e gli spessori generali per questa stanza.")
    
    c_fin1, c_fin2, c_fin3 = st.columns(3)
    fin_cassa_def = c_fin1.selectbox("Materiale/Finitura Cassa", opzioni_finiture, key="df_fin_cassa")
    fin_anta_def = c_fin2.selectbox("Materiale/Finitura Anta", opzioni_finiture, key="df_fin_anta")
    fin_top_def = c_fin3.selectbox("Materiale Top / Piano di Lavoro", opzioni_finiture, key="df_fin_top")
    
    st.markdown("##### 📏 Spessori Materiale Configurazione")
    c_sp1, c_sp2 = st.columns(2)
    spessore_cassa = c_sp1.number_input("Spessore Materiale Cassa (mm)", min_value=1, value=18, step=1, key="df_sp_cassa")
    spessore_anta = c_sp2.number_input("Spessore Materiale Anta (mm)", min_value=1, value=22, step=1, key="df_sp_anta")
    
    # Memorizzazione nello stato di sessione
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

# Carica istanze attuali dal DB
istanze_caricate = load_istanze_blocchi(tip_id)
righe_moduli_esistenti = []
righe_lineari_esistenti = []

for inst in istanze_caricate:
    m = inst['catalogo_modelli']
    label = f"{m['codice']} | {m['descrizione'] if m['descrizione'] else ''}"
    
    fin_cassa_corr = inst.get('finitura_cassa') if inst.get('finitura_cassa') else st.session_state["default_finitura_cassa"]
    fin_anta_corr = inst.get('finitura_anta') if inst.get('finitura_anta') else st.session_state["default_finitura_anta"]
    
    # 🎯 Aggiornato: fallback sul valore predefinito 'Standard (8mm)'
    tipo_schiena_corr = inst.get('tipo_schiena') if inst.get('tipo_schiena') else "Standard (8mm)"
    
    riga = {
        "ID_DB": inst['id'],
        "Elemento": label,
        "L (mm)": inst['l'],
        "P / Spessore (mm)": inst['p'],  
        "H (mm)": inst['h'],
        "Finitura Cassa": fin_cassa_corr,
        "Finitura Anta": fin_anta_corr,
        "Config. Schiena": tipo_schiena_corr,  # 🎯 Sostituisce il vecchio Escludi Schiena booleano
        "Quantità": inst['quantita']
    }
    if any(k in label.lower() for k in keywords_lineari):
        righe_lineari_esistenti.append(riga)
    else:
        righe_moduli_esistenti.append(riga)

df_moduli_init = pd.DataFrame(righe_moduli_esistenti) if righe_moduli_esistenti else pd.DataFrame(columns=["ID_DB", "Elemento", "L (mm)", "P / Spessore (mm)", "H (mm)", "Finitura Cassa", "Finitura Anta", "Config. Schiena", "Quantità"])
df_lineari_init = pd.DataFrame(righe_lineari_esistenti) if righe_lineari_esistenti else pd.DataFrame(columns=["ID_DB", "Elemento", "L (mm)", "P / Spessore (mm)", "H (mm)", "Quantità"])

# =========================================================================
# RENDERING MATRICI EDITABILI IN TEMPO REALE
# =========================================================================
st.markdown("---")
st.caption("💡 Fai clic su **`+ Add row`** in fondo a ciascuna griglia per aggiungere elementi al preventivo.")

# --- TABELLA 1: MODULI ---
st.subheader("🧱 1. Matrice Computo Moduli / Scocche")
opzioni_schiena_lista = ["Standard (8mm)", "Economica (3mm)", "Nessuna"]

ed_moduli = st.data_editor(
    df_moduli_init,
    column_config={
        "ID_DB": st.column_config.TextColumn("ID", disabled=True, width="small"),
        "Elemento": st.column_config.SelectboxColumn("Seleziona Modello da Catalogo", options=opzioni_moduli, required=True, width="large"),
        "L (mm)": st.column_config.NumberColumn("L", min_value=0, format="%d"),
        "P / Spessore (mm)": st.column_config.NumberColumn("P (Profondità/Spessore Standard)", min_value=0, format="%d"), 
        "H (mm)": st.column_config.NumberColumn("H", min_value=0, format="%d"),
        "Finitura Cassa": st.column_config.SelectboxColumn("Finitura Cassa", options=opzioni_finiture, default=st.session_state["default_finitura_cassa"], width="medium"),
        "Finitura Anta": st.column_config.SelectboxColumn("Finitura Anta", options=opzioni_finiture, default=st.session_state["default_finitura_anta"], width="medium"),
        "Config. Schiena": st.column_config.SelectboxColumn("Config. Schiena", options=opzioni_schiena_lista, default="Standard (8mm)", width="medium"), # 🎯 Menu a tendina coerente
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
        "P (mm)": st.column_config.NumberColumn("P", min_value=0, format="%d"),
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
                
                fin_cassa = r.get("Finitura Cassa") if pd.notna(r.get("Finitura Cassa")) else st.session_state["default_finitura_cassa"]
                fin_anta = r.get("Finitura Anta") if pd.notna(r.get("Finitura Anta")) else st.session_state["default_finitura_anta"]
                
                # 🎯 Aggiornato: Salva la stringa di configurazione sul DB
                tipo_s = r.get("Config. Schiena") if pd.notna(r.get("Config. Schiena")) else "Standard (8mm)"
                
                res = supabase.table("istanze_blocchi").insert({
                    "tipologia_id": tip_id, 
                    "modello_id": master['id'], 
                    "l": l_val, 
                    "p": p_val, 
                    "h": h_val, 
                    "finitura_cassa": fin_cassa,
                    "finitura_anta": fin_anta,
                    "tipo_schiena": tipo_s,
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

            st.success("🎉 Configurazione e finiture salvate con successo!")
            st.rerun()
        except Exception as e:
            st.error(f"Errore durante il salvataggio: {str(e)}")

# =========================================================================
# 📊 ENGINE DI CALCOLO DINAMICO MQ SCHIENE
# =========================================================================
st.markdown("---")
st.subheader("📐 Calcolo Superfici e Sviluppo Schiene")

if "quota_heldom" not in st.session_state:
    st.session_state["quota_heldom"] = 60  

heldom = st.number_input("Quota Heldom da detrarre (mm):", min_value=0, value=st.session_state["quota_heldom"], step=1, key="sb_heldom")
st.session_state["quota_heldom"] = heldom

totale_mq_schiene = 0.0
righe_sviluppo_schiene = []

for idx, r in ed_moduli.iterrows():
    if pd.isna(r.get("Elemento")): 
        continue
    
    # 🎯 Aggiornato: Se l'utente ha impostato 'Nessuna', la schiena viene esclusa dal calcolo metrico
    if r.get("Config. Schiena") == "Nessuna":
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
        "Tipo Scelta": r.get("Config. Schiena"),
        "Q.tà": int(qta),
        "Superficie Totale (mq)": round(mq_totali_riga, 3)
    })

if righe_sviluppo_schiene:
    df_schiene_calc = pd.DataFrame(righe_sviluppo_schiene)
    st.dataframe(df_schiene_calc, use_container_width=True, hide_index=True)
    st.metric(label="📊 Superficie Totale Schiene Sviluppate", value=f"{totale_mq_schiene:.3f} mq")
else:
    st.info("Nessuna schiena inserita nel calcolo attuale (tutti gli elementi sono impostati su 'Nessuna' o la matrice è vuota).")
