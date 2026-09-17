import pandas as pd
from supabase import create_client
import streamlit as st
from amministrazione import render_amministrazione
from engine import calcola_modulo_parametrico
from exports import genera_excel_preventivo, genera_pdf_preventivo

st.set_page_config(page_title="Preventivatore Arredi Modulari", layout="wide")

# Connessione Supabase
URL = st.secrets.get("SUPABASE_URL", "https://tuo-id.supabase.co")
KEY = st.secrets.get("SUPABASE_KEY", "tua-chiave")
supabase = create_client(URL, KEY)

# Navigazione Sezioni
st.sidebar.title("📍 Navigazione")
modalita = st.sidebar.radio("Sezione:", ["Preventivatore", "Amministrazione"])

if modalita == "Amministrazione":
    render_amministrazione(supabase)
else:
    # ==========================================
    # 1. GESTIONE CLIENTI & PROGETTI IN SIDEBAR
    # ==========================================
    st.sidebar.divider()
    st.sidebar.header("📁 Clienti & Progetti")
    
    lista_clienti = supabase.table("clienti").select("*").order("ragione_sociale").execute().data
    
    # --- FORM CREAZIONE NUOVO CLIENTE ---
    with st.sidebar.expander("👤 Nuovo Cliente"):
        nuovo_cliente_nome = st.text_input("Nome / Ragione Sociale")
        nuovo_cliente_ind = st.text_input("Indirizzo / Cantiere")
        if st.button("Crea Cliente"):
            if nuovo_cliente_nome:
                supabase.table("clienti").insert({
                    "ragione_sociale": nuovo_cliente_nome,
                    "indirizzo": nuovo_cliente_ind
                }).execute()
                st.success("Cliente creato!")
                st.rerun()

    # --- FORM CREAZIONE NUOVO PROGETTO ---
    with st.sidebar.expander("📂 Nuovo Progetto"):
        if lista_clienti:
            opzioni_cli_create = {c['ragione_sociale']: c['id'] for c in lista_clienti}
            cli_selected_for_proj = st.selectbox("Seleziona Cliente per Progetto:", list(opzioni_cli_create.keys()))
            nome_nuovo_progetto = st.text_input("Nome Progetto / Riferimento", "Ristrutturazione 2026")
            
            if st.button("Crea Progetto"):
                if nome_nuovo_progetto:
                    p_created = supabase.table("progetti").insert({
                        "cliente_id": opzioni_cli_create[cli_selected_for_proj],
                        "nome_cliente": cli_selected_for_proj,
                        "nome_progetto": nome_nuovo_progetto
                    }).execute().data[0]
                    
                    supabase.table("varianti_progetto").insert({
                        "progetto_id": p_created["id"],
                        "nome_variante": "Variante Base",
                        "ricarico_progetto_perc": 120.0,
                        "sconto_finale_perc": 0.0,
                        "ricarico_montaggio_perc": 10.0,
                        "is_principale": True
                    }).execute()
                    
                    st.success("Progetto creato!")
                    st.rerun()
        else:
            st.info("Crea prima un cliente per poter aggiungere un progetto.")

    if not lista_clienti:
        st.warning("Nessun cliente presente. Crea il primo cliente dalla sidebar.")
        st.stop()

    # --- SELEZIONE CLIENTE E PROGETTO SEPARATE ---
    st.sidebar.divider()
    
    opzioni_clienti_map = {c['ragione_sociale']: c for c in lista_clienti}
    cliente_selezionato_nome = st.sidebar.selectbox("👤 Seleziona Cliente:", list(opzioni_clienti_map.keys()))
    cliente_attuale = opzioni_clienti_map[cliente_selezionato_nome]
    cliente_id = cliente_attuale["id"]

    progetti_cliente = supabase.table("progetti").select("*").eq("cliente_id", cliente_id).order("created_at", desc=True).execute().data
    
    if not progetti_cliente:
        st.warning(f"Nessun progetto associato a '{cliente_attuale['ragione_sociale']}'. Creane uno dalla sidebar.")
        st.stop()
        
    opzioni_progetti_map = {p['nome_progetto']: p for p in progetti_cliente}
    progetto_selezionato_nome = st.sidebar.selectbox("📂 Seleziona Progetto:", list(opzioni_progetti_map.keys()))
    progetto_attuale = opzioni_progetti_map[progetto_selezionato_nome]
    progetto_id = progetto_attuale["id"]

    mat_db = supabase.table("finiture_materiali").select("*").execute().data
    finiture_lista = sorted(list(set([m["nome_finitura"] for m in mat_db]))) if mat_db else ["Laminato Standard"]

    st.title(f"📐 Preventivo: {cliente_attuale['ragione_sociale']} — {progetto_attuale['nome_progetto']}")

    # ==========================================
    # SCHEDA 1: SCHEDA CLIENTE
    # ==========================================
    with st.expander("👤 Scheda Cliente", expanded=False):
        col_cli1, col_cli2 = st.columns(2)
        cliente_nome_mod = col_cli1.text_input("Nome / Ragione Sociale Cliente", value=cliente_attuale["ragione_sociale"])
        cliente_ind_mod = col_cli2.text_input("Indirizzo Sede / Fatturazione", value=cliente_attuale.get("indirizzo") or "")

        if st.button("💾 Salva Dati Cliente"):
            supabase.table("clienti").update({
                "ragione_sociale": cliente_nome_mod,
                "indirizzo": cliente_ind_mod
            }).eq("id", cliente_id).execute()
            
            supabase.table("progetti").update({
                "nome_cliente": cliente_nome_mod
            }).eq("cliente_id", cliente_id).execute()
            
            st.success("Dati cliente aggiornati!")
            st.rerun()

    # ==========================================
    # SCHEDA 2: GESTIONE PROGETTO
    # ==========================================
    with st.expander("📁 Gestione Progetto", expanded=False):
        col_p1, col_p2 = st.columns(2)
        proj_nome_mod = col_p1.text_input("Nome Progetto / Riferimento", value=progetto_attuale["nome_progetto"])
        proj_ind_mod = col_p2.text_input("Indirizzo Cantiere / Consegna", value=progetto_attuale.get("indirizzo") or cliente_attuale.get("indirizzo") or "")

        if st.button("💾 Salva Dati Progetto"):
            supabase.table("progetti").update({
                "nome_progetto": proj_nome_mod,
                "indirizzo": proj_ind_mod
            }).eq("id", progetto_id).execute()
            
            st.success("Dati progetto aggiornati!")
            st.rerun()

    # ==========================================
    # SELEZIONE E GESTIONE VARIANTI FINITURA
    # ==========================================
    st.subheader("🔀 Gestione Variante Finitura")
    
    varianti = supabase.table("varianti_progetto").select("*").eq("progetto_id", progetto_id).execute().data
    opzioni_v = {v["nome_variante"]: v for v in varianti}
    
    col_v1, col_v2 = st.columns([2, 1])
    
    with col_v1:
        variante_attuale_nome = st.selectbox("Seleziona Variante Attiva su cui lavorare:", list(opzioni_v.keys()))
        variante_attuale = opzioni_v[variante_attuale_nome]
        variante_id = variante_attuale["id"]
        
    with col_v2:
        with st.popover("➕ Nuova Variante Finiture"):
            nome_nuova_var = st.text_input("Nome Variante (es. Laccato Premium)")
            if st.button("Salva Nuova Variante"):
                if nome_nuova_var:
                    supabase.table("varianti_progetto").insert({
                        "progetto_id": progetto_id,
                        "nome_variante": nome_nuova_var,
                        "ricarico_progetto_perc": variante_attuale.get("ricarico_progetto_perc", 120.0),
                        "sconto_finale_perc": variante_attuale.get("sconto_finale_perc", 0.0),
                        "ricarico_montaggio_perc": variante_attuale.get("ricarico_montaggio_perc", 10.0)
                    }).execute()
                    st.success("Variante aggiunta!")
                    st.rerun()

    # ==========================================
    # SCHEDA 3: FINITURE PREDEFINITE VARIANTE
    # ==========================================
    with st.expander(f"🎨 Finiture Predefinite Variante ({variante_attuale['nome_variante']})", expanded=False):
        st.write("**Parametri Economici della Variante:**")
        col_par1, col_par2, col_par3 = st.columns(3)
        ricarico_p = col_par1.number_input("Ricarico Progetto (%)", value=float(variante_attuale.get("ricarico_progetto_perc", 120.0)), step=1.0, format="%.2f")
        sconto_f = col_par2.number_input("Sconto Finale (%)", value=float(variante_attuale.get("sconto_finale_perc", 0.0)), step=1.0, format="%.2f")
        mont_p = col_par3.number_input("Montaggio & Trasporto (%)", value=float(variante_attuale.get("ricarico_montaggio_perc", 10.0)), step=1.0, format="%.2f")

        st.markdown("---")
        st.write("Seleziona le finiture di default applicate ai nuovi moduli inseriti in questa variante.")
        col_fin1, col_fin2 = st.columns(2)
        
        def_cassa_val = variante_attuale.get("default_finitura_cassa")
        def_anta_val = variante_attuale.get("default_finitura_anta")
        
        def_cassa_idx = finiture_lista.index(def_cassa_val) if def_cassa_val in finiture_lista else 0
        def_anta_idx = finiture_lista.index(def_anta_val) if def_anta_val in finiture_lista else 0

        default_cassa = col_fin1.selectbox("Finitura CASSA (Default)", finiture_lista, index=def_cassa_idx)
        default_anta = col_fin2.selectbox("Finitura ANTA / FRONTALE (Default)", finiture_lista, index=def_anta_idx)
        
        if st.button("💾 Salva Impostazioni e Finiture Variante"):
            supabase.table("varianti_progetto").update({
                "ricarico_progetto_perc": ricarico_p,
                "sconto_finale_perc": sconto_f,
                "ricarico_montaggio_perc": mont_p,
                "default_finitura_cassa": default_cassa,
                "default_finitura_anta": default_anta
            }).eq("id", variante_id).execute()
            
            st.success("Parametri e finiture predefinite salvati!")
            st.rerun()

    st.divider()

    # ==========================================
    # 3. GESTIONE AMBIENTI DEL PROGETTO
    # ==========================================
    ambienti = supabase.table("ambienti").select("*").eq("progetto_id", progetto_id).execute().data

    col_a1, col_a2 = st.columns([3, 1])
    with col_a1:
        st.subheader(f"🏠 Ambienti del Progetto ({len(ambienti)})")
    with col_a2:
        with st.popover("➕ Crea Nuovo Ambiente"):
            nuovo_amb_nome = st.text_input("Nome Ambiente (es. Cucina)")
            if st.button("Salva Ambiente") and nuovo_amb_nome:
                supabase.table("ambienti").insert({
                    "progetto_id": progetto_id,
                    "nome_ambiente": nuovo_amb_nome
                }).execute()
                st.rerun()

    if not ambienti:
        st.info("Nessun ambiente inserito. Crea il primo ambiente per iniziare ad inserire i moduli.")
        st.stop()

    # ==========================================
    # 4. INSERIMENTO ELEMENTI NELL'AMBIENTE (4 TAB)
    # ==========================================
    st.subheader("➕ Inserisci Elementi nell'Ambiente")
    tab_m1, tab_m2, tab_m3, tab_m4 = st.tabs([
        "📦 Moduli (Standard / Custom)", 
        "📐 Gole & Zoccoli", 
        "💡 Illuminazione", 
        "🔩 Accessori & Ferramenta"
    ])

    # --- TAB 1: MODULI STANDARD O CUSTOM ---
    with tab_m1:
        sub_tab_std, sub_tab_cust = st.tabs(["⚡ Modulo Standard", "✏️ Modulo Custom"])
        
        with sub_tab_std:
            moduli_std_db = supabase.table("moduli_standard").select("*").execute().data
            if moduli_std_db:
                col_s1, col_s2 = st.columns(2)
                amb_std_dest = col_s1.selectbox("Ambiente Destinazione", options=[a['id'] for a in ambienti], format_func=lambda x: [a['nome_ambiente'] for a in ambienti if a['id']==x][0], key="amb_std_mod")
                mod_std_sel_id = col_s2.selectbox("Modulo Standard", options=[m['id'] for m in moduli_std_db], format_func=lambda x: [m['nome_modulo'] for m in moduli_std_db if m['id']==x][0])
                
                m_std_obj = next(m for m in moduli_std_db if m['id'] == mod_std_sel_id)
                st.info(f"**Dettagli Modulo:** `{m_std_obj['categoria']}` | `{m_std_obj['larghezza_mm']}x{m_std_obj['altezza_mm']}x{m_std_obj['profondita_mm']} mm`")
                
                if st.button("🚀 Inserisci Modulo Standard"):
                    mod_base = supabase.table("moduli_base").insert({
                        "ambiente_id": amb_std_dest,
                        "categoria": m_std_obj["categoria"],
                        "nome_modulo": m_std_obj["nome_modulo"],
                        "larghezza_mm": m_std_obj["larghezza_mm"],
                        "altezza_mm": m_std_obj["altezza_mm"],
                        "profondita_mm": m_std_obj["profondita_mm"],
                        "tipo_apertura": m_std_obj["tipo_apertura"],
                        "num_ante": m_std_obj.get("num_ante", 1),
                        "num_cassetti": m_std_obj.get("num_cassetti", 0)
                    }).execute().data[0]
                    
                    fin_anta_id = next((m["id"] for m in mat_db if m["nome_finitura"] == default_anta), mat_db[0]["id"] if mat_db else None)
                    if fin_anta_id:
                        supabase.table("configurazione_modulo_variante").insert({
                            "variante_id": variante_id,
                            "modulo_base_id": mod_base["id"],
                            "finitura_id": fin_anta_id
                        }).execute()
                    st.success("Modulo Standard inserito!")
                    st.rerun()

        with sub_tab_cust:
            amb_m = st.selectbox("Ambiente Destinazione", options=[a['id'] for a in ambienti], format_func=lambda x: [a['nome_ambiente'] for a in ambienti if a['id']==x][0], key="amb_cust_mod")
            c1, c2, c3 = st.columns(3)
            categoria = c1.selectbox("Categoria", ["basi", "pensili", "colonne", "mensole"])
            nome_mod = c2.text_input("Nome Modulo Custom", "Base Custom")
            apertura = c3.selectbox("Tipo Apertura", ["ante", "cassetti", "vasistas"])
            
            d1, d2, d3 = st.columns(3)
            L = d1.number_input("Larghezza (mm)", value=600, step=10, key="cust_l")
            H = d2.number_input("Altezza (mm)", value=720, step=10, key="cust_h")
            P = d3.number_input("Profondità (mm)", value=560, step=10, key="cust_p")
            
            finitura_custom = st.selectbox("Finitura Frontale / Anta", finiture_lista, key="fin_cust")
            
            if st.button("💾 Salva Modulo Custom"):
                mod_base = supabase.table("moduli_base").insert({
                    "ambiente_id": amb_m,
                    "categoria": categoria,
                    "nome_modulo": nome_mod,
                    "larghezza_mm": L,
                    "altezza_mm": H,
                    "profondita_mm": P,
                    "tipo_apertura": apertura
                }).execute().data[0]
                
                fin_obj = next((m for m in mat_db if m["nome_finitura"] == finitura_custom), None)
                if fin_obj:
                    supabase.table("configurazione_modulo_variante").insert({
                        "variante_id": variante_id,
                        "modulo_base_id": mod_base["id"],
                        "finitura_id": fin_obj["id"]
                    }).execute()
                st.success("Modulo Custom creato!")
                st.rerun()

    # --- TAB 2: GOLE & ZOCCOLI ---
    with tab_m2:
        col_gz1, col_gz2 = st.columns(2)
        amb_gz = col_gz1.selectbox("Ambiente Destinazione", options=[a['id'] for a in ambienti], format_func=lambda x: [a['nome_ambiente'] for a in ambienti if a['id']==x][0], key="amb_gz")
        cat_gz = col_gz2.selectbox("Tipo Elemento", ["gole_zoccoli"], format_func=lambda x: "Gola / Zoccolo")
        
        g1, g2, g3 = st.columns(3)
        nome_gz = g1.text_input("Descrizione Elemento", "Zoccolo Alluminio H100")
        L_gz = g2.number_input("Lunghezza (mm)", value=2400, step=50, key="lgz")
        H_gz = g3.number_input("Altezza (mm)", value=100, step=10, key="hgz")
        
        finitura_gz = st.selectbox("Finitura / Colore", finiture_lista, key="fin_gz")

        if st.button("💾 Salva Gola / Zoccolo"):
            mod_base = supabase.table("moduli_base").insert({
                "ambiente_id": amb_gz,
                "categoria": "gole_zoccoli",
                "nome_modulo": nome_gz,
                "larghezza_mm": L_gz,
                "altezza_mm": H_gz,
                "profondita_mm": 20,
                "tipo_apertura": "fisso"
            }).execute().data[0]
            
            fin_obj = next((m for m in mat_db if m["nome_finitura"] == finitura_gz), None)
            if fin_obj:
                supabase.table("configurazione_modulo_variante").insert({
                    "variante_id": variante_id,
                    "modulo_base_id": mod_base["id"],
                    "finitura_id": fin_obj["id"]
                }).execute()
            st.success("Gola / Zoccolo inserito!")
            st.rerun()

    # --- TAB 3: ILLUMINAZIONE ---
    with tab_m3:
        col_lu1, col_lu2 = st.columns(2)
        amb_lu = col_lu1.selectbox("Ambiente Destinazione", options=[a['id'] for a in ambienti], format_func=lambda x: [a['nome_ambiente'] for a in ambienti if a['id']==x][0], key="amb_lu")
        nome_lu = col_lu2.text_input("Descrizione Luce / LED", "Barra LED Sottopensile")
        
        u1, u2, u3 = st.columns(3)
        L_lu = u1.number_input("Lunghezza (mm)", value=1200, step=50, key="llu")
        H_lu = u2.number_input("Altezza/Profilo (mm)", value=10, step=1, key="hlu")
        P_lu = u3.number_input("Profondità/Incasso (mm)", value=10, step=1, key="plu")
        
        finitura_lu = st.selectbox("Temperatura Luce / Profilo", finiture_lista, key="fin_lu")

        if st.button("💾 Salva Illuminazione"):
            mod_base = supabase.table("moduli_base").insert({
                "ambiente_id": amb_lu,
                "categoria": "illuminazione",
                "nome_modulo": nome_lu,
                "larghezza_mm": L_lu,
                "altezza_mm": H_lu,
                "profondita_mm": P_lu,
                "tipo_apertura": "luce"
            }).execute().data[0]
            
            fin_obj = next((m for m in mat_db if m["nome_finitura"] == finitura_lu), None)
            if fin_obj:
                supabase.table("configurazione_modulo_variante").insert({
                    "variante_id": variante_id,
                    "modulo_base_id": mod_base["id"],
                    "finitura_id": fin_obj["id"]
                }).execute()
            st.success("Elemento Illuminazione inserito!")
            st.rerun()

    # --- TAB 4: ACCESSORI & FERRAMENTA ---
    with tab_m4:
        acc_db = supabase.table("accessori_ferramenta").select("*").execute().data
        col_ac1, col_ac2 = st.columns(2)
        amb_ac = col_ac1.selectbox("Ambiente Destinazione", options=[a['id'] for a in ambienti], format_func=lambda x: [a['nome_ambiente'] for a in ambienti if a['id']==x][0], key="amb_ac")
        
        if acc_db:
            opzioni_acc = {f"{a['codice']} - {a['nome']} (€ {a['costo_unitario']})": a for a in acc_db}
            acc_sel_key = col_ac2.selectbox("Seleziona Accessorio da Listino", list(opzioni_acc.keys()))
            acc_obj = opzioni_acc[acc_sel_key]
            
            q1, q2 = st.columns(2)
            qta_acc = q1.number_input("Quantità / Moduli", value=1, min_value=1, step=1)
            desc_acc_custom = q2.text_input("Note / Descrizione Personalizzata", value=acc_obj['nome'])
            
            if st.button("💾 Salva Accessorio nell'Ambiente"):
                mod_base = supabase.table("moduli_base").insert({
                    "ambiente_id": amb_ac,
                    "categoria": "accessori",
                    "nome_modulo": desc_acc_custom,
                    "larghezza_mm": qta_acc * 100, # Usiamo la larghezza per memorizzare la quantità base
                    "altezza_mm": 0,
                    "profondita_mm": 0,
                    "tipo_apertura": "accessorio",
                    "num_ante": qta_acc
                }).execute().data[0]
                st.success("Accessorio inserito!")
                st.rerun()
        else:
            st.info("Nessun accessorio presente nel listino. Configurali nell'Amministrazione.")

    # ==========================================
    # 5. VISUALIZZAZIONE & EDITING PER AMBIENTE
    # ==========================================
    st.divider()
    
    res_mod_base = supabase.table("moduli_base").select("*, ambienti!inner(progetto_id, nome_ambiente)").eq("ambienti.progetto_id", progetto_id).execute()
    moduli_totali = res_mod_base.data
    
    res_cfg = supabase.table("configurazione_modulo_variante").select("*, finiture_materiali(*)").eq("variante_id", variante_id).execute()
    cfg_map = {c["modulo_base_id"]: c["finiture_materiali"] for c in res_cfg.data if c.get("finiture_materiali")}
    
    soglie_db = supabase.table("soglie_cerniere").select("*").execute().data
    prezzi_acc_map = {a["codice"]: float(a["costo_unitario"]) for a in (acc_db or [])}

    righe_preventivo = []
    
    for m in moduli_totali:
        m_id = m["id"]
        fin_info = cfg_map.get(m_id)
        nome_fin = fin_info["nome_finitura"] if fin_info else (default_anta or "Laminato Standard")
        
        prezzi_mat_map = {mat["spessore_mm"]: float(mat["costo_mq"]) for mat in mat_db if mat["nome_finitura"] == nome_fin}

        if m.get("costo_manuale") is not None:
            costo_ind = float(m["costo_manuale"])
        else:
            costo_ind = calcola_modulo_parametrico(
                categoria=m["categoria"],
                L_mm=m["larghezza_mm"],
                H_mm=m["altezza_mm"],
                P_mm=m["profondita_mm"],
                spessore_mensola_mm=m.get("spessore_mensola_mm", 30),
                tipo_apertura=m.get("tipo_apertura", "ante"),
                num_ante=m.get("num_ante", 1),
                num_cassetti=m.get("num_cassetti", 0),
                prezzi_mat=prezzi_mat_map,
                prezzi_acc=prezzi_acc_map,
                soglie_cerniere=soglie_db
            )
        
        prezzo_ricaricato = costo_ind * (1 + (ricarico_p / 100))
        
        righe_preventivo.append({
            "id": m_id,
            "Ambiente": m["ambienti"]["nome_ambiente"],
            "categoria": m["categoria"],
            "nome_modulo": m["nome_modulo"],
            "larghezza_mm": m["larghezza_mm"],
            "altezza_mm": m["altezza_mm"],
            "profondita_mm": m["profondita_mm"],
            "tipo_apertura": m.get("tipo_apertura", "ante"),
            "num_ante": m.get("num_ante", 1),
            "num_cassetti": m.get("num_cassetti", 0),
            "Finitura": nome_fin,
            "costo_industriale": costo_ind,
            "prezzo_ricaricato": prezzo_ricaricato
        })

    if righe_preventivo:
        df_prev_all = pd.DataFrame(righe_preventivo)
        
        # Mappatura delle 4 Categorie Richieste
        def mappa_gruppo(cat):
            cat_l = str(cat).lower()
            if cat_l in ["gole_zoccoli", "zoccoli", "gole"]:
                return "Gole & Zoccoli"
            elif cat_l in ["illuminazione", "luci"]:
                return "Illuminazione"
            elif cat_l in ["accessori", "ferramenta"]:
                return "Accessori & Ferramenta"
            else:
                return "Moduli"

        df_prev_all["Gruppo"] = df_prev_all["categoria"].apply(mappa_gruppo)

        for amb_obj in ambienti:
            amb_nome = amb_obj["nome_ambiente"]
            df_amb = df_prev_all[df_prev_all["Ambiente"] == amb_nome]
            
            if df_amb.empty:
                continue
                
            st.markdown(f"### 📍 Ambiente: `{amb_nome}`")
            
            gruppi = ["Moduli", "Gole & Zoccoli", "Illuminazione", "Accessori & Ferramenta"]
            
            for grp in gruppi:
                df_grp = df_amb[df_amb["Gruppo"] == grp]
                if not df_grp.empty:
                    st.markdown(f"#### 🔹 {grp}")
                    
                    df_display = df_grp[[
                        "id", "nome_modulo", "larghezza_mm", "altezza_mm", 
                        "profondita_mm", "tipo_apertura", "num_ante", "num_cassetti", 
                        "Finitura", "costo_industriale", "prezzo_ricaricato"
                    ]].copy()
                    
                    df_edited = st.data_editor(
                        df_display,
                        key=f"editor_{amb_obj['id']}_{grp}",
                        hide_index=True,
                        column_config={
                            "id": None, # Nasconde l'ID
                            "nome_modulo": st.column_config.TextColumn("Modulo / Descrizione", required=True),
                            "larghezza_mm": st.column_config.NumberColumn("Larghezza (mm)", step=10),
                            "altezza_mm": st.column_config.NumberColumn("Altezza (mm)", step=10),
                            "profondita_mm": st.column_config.NumberColumn("Profondità (mm)", step=10),
                            "tipo_apertura": st.column_config.SelectboxColumn("Apertura", options=["ante", "cassetti", "vasistas", "fisso", "luce", "accessorio"]),
                            "num_ante": st.column_config.NumberColumn("Ante/Qtà", step=1),
                            "num_cassetti": st.column_config.NumberColumn("Cassetti", step=1),
                            "Finitura": st.column_config.Column("Finitura", options=finiture_lista, required=True),
                            "costo_industriale": st.column_config.NumberColumn("Costo Ind. (€)", format="%.2f €", min_value=0.0),
                            "prezzo_ricaricato": st.column_config.NumberColumn("Prezzo (€)", format="%.2f €", disabled=True)
                        },
                        use_container_width=True
                    )
                    
                    # Tasto Salvataggio Modifiche Tabella
                    col_sav, col_tot = st.columns([2, 2])
                    with col_sav:
                        if st.button(f"💾 Salva Modifiche {grp} ({amb_nome})", key=f"btn_sav_{amb_obj['id']}_{grp}"):
                            for _, row in df_edited.iterrows():
                                m_id = row["id"]
                                supabase.table("moduli_base").update({
                                    "nome_modulo": row["nome_modulo"],
                                    "larghezza_mm": int(row["larghezza_mm"]),
                                    "altezza_mm": int(row["altezza_mm"]),
                                    "profondita_mm": int(row["profondita_mm"]),
                                    "tipo_apertura": row["tipo_apertura"],
                                    "num_ante": int(row["num_ante"]),
                                    "num_cassetti": int(row["num_cassetti"])
                                    "costo_manuale": float(row["costo_industriale"])
                                }).eq("id", row["id"]).execute()

                                fin_obj = next((m for m in mat_db if m["nome_finitura"] == row["Finitura"]), None)
                                if fin_obj:
                                    cfg_exist = supabase.table("configurazione_modulo_variante").select("id").eq("variante_id", variante_id).eq("modulo_base_id", m_id).execute().data
                                    if cfg_exist:
                                        supabase.table("configurazione_modulo_variante").update({
                                            "finitura_id": fin_obj["id"]
                                        }).eq("id", cfg_exist[0]["id"]).execute()
                                    else:
                                        supabase.table("configurazione_modulo_variante").insert({
                                            "variante_id": variante_id,
                                            "modulo_base_id": m_id,
                                            "finitura_id": fin_obj["id"]
                                        }).execute()
                                        
                            st.success(f"Modifiche salvate per {grp}!")
                            st.rerun()

                    subtot_grp = df_grp["prezzo_ricaricato"].sum()
                    with col_tot:
                        st.metric(f"Subtotale {grp}", f"€ {subtot_grp:.2f}")

                    st.markdown("---")

        # --- OPZIONE DI ELIMINAZIONE MODULI ---
        with st.expander("🗑️ Rimuovi Elemento dall'Ambiente"):
            id_del = st.selectbox(
                "Seleziona elemento da eliminare:", 
                options=df_prev_all["id"].tolist(),
                format_func=lambda x: f"{df_prev_all[df_prev_all['id']==x]['nome_modulo'].values[0]} ({df_prev_all[df_prev_all['id']==x]['Ambiente'].values[0]})"
            )
            if st.button("Elimina Elemento"):
                supabase.table("moduli_base").delete().eq("id", id_del).execute()
                st.success("Elemento eliminato!")
                st.rerun()

        # ==========================================
        # 6. TOTALI GENERALI E EXPORT PREVENTIVO
        # ==========================================
        tot_costo_ind = df_prev_all["costo_industriale"].sum()
        tot_ricarici = tot_costo_ind * (1 + (ricarico_p / 100))
        tot_scontato = tot_ricarici * (1 - (sconto_f / 100))
        tot_finale = tot_scontato * (1 + (mont_p / 100))

        st.subheader(f"📊 Totali Preventivo — Variante: {variante_attuale['nome_variante']}")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Tot. Costo Industriale", f"€ {tot_costo_ind:.2f}")
        r2.metric(f"Tot. Listino (Ricarico {ricarico_p}%)", f"€ {tot_ricarici:.2f}")
        r3.metric(f"Tot. Scontato ({sconto_f}%)", f"€ {tot_scontato:.2f}")
        r4.metric(f"PREZZO FINALE (+{mont_p}% Mont.)", f"€ {tot_finale:.2f}")

        st.divider()
        col_exp1, col_exp2 = st.columns(2)
        excel_data = genera_excel_preventivo(
            df_moduli=df_prev_all,
            progetto_nome=f"{cliente_attuale['ragione_sociale']} - {progetto_attuale['nome_progetto']}",
            ricarico_proj=ricarico_p,
            sconto_fin=sconto_f,
            ricarico_mont=mont_p
        )
        col_exp1.download_button(
            label="📊 Scarica Excel (Uso Interno)",
            data=excel_data,
            file_name=f"Preventivo_{cliente_attuale['ragione_sociale']}_{progetto_attuale['nome_progetto']}_{variante_attuale['nome_variante']}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        pdf_data = genera_pdf_preventivo(
            df_moduli=df_prev_all,
            cliente_nome=cliente_attuale["ragione_sociale"],
            indirizzo=progetto_attuale.get("indirizzo") or cliente_attuale.get("indirizzo", ""),
            sconto_fin=sconto_f,
            ricarico_mont=mont_p,
            ricarico_proj=ricarico_p
        )
        col_exp2.download_button(
            label="📄 Scarica PDF Offerta Cliente",
            data=pdf_data,
            file_name=f"Offerta_{cliente_attuale['ragione_sociale']}_{progetto_attuale['nome_progetto']}_{variante_attuale['nome_variante']}.pdf",
            mime="application/pdf"
        )
    else:
        st.info("Nessun elemento ancora inserito in questo progetto.")
