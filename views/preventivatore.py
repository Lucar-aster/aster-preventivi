import streamlit as st
import pandas as pd

supabase = st.session_state["supabase"]

# =========================================================================
# CARICAMENTO DATI CON CACHING ED EAGER LOOKUP
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

@st.cache_data(ttl=600)
def load_accessori_default_mappa():
    """Scarica tutte le associazioni modelli-accessori per iniettarle istantaneamente a costo zero."""
    try:
        res = supabase.table("modelli_accessori_default").select("modello_id, quantita, catalogo_accessori(prezzo)").execute()
        return res.data if res.data else []
    except Exception:
        return []

def load_progetti():
    res = supabase.table("progetti").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

def load_tipologies(progetto_id):
    res = supabase.table("tipologie_cucine").select("*").eq("progetto_id", progetto_id).execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()

def load_istanze_blocchi_ottimizzato(tipologia_id):
    res = supabase.table("istanze_blocchi")\
        .select("*, catalogo_modelli(*), istanze_blocchi_accessori(*, catalogo_accessori(*))")\
        .eq("tipologia_id", tipologia_id)\
        .execute()
    return res.data if res.data else []

# =========================================================================
# NUOVO MOTORE DI CALCOLO GEOMETRICO PARAMETRICO (CASSETTI INCLUSI)
# =========================================================================
def calcola_mq_reali_geometrico(tipo, L, P, H, n_ripiani, h_eldom, n_cassetti, n_cestelli):
    L, P, H = float(L), float(P), float(H)
    n_ripiani = int(n_ripiani or 0)
    h_eldom = float(h_eldom or 0)
    n_cassetti = int(n_cassetti or 0)
    n_cestelli = int(n_cestelli or 0)
    
    famiglia = str(tipo).lower()
    
    # 1. SVILUPPO CASSA
    if famiglia == "base":
        mm2_cassa = (2 * (P * H)) + (L * P) + (n_ripiani * (L * P))
        mq_cassa = mm2_cassa / 1000000.0
    elif famiglia in ["pensile", "colonna"]:
        mm2_cassa = (2 * (P * H)) + (2 * (L * P)) + (n_ripiani * (L * P))
        mq_cassa = mm2_cassa / 1000000.0
    else:
        mq_cassa = 0.0

    # 2. SVILUPPO SCHIENA
    mq_schiena = (L * H) / 1000000.0 if famiglia in ["base", "pensile", "colonna"] else 0.0

    # 3. SVILUPPO ANTE (Al lordo dei cassetti, l'estetica frontale sottrae solo l'elettrodomestico)
    mq_ante = (L * max(0.0, H - h_eldom)) / 1000000.0 if famiglia in ["base", "pensile", "colonna"] else 0.0

    # 4. SVILUPPO SCATOLA CASSETTI INTERNI (Sponde H120 e H240 + Fondi)
    # Sviluppo singolo cassetto: 2 sponde laterali (P * 120) + Fondo (L * P) + Retro interno (L * 120)
    mm2_singolo_cassetto = (2 * (P * 120)) + (L * P) + (L * 120)
    mm2_singolo_cestello = (2 * (P * 240)) + (L * P) + (L * 240)
    
    mq_cassetti = ((n_cassetti * mm2_singolo_cassetto) + (n_cestelli * mm2_singolo_cestello)) / 1000000.0

    return {
        "cassa": round(mq_cassa, 3),
        "schiena": round(mq_schiena, 3),
        "ante": round(mq_ante, 3),
        "cassetti": round(mq_cassetti, 3)
    }

def risolvi_materiale_effettivo(ist, cucina, progetto, componente):
    if componente == "cassa":
        return cucina.get('finitura_cassa_overridden') or progetto.get('default_cassa_id')
    elif componente == "schiena":
        return cucina.get('finitura_cassa_overridden') or progetto.get('default_schiena_id')
    elif componente == "ante":
        return cucina.get('finitura_ante_overridden') or progetto.get('default_ante_id')
    elif componente == "cassetti":
        return cucina.get('finitura_cassetti_overridden') or progetto.get('default_cassetti_id')
    elif componente == "gole":
        return cucina.get('finitura_gole_overridden') or progetto.get('default_gole_id')
    elif componente == "zoccoli":
        return cucina.get('finitura_zoccoli_overridden') or progetto.get('default_zoccoli_id')
    return None

# =========================================================================
# UI SIDEBAR - NAVIGAZIONE E CAPITOLATO COMMESSE
# =========================================================================
df_materiali = load_materiali()
df_clienti = load_clienti()
df_progetti = load_progetti()
acc_default_lista = load_accessori_default_mappa()

st.sidebar.subheader("📂 Selezione Commessa")
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
            "default_ante_id": def_mat, "default_cassetti_id": def_mat,
            "default_gole_id": def_mat, "default_zoccoli_id": def_mat
        }).execute()
        st.rerun()
    st.stop()

progetto_attivo = df_progetti_filtrati[df_progetti_filtrati['nome_progetto'] == scelta_progetto].iloc[0].to_dict()

# SIDEBAR: SELEZIONE CAPITOLATO CON FINITURA CASSETTI
st.sidebar.markdown("---")
st.sidebar.subheader("📐 Capitolato Generale")

mat_casse = df_materiali[df_materiali['categoria'] == 'cassa']
mat_ante = df_materiali[df_materiali['categoria'] == 'anta']
mat_lineari = df_materiali[df_materiali['categoria'] == 'lineare']

def safe_idx(df_sub, target_id):
    if target_id in df_sub['id'].values:
        return df_sub['nome'].tolist().index(df_sub[df_sub['id'] == target_id].iloc[0]['nome'])
    return 0

sel_cassa = st.sidebar.selectbox("Struttura Scocca", mat_casse['nome'].tolist(), index=safe_idx(mat_casse, progetto_attivo.get('default_cassa_id')))
sel_ante = st.sidebar.selectbox("Finitura Ante", mat_ante['nome'].tolist(), index=safe_idx(mat_ante, progetto_attivo.get('default_ante_id')))
sel_cassetti = st.sidebar.selectbox("Finitura Struttura Cassetti", df_materiali['nome'].tolist(), index=safe_idx(df_materiali, progetto_attivo.get('default_cassetti_id')))
sel_gole = st.sidebar.selectbox("Profilo Gole", mat_lineari['nome'].tolist(), index=safe_idx(mat_lineari, progetto_attivo.get('default_gole_id')))
sel_zoccoli = st.sidebar.selectbox("Finitura Zoccoli", mat_lineari['nome'].tolist(), index=safe_idx(mat_lineari, progetto_attivo.get('default_zoccoli_id')))

id_cassa = mat_casse[mat_casse['nome'] == sel_cassa].iloc[0]['id']
id_ante = mat_ante[mat_ante['nome'] == sel_ante].iloc[0]['id']
id_cassetti = df_materiali[df_materiali['nome'] == sel_cassetti].iloc[0]['id']
id_gole = mat_lineari[mat_lineari['nome'] == sel_gole].iloc[0]['id']
id_zoccoli = mat_lineari[mat_lineari['nome'] == sel_zoccoli].iloc[0]['id']

if (str(id_cassa) != str(progetto_attivo.get('default_cassa_id')) or
    str(id_ante) != str(progetto_attivo.get('default_ante_id')) or
    str(id_cassetti) != str(progetto_attivo.get('default_cassetti_id')) or
    str(id_gole) != str(progetto_attivo.get('default_gole_id')) or
    str(id_zoccoli) != str(progetto_attivo.get('default_zoccoli_id'))):
    
    if st.sidebar.button("💾 Aggiorna Capitolato", type="primary", use_container_width=True):
        supabase.table("progetti").update({
            "default_cassa_id": id_cassa, "default_schiena_id": id_cassa,
            "default_ante_id": id_ante, "default_cassetti_id": id_cassetti,
            "default_gole_id": id_gole, "default_zoccoli_id": id_zoccoli
        }).eq("id", progetto_attivo['id']).execute()
        st.rerun()

# =========================================================================
# COSTRUZIONE INTERFACCIA ED ELABORAZIONE ECONOMICA
# =========================================================================
st.title(f"📊 Preventivatore Contract")
st.caption(f"Cliente: **{scelta_cliente}** | Commessa: **{scelta_progetto}**")

df_cucine = load_tipologies(progetto_attivo['id'])
prezzi_dict = df_materiali.set_index('id').to_dict('index')

# Convertiamo la lista degli accessori di default in un dizionario mappato per velocizzare il ciclo
accessori_def_mappa = {}
for item in acc_default_lista:
    m_id = item['modello_id']
    if m_id not in accessori_def_mappa:
        accessori_def_mappa[m_id] = []
    accessori_def_mappa[m_id].append(item)

if df_cucine.empty:
    st.info("Nessuna tipologia ancora legata a questa commessa.")
else:
    totalone_commessa = 0.0
    
    for _, cucina_row in df_cucine.iterrows():
        c_id = cucina_row['id']
        nome_visualizzato = cucina_row.get('nome_tipologia', cucina_row.get('nome', 'Tipologia Senza Nome'))
        st.markdown(f"### 🏢 Tipologia: {nome_visualizzato}")
        
        istanze = load_istanze_blocchi_ottimizzato(c_id)
        costo_cucina_singola = 0.0
        
        for ist in istanze:
            modello = ist['catalogo_modelli']
            qta = int(ist.get('quantita') or 1)
            L, P, H = int(ist.get('L') or 0), int(ist.get('P') or 0), int(ist.get('H') or 0)
            
            # Sviluppo Materiali e Scocche
            if modello['metodo_calcolo'] == 'lineare':
                tag = (str(modello.get('tipo', '')) + str(modello.get('codice', ''))).lower()
                cat_lin = "zoccoli" if "zoccolo" in tag else "gole"
                mat_id = risolvi_materiale_effettivo(ist, cucina_row, progetto_attivo, cat_lin)
                prezzo_ml = float(prezzi_dict.get(mat_id, {}).get('prezzo_ml') or 0.0)
                costo_mat = (L / 1000.0) * prezzo_ml
            else:
                m_cassa = risolvi_materiale_effettivo(ist, cucina_row, progetto_attivo, "cassa")
                m_ante = risolvi_materiale_effettivo(ist, cucina_row, progetto_attivo, "ante")
                m_cassetti = risolvi_materiale_effettivo(ist, cucina_row, progetto_attivo, "cassetti")
                
                p_cassa = float(prezzi_dict.get(m_cassa, {}).get('prezzo_mq') or 0.0)
                p_ante = float(prezzi_dict.get(m_ante, {}).get('prezzo_mq') or 0.0)
                p_cassetti = float(prezzi_dict.get(m_cassetti, {}).get('prezzo_mq') or 0.0)
                
                # Esecuzione del nuovo algoritmo geometrico
                mq = calcola_mq_reali_geometrico(
                    modello.get('tipo', 'Base'), L, P, H,
                    modello.get('n_ripiani', 0), modello.get('h_eldom', 0),
                    modello.get('n_cassetti', 0), modello.get('n_cestelli', 0)
                )
                
                costo_mat = (mq['cassa'] * p_cassa) + (mq['schiena'] * p_cassa) + (mq['ante'] * p_ante) + (mq['cassetti'] * p_cassetti)
                
            # Calcolo Ferramenta (1. Accessori inseriti manualmente nell'istanza)
            costo_ferr = 0.0
            for acc_link in ist.get('istanze_blocchi_accessori', []):
                p_unit = float(acc_link.get('catalogo_accessori', {}).get('prezzo') or 0.0)
                costo_ferr += p_unit * int(acc_link.get('quantita', 1))
                
            # Calcolo Ferramenta (2. Accessori ereditati AUTOMATICAMENTE dal Modello Master)
            for acc_def in accessori_def_mappa.get(modello['id'], []):
                p_unit = float(acc_def.get('catalogo_accessori', {}).get('prezzo') or 0.0)
                costo_ferr += p_unit * int(acc_def.get('quantita', 1))
                
            costo_cucina_singola += (costo_mat + costo_ferr) * qta
            
        lotto_unita = int(cucina_row.get('quantita_lotto', 1))
        costo_totale_lotto = costo_cucina_singola * lotto_unita
        totalone_commessa += costo_totale_lotto
        
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Costo Unitario Configurazione", f"€ {costo_cucina_singola:,.2f}")
        col_m2.metric(f"Totale Lotto ({lotto_unita} pz)", f"€ {costo_totale_lotto:,.2f}")
        
        # Pannello per le modifiche locali alla tipologia
        with st.expander("🛠️ Personalizza Finiture Speciali e Overrides per questa Tipologia"):
            col_f1, col_f2, col_f3, col_f4, col_f5, col_f6 = st.columns(6)
            l_all = ["default"] + df_materiali['nome'].tolist()
            l_casse = ["default"] + mat_casse['nome'].tolist()
            l_ante = ["default"] + mat_ante['nome'].tolist()
            l_lin = ["default"] + mat_lineari['nome'].tolist()
            
            def get_cov_idx(lista, m_id):
                if not m_id: return 0
                n = df_materiali[df_materiali['id'] == m_id]['nome'].tolist()
                return lista.index(n[0]) if n and n[0] in lista else 0

            with col_f1: cov_c = st.selectbox("Scocca", l_casse, index=get_cov_idx(l_casse, cucina_row.get('finitura_cassa_overridden')), key=f"c_{c_id}")
            with col_f2: cov_a = st.selectbox("Ante", l_ante, index=get_cov_idx(l_ante, cucina_row.get('finitura_ante_overridden')), key=f"a_{c_id}")
            with col_f3: cov_cas = st.selectbox("Cassetti", l_all, index=get_cov_idx(l_all, cucina_row.get('finitura_cassetti_overridden')), key=f"cas_{c_id}")
            with col_f4: cov_g = st.selectbox("Gole", l_lin, index=get_cov_idx(l_lin, cucina_row.get('finitura_gole_overridden')), key=f"g_{c_id}")
            with col_f5: cov_z = st.selectbox("Zoccoli", l_lin, index=get_cov_idx(l_lin, cucina_row.get('finitura_zoccoli_overridden')), key=f"z_{c_id}")
            with col_f6: q_lotto = st.number_input("Q.tà Lotto", min_value=1, value=lotto_unita, key=f"q_{c_id}")
            
            u_c = None if cov_c == "default" else df_materiali[df_materiali['nome'] == cov_c].iloc[0]['id']
            u_a = None if cov_a == "default" else df_materiali[df_materiali['nome'] == cov_a].iloc[0]['id']
            u_cas = None if cov_cas == "default" else df_materiali[df_materiali['nome'] == cov_cas].iloc[0]['id']
            u_g = None if cov_g == "default" else df_materiali[df_materiali['nome'] == cov_g].iloc[0]['id']
            u_z = None if cov_z == "default" else df_materiali[df_materiali['nome'] == cov_z].iloc[0]['id']
            
            if (str(u_c) != str(cucina_row.get('finitura_cassa_overridden')) or
                str(u_a) != str(cucina_row.get('finitura_ante_overridden')) or
                str(u_cas) != str(cucina_row.get('finitura_cassetti_overridden')) or
                str(u_g) != str(cucina_row.get('finitura_gole_overridden')) or
                str(u_z) != str(cucina_row.get('finitura_zoccoli_overridden')) or
                int(q_lotto) != lotto_unita):
                
                if st.button("💾 Salva Finiture Tipologia", key=f"b_save_{c_id}"):
                    supabase.table("tipologie_cucine").update({
                        "finitura_cassa_overridden": u_c, "finitura_ante_overridden": u_a,
                        "finitura_cassetti_overridden": u_cas,
                        "finitura_gole_overridden": u_g, "finitura_zoccoli_overridden": u_z,
                        "quantita_lotto": int(q_lotto)
                    }).eq("id", c_id).execute()
                    st.rerun()
        st.markdown("---")
        
    st.header(f"💰 Totale Valore Commessa Contract: € {totalone_commessa:,.2f}")
