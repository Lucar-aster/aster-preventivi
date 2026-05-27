import streamlit as st
import pandas as pd

# Recupero della connessione centralizzata
supabase = st.session_state["supabase"]

# =========================================================================
# UTILITY DI CARICAMENTO DATI CON CACHING SELETTIVO
# =========================================================================
@st.cache_data(ttl=600)
def load_materiali():
    try:
        res = supabase.table("materiali").select("id, nome, prezzo_mq, prezzo_ml, categoria").execute()
        df = pd.DataFrame(res.data) if res.data else pd.DataFrame()
        if not df.empty:
            df['prezzo_mq'] = df['prezzo_mq'].fillna(0.0).astype(float)
            df['prezzo_ml'] = df['prezzo_ml'].fillna(0.0).astype(float)
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=600)
def load_clienti():
    try:
        res = supabase.table("clienti").select("*").execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame(columns=['id', 'nome_cliente'])
    except Exception:
        return pd.DataFrame(columns=['id', 'nome_cliente'])

# I dati dinamici legati alla commessa NON usano il caching per aggiornarsi all'istante
def load_progetti():
    res = supabase.table("progetti").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

def load_tipologies(progetto_id):
    res = supabase.table("tipologie_cucine").select("*").eq("progetto_id", progetto_id).execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

def load_istanze_blocchi_ottimizzato(tipologia_id):
    """Eager Loading: Scarica blocchi, modelli e accessori in un'unica chiamata."""
    try:
        res = supabase.table("istanze_blocchi")\
            .select("*, catalogo_modelli(*), istanze_blocchi_accessori(*, catalogo_accessori(*))")\
            .eq("tipologia_id", tipologia_id)\
            .execute()
        return res.data if res.data else []
    except Exception:
        return []

# =========================================================================
# MOTORE DI CALCOLO MATEMATICO
# =========================================================================
def calcola_mq_reali_geometrico(tipo, L, P, H, n_ripiani, h_eldom):
    """
    Calcola lo sviluppo reale in MQ dei componenti della cassa e delle ante 
    basandosi sulla fisica costruttiva del mobile (misure espresse in mm).
    """
    L, P, H = float(L), float(P), float(H)
    n_ripiani = int(n_ripiani or 0)
    h_eldom = float(h_eldom or 0)
    
    famiglia = str(tipo).lower()
    
    # 1. SVILUPPO GEOMETRICO CASSA (Convertito in MQ dividendo per 1.000.000)
    if famiglia == "base":
        # 2 Fianchi (P x H) + 1 Fondo (L x P) + N Ripiani (L x P)
        mm2_cassa = (2 * (P * H)) + (L * P) + (n_ripiani * (L * P))
        mq_cassa = mm2_cassa / 1000000.0
    elif famiglia in ["pensile", "colonna"]:
        # 2 Fianchi (P x H) + 1 Fondo (L x P) + 1 Cielo (L x P) + N Ripiani (L x P)
        mm2_cassa = (2 * (P * H)) + (2 * (L * P)) + (n_ripiani * (L * P))
        mq_cassa = mm2_cassa / 1000000.0
    else:
        # Gole, Zoccoli, Accessori non sviluppano cubatura cassa superficiale
        mq_cassa = 0.0

    # 2. SVILUPPO SCHIENA (Superficie posteriore pulita L x H)
    if famiglia in ["base", "pensile", "colonna"]:
        mq_schiena = (L * H) / 1000000.0
    else:
        mq_schiena = 0.0

    # 3. SVILUPPO ANTE (Sottrazione vano elettrodomestico: L x (H - Heldom))
    if famiglia in ["base", "pensile", "colonna"]:
        h_effettiva_anta = max(0.0, H - h_eldom)
        mq_ante = (L * h_effettiva_anta) / 1000000.0
    else:
        mq_ante = 0.0

    return {
        "cassa": round(mq_cassa, 3),
        "schiena": round(mq_schiena, 3),
        "ante": round(mq_ante, 3)
    }

def risolvi_materiale_effettivo(ist, cucina, progetto, componente):
    """Risolve la cascata gerarchica delle finiture (Cucina Overridden -> Capitolato Progetto)."""
    if componente == "cassa":
        return cucina.get('finitura_cassa_overridden') or progetto.get('default_cassa_id')
    elif componente == "schiena":
        return cucina.get('finitura_cassa_overridden') or progetto.get('default_schiena_id')
    elif componente == "ante":
        return cucina.get('finitura_ante_overridden') or proyecto.get('default_ante_id')
    elif componente == "gole":
        return cucina.get('finitura_gole_overridden') or progetto.get('default_gole_id')
    elif componente == "zoccoli":
        return cucina.get('finitura_zoccoli_overridden') or progetto.get('default_zoccoli_id')
    return None

# =========================================================================
# UI SIDEBAR - STRUTTURA GERARCHICA
# =========================================================================
df_materiali = load_materiali()
df_clienti = load_clienti()
df_progetti = load_progetti()

st.sidebar.subheader("📂 Selezione Commessa")

# 1. Cliente
lista_clienti = df_clienti['nome_cliente'].tolist() if not df_clienti.empty else []
scelta_cliente = st.sidebar.selectbox("👤 Seleziona Cliente", lista_clienti + ["➕ Aggiungi Nuovo Cliente..."])

if scelta_cliente == "➕ Aggiungi Nuovo Cliente...":
    nuovo_cliente = st.sidebar.text_input("Ragione Sociale / Nome Cliente")
    if st.sidebar.button("💾 Salva Cliente", type="primary") and nuovo_cliente:
        supabase.table("clienti").insert({"nome_cliente": nuovo_cliente}).execute()
        st.cache_data.clear()
        st.rerun()
    st.stop()

cliente_id = df_clienti[df_clienti['nome_cliente'] == scelta_cliente].iloc[0]['id']

# 2. Progetto/Commessa filtrata
df_progetti_filtrati = df_progetti[df_progetti['cliente_id'] == cliente_id] if not df_progetti.empty else pd.DataFrame()
lista_prog = df_progetti_filtrati['nome_progetto'].tolist() if not df_progetti_filtrati.empty else []
scelta_progetto = st.sidebar.selectbox("🏢 Seleziona Commessa", lista_prog + ["➕ Aggiungi Nuova Commessa..."])

if scelta_progetto == "➕ Aggiungi Nuova Commessa...":
    nuova_commessa = st.sidebar.text_input("Codice / Nome Commessa")
    if st.sidebar.button("💾 Salva Commessa", type="primary") and nuova_commessa:
        def_mat = df_materiali.iloc[0]['id'] if not df_materiali.empty else None
        supabase.table("progetti").insert({
            "nome_progetto": nuova_commessa, "cliente_id": cliente_id,
            "default_cassa_id": def_mat, "default_schiena_id": def_mat,
            "default_ante_id": def_mat, "default_gole_id": def_mat, "default_zoccoli_id": def_mat
        }).execute()
        st.rerun()
    st.stop()

progetto_attivo = df_progetti_filtrati[df_progetti_filtrati['nome_progetto'] == scelta_progetto].iloc[0].to_dict()

# 3. Capitolato di Progetto (Senza Loop)
st.sidebar.markdown("---")
st.sidebar.subheader("📐 Capitolato Generale")

mat_casse = df_materiali[df_materiali['categoria'] == 'cassa']
mat_ante = df_materiali[df_materiali['categoria'] == 'anta']
mat_lineari = df_materiali[df_materiali['categoria'] == 'lineare']

def safe_idx(df_sub, target_id):
    if target_id in df_sub['id'].values:
        return df_sub['nome'].tolist().index(df_sub[df_sub['id'] == target_id].iloc[0]['nome'])
    return 0

sel_cassa = st.sidebar.selectbox("Struttura (Cassa 18 + Schiena 8)", mat_casse['nome'].tolist(), index=safe_idx(mat_casse, progetto_attivo.get('default_cassa_id')))
sel_ante = st.sidebar.selectbox("Finitura Ante", mat_ante['nome'].tolist(), index=safe_idx(mat_ante, progetto_attivo.get('default_ante_id')))
sel_gole = st.sidebar.selectbox("Profilo Gole", mat_lineari['nome'].tolist(), index=safe_idx(mat_lineari, progetto_attivo.get('default_gole_id')))
sel_zoccoli = st.sidebar.selectbox("Finitura Zoccoli", mat_lineari['nome'].tolist(), index=safe_idx(mat_lineari, progetto_attivo.get('default_zoccoli_id')))

id_cassa = mat_casse[mat_casse['nome'] == sel_cassa].iloc[0]['id']
id_ante = mat_ante[mat_ante['nome'] == sel_ante].iloc[0]['id']
id_gole = mat_lineari[mat_lineari['nome'] == sel_gole].iloc[0]['id']
id_zoccoli = mat_lineari[mat_lineari['nome'] == sel_zoccoli].iloc[0]['id']

if (str(id_cassa) != str(progetto_attivo.get('default_cassa_id')) or
    str(id_ante) != str(progetto_attivo.get('default_ante_id')) or
    str(id_gole) != str(progetto_attivo.get('default_gole_id')) or
    str(id_zoccoli) != str(progetto_attivo.get('default_zoccoli_id'))):
    
    if st.sidebar.button("💾 Aggiorna Capitolato", type="primary", use_container_width=True):
        supabase.table("progetti").update({
            "default_cassa_id": id_cassa, "default_schiena_id": id_cassa,
            "default_ante_id": id_ante, "default_gole_id": id_gole, "default_zoccoli_id": id_zoccoli
        }).eq("id", progetto_attivo['id']).execute()
        st.rerun()

# =========================================================================
# INTERFACCIA CENTRALE - COMPUTO METRICO
# =========================================================================
st.title(f"📊 Preventivatore Contract")
st.caption(f"Cliente: **{scelta_cliente}** | Commessa attiva: **{scelta_progetto}**")

df_cucine = load_tipologies(progetto_attivo['id'])
prezzi_dict = df_materiali.set_index('id').to_dict('index')

if df_cucine.empty:
    st.info("Nessuna cucina o locale associato a questa commessa. Aggiungi una tipologia per iniziare.")
else:
    totalone_commessa = 0.0
    
    for _, cucina_row in df_cucine.iterrows():
        c_id = cucina_row['id']
        st.markdown(f"### 🏢 Tipologia: {cucina_row['nome_cucina']}")
        
        # Sviluppo ed Eager Loading
        istanze = load_istanze_blocchi_ottimizzato(c_id)
        costo_cucina_singola = 0.0
        
        for ist in istanze:
            modello = ist['catalogo_modelli']
            qta = int(ist.get('quantita') or 1)
            L = int(ist.get('L') or ist.get('l') or 0)
            P = int(ist.get('P') or ist.get('p') or 0)
            H = int(ist.get('H') or ist.get('h') or 0)
            
            # Calcolo Materiali
            if modello['metodo_calcolo'] == 'lineare':
                tag = (str(modello.get('tipo', '')) + str(modello.get('codice', ''))).lower()
                cat_lin = "zoccoli" if "zoccolo" in tag else "gole"
                mat_id = risolvi_materiale_effettivo(ist, cucina_row, progetto_attivo, cat_lin)
                prezzo_ml = float(prezzi_dict.get(mat_id, {}).get('prezzo_ml') or 0.0)
                costo_mat = (L / 1000.0) * prezzo_ml
            else:
                m_cassa = risolvi_materiale_effettivo(ist, cucina_row, proyecto_attivo, "cassa")
                m_ante = risolvi_materiale_effettivo(ist, cucina_row, progetto_attivo, "ante")
                p_cassa = float(prezzi_dict.get(m_cassa, {}).get('prezzo_mq') or 0.0)
                p_ante = float(prezzi_dict.get(m_ante, {}).get('prezzo_mq') or 0.0)
                
                # Estraiamo i dati di scomposizione dal modello master
                t_modello = modello.get('tipo', 'Base')
                ripiani_modello = modello.get('n_ripiani', 0)
                eldom_modello = modello.get('h_eldom', 0)
                
                # Calcolo geometrico analitico
                mq = calcola_mq_reali_geometrico(t_modello, L, P, H, ripiani_modello, eldom_modello)
                
                # La cassa e la schiena ereditano lo stesso prezzo al MQ (spessore 18mm e spessore 8mm unificati)
                costo_mat = (mq['cassa'] * p_cassa) + (mq['schiena'] * p_cassa) + (mq['ante'] * p_ante)
                
            # Calcolo Ferramenta istantaneo (zero chiamate di rete)
            costo_ferr = 0.0
            for acc_link in ist.get('istanze_blocchi_accessori', []):
                p_unit = float(acc_link.get('catalogo_accessori', {}).get('prezzo') or 0.0)
                costo_ferr += p_unit * int(acc_link.get('quantita', 1))
                
            costo_cucina_singola += (costo_mat + costo_ferr) * qta
            
        lotto_unita = int(cucina_row.get('quantita_lotto', 1))
        costo_totale_lotto = costo_cucina_singola * lotto_unita
        totalone_commessa += costo_totale_lotto
        
        # Render Righe di Riepilogo Economico
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Costo Unitario Tipologia", f"€ {costo_cucina_singola:,.2f}")
        col_m2.metric(f"Totale Lotto ({lotto_unita} pz)", f"€ {costo_totale_lotto:,.2f}")
        
        # 5 Colonne di Configurazione Sovrascritture (Senza Loop)
        with st.expander("🛠️ Personalizza Finiture Speciali per questa Tipologia"):
            col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns(5)
            
            l_casse = ["default"] + mat_casse['nome'].tolist()
            l_ante = ["default"] + mat_ante['nome'].tolist()
            l_lin = ["default"] + mat_lineari['nome'].tolist()
            
            def get_cov_idx(lista, m_id):
                if not m_id: return 0
                n = df_materiali[df_materiali['id'] == m_id]['nome'].tolist()
                return lista.index(n[0]) if n and n[0] in lista else 0

            with col_f1: cov_c = st.selectbox("Cassa", l_casse, index=get_cov_idx(l_casse, cucina_row.get('finitura_cassa_overridden')), key=f"c_{c_id}")
            with col_f2: cov_a = st.selectbox("Ante", l_ante, index=get_cov_idx(l_ante, cucina_row.get('finitura_ante_overridden')), key=f"a_{c_id}")
            with col_f3: cov_g = st.selectbox("Gole", l_lin, index=get_cov_idx(l_lin, cucina_row.get('finitura_gole_overridden')), key=f"g_{c_id}")
            with col_f4: cov_z = st.selectbox("Zoccoli", l_lin, index=get_cov_idx(l_lin, cucina_row.get('finitura_zoccoli_overridden')), key=f"z_{c_id}")
            with col_f5: q_lotto = st.number_input("Quantità Lotto", min_value=1, value=lotto_unita, key=f"q_{c_id}")
            
            u_c = None if cov_c == "default" else df_materiali[df_materiali['nome'] == cov_c].iloc[0]['id']
            u_a = None if cov_a == "default" else df_materiali[df_materiali['nome'] == cov_a].iloc[0]['id']
            u_g = None if cov_g == "default" else df_materiali[df_materiali['nome'] == cov_g].iloc[0]['id']
            u_z = None if cov_z == "default" else df_materiali[df_materiali['nome'] == cov_z].iloc[0]['id']
            
            if (str(u_c) != str(cucina_row.get('finitura_cassa_overridden')) or
                str(u_a) != str(cucina_row.get('finitura_ante_overridden')) or
                str(u_g) != str(cucina_row.get('finitura_gole_overridden')) or
                str(u_z) != str(cucina_row.get('finitura_zoccoli_overridden')) or
                int(q_lotto) != lotto_unita):
                
                if st.button("💾 Salva Finiture Tipologia", key=f"b_save_{c_id}"):
                    supabase.table("tipologie_cucine").update({
                        "finitura_cassa_overridden": u_c, "finitura_ante_overridden": u_a,
                        "finitura_gole_overridden": u_g, "finitura_zoccoli_overridden": u_z,
                        "quantita_lotto": int(q_lotto)
                    }).eq("id", c_id).execute()
                    st.rerun()
        st.markdown("---")
        
    st.header(f"💰 Totale Valore Commessa Contract: € {totalone_commessa:,.2f}")
