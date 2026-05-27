import streamlit as st
import pandas as pd
import json
from uuid import UUID
from supabase import create_client, Client

# =========================================================================
# CONFIGURAZIONE PAGINA STREAMLIT
# =========================================================================
st.set_page_config(
    page_title="K-Contract Enterprise - Preventivatore Cucine",
    page_icon="🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estetica e stile personalizzato tramite CSS
st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    .stMetric { background-color: #f8fafc; padding: 10px; border-radius: 10px; border: 1px solid #e2e8f0; }
    .kpi-title { font-size: 0.8rem; color: #64748b; font-weight: 600; text-transform: uppercase; }
    .kpi-value { font-size: 1.5rem; color: #0f172a; font-weight: 800; }
    </style>
""", unsafe_allow_html=True)

# =========================================================================
# CONNESSIONE A SUPABASE
# =========================================================================
@st.cache_resource
def init_supabase() -> Client:
    """Inizializza il client di Supabase recuperando le credenziali dai secrets."""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except KeyError:
        st.error("Errore: Credenziali Supabase non trovate nei secrets di Streamlit (`.streamlit/secrets.toml`).")
        st.stop()

supabase = init_supabase()

# =========================================================================
# FUNZIONI DI CARICAMENTO DATI (FETCH)
# =========================================================================
def load_materiali():
    """Carica l'elenco completo dei materiali e dei prezzi al MQ/ML."""
    res = supabase.table("materiali").select("*").execute()
    return pd.DataFrame(res.data)

def load_accessori():
    """Carica l'elenco master della ferramenta e degli accessori."""
    res = supabase.table("catalogo_accessori").select("*").execute()
    return pd.DataFrame(res.data)

def load_modelli_catalogo():
    """Carica la libreria master dei modelli standard (MQ e ML)."""
    res = supabase.table("catalogo_modelli").select("*").execute()
    return pd.DataFrame(res.data)

def load_progetti():
    """Carica l'elenco dei progetti contract attivi."""
    res = supabase.table("progetti").select("*").execute()
    return pd.DataFrame(res.data)

def load_tipologie_cucine(progetto_id):
    """Carica le tipologie di cucine associate a un progetto specifico."""
    res = supabase.table("tipologie_cucine").select("*").eq("progetto_id", progetto_id).execute()
    return pd.DataFrame(res.data)

def load_istanze_blocchi(tipologia_id):
    """Carica i blocchi associati a una tipologia di cucina, includendo le relazioni."""
    # Effettuiamo una query relazionale per ottenere anche i dati del modello master
    res = supabase.table("istanze_blocchi")\
        .select("*, catalogo_modelli(*)")\
        .eq("tipologia_id", tipologia_id)\
        .execute()
    return res.data

def load_blocchi_accessori(blocco_id):
    """Carica gli accessori/ferramenta extra associati a uno specifico blocco."""
    res = supabase.table("istanze_blocchi_accessori")\
        .select("*, catalogo_accessori(*)")\
        .eq("istanza_blocco_id", blocco_id)\
        .execute()
    return res.data

# =========================================================================
# LOGICA CORE DI CALCOLO MATEMATICO (MQ & ML & ACCESSORI)
# =========================================================================
def calcola_mq_reali(modello, L, P, H):
    """Calcola i metri quadri dei componenti proporzionalmente alle misure custom."""
    # Rapporti rispetto alle dimensioni standard di catalogo
    ratio_vol = (L * P * H) / (modello['l_std'] * modello['p_std'] * modello['h_std']) if (modello['p_std'] * modello['h_std']) > 0 else 1.0
    ratio_surf = (L * H) / (modello['l_std'] * modello['h_std']) if modello['h_std'] > 0 else 1.0
    
    mq_cassa = float(modello['mq_cassa_std'] or 0) * ratio_vol
    mq_schiena = float(modello['mq_schiena_std'] or 0) * ratio_surf
    mq_ante = float(modello['mq_ante_std'] or 0) * ratio_surf
    
    # Valori di soglia minimi fisici per evitare zeri strutturali
    return {
        "cassa": max(0.05, round(mq_cassa, 3)),
        "schiena": max(0.02, round(mq_schiena, 3)),
        "ante": max(0.02, round(mq_ante, 3))
    }

def risolvi_materiale_effettivo(blocco, cucina, progetto, componente):
    """Risolve l'ereditarietà a cascata del materiale (Blocco -> Cucina -> Progetto)."""
    # 1. Controlla il livello blocco (sovrascrittura specifica)
    val_blocco = blocco.get(f"sovrascrittura_{componente}")
    if val_blocco and val_blocco != "default":
        return val_blocco
    
    # 2. Controlla il livello tipologia cucina
    val_cucina = cucina.get(f"finitura_{componente}_overridden")
    if val_cucina and val_cucina != "default":
        return val_cucina
        
    # 3. Fallback sul default di progetto (capitolato generale)
    return progetto.get(f"default_{componente}_id")

# =========================================================================
# INTERFACCIA UTENTE (UI) - SIDEBAR & LISTINI
# =========================================================================
st.sidebar.title("🍳 K-Contract Pro")
st.sidebar.subheader("Pannello di Controllo")

# Caricamento database globali
df_materiali = load_materiali()
df_accessori = load_accessori()
df_modelli = load_modelli_catalogo()
df_progetti = load_progetti()

# Selezione o Creazione del Progetto
if df_progetti.empty:
    st.warning("Nessun progetto trovato su Supabase. Creane uno per iniziare.")
    nuovo_nome = st.text_input("Nome Nuovo Progetto")
    if st.button("Crea Progetto Iniziale"):
        # Seleziona dei materiali di default arbitrari per il seeding
        cassa_id = df_materiali[df_materiali['categoria']=='cassa'].iloc[0]['id']
        sch_id = df_materiali[df_materiali['categoria']=='schiena'].iloc[0]['id']
        ant_id = df_materiali[df_materiali['categoria']=='anta'].iloc[0]['id']
        lin_id = df_materiali[df_materiali['categoria']=='lineare'].iloc[0]['id']
        
        supabase.table("progetti").insert({
            "nome_progetto": nuovo_nome,
            "default_cassa_id": cassa_id,
            "default_schiena_id": sch_id,
            "default_ante_id": ant_id,
            "default_lineare_id": lin_id
        }).execute()
        st.rerun()

progetto_selezionato_nome = st.sidebar.selectbox(
    "Seleziona Commessa Contract", 
    df_progetti['nome_progetto'].tolist()
)
progetto_attivo = df_progetti[df_progetti['nome_progetto'] == progetto_selezionato_nome].iloc[0].to_dict()

# Mostra e modifica i default di capitolato direttamente nella Sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("Default Capitolato Progetto")

# Dropdown di selezione materiali di default nella sidebar
def_cassa = st.sidebar.selectbox(
    "Cassa Default (18mm)", 
    df_materiali[df_materiali['categoria']=='cassa']['nome'].tolist(),
    index=df_materiali[df_materiali['categoria']=='cassa']['id'].tolist().index(progetto_attivo['default_cassa_id'])
)
def_schiena = st.sidebar.selectbox(
    "Schiena Default (8mm)", 
    df_materiali[df_materiali['categoria']=='schiena']['nome'].tolist(),
    index=df_materiali[df_materiali['categoria']=='schiena']['id'].tolist().index(progetto_attivo['default_schiena_id'])
)
def_ante = st.sidebar.selectbox(
    "Ante Default", 
    df_materiali[df_materiali['categoria']=='anta']['nome'].tolist(),
    index=df_materiali[df_materiali['categoria']=='anta']['id'].tolist().index(progetto_attivo['default_ante_id'])
)
def_lineare = st.sidebar.selectbox(
    "Profili & Zoccoli Default", 
    df_materiali[df_materiali['categoria']=='lineare']['nome'].tolist(),
    index=df_materiali[df_materiali['categoria']=='lineare']['id'].tolist().index(progetto_attivo['default_lineare_id'])
)

# Rilevamento modifiche per aggiornare Supabase
cassa_uuid = df_materiali[df_materiali['nome'] == def_cassa].iloc[0]['id']
schiena_uuid = df_materiali[df_materiali['nome'] == def_schiena].iloc[0]['id']
ante_uuid = df_materiali[df_materiali['nome'] == def_ante].iloc[0]['id']
lineare_uuid = df_materiali[df_materiali['nome'] == def_lineare].iloc[0]['id']

if (cassa_uuid != progetto_attivo['default_cassa_id'] or 
    schiena_uuid != progetto_attivo['default_schiena_id'] or 
    ante_uuid != progetto_attivo['default_ante_id'] or
    lineare_uuid != progetto_attivo['default_lineare_id']):
    
    supabase.table("progetti").update({
        "default_cassa_id": cassa_uuid,
        "default_schiena_id": schiena_uuid,
        "default_ante_id": ante_uuid,
        "default_lineare_id": lineare_uuid
    }).eq("id", progetto_attivo['id']).execute()
    st.sidebar.success("Capitolato aggiornato con successo!")
    st.rerun()

# =========================================================================
# MAIN DASHBOARD - CALCOLO VALORE COMMESSA
# =========================================================================
st.title(f"🏢 Contract: {progetto_attivo['nome_progetto']}")
st.write("Sviluppo preventivo industriale integrato per lotti di cucine personalizzate.")

# Carica cucine associate al progetto
df_cucine = load_tipologie_cucine(progetto_attivo['id'])

if df_cucine.empty:
    st.info("Nessuna tipologia di cucina configurata in questa commessa. Aggiungine una per iniziare.")
    nuova_cucina_nome = st.text_input("Nome Nuova Tipologia (es. Cucina Tipo A)")
    unita_lotto = st.number_input("Numero appartamenti nel lotto", min_value=1, value=10)
    if st.button("Aggiungi Cucina Standard"):
        supabase.table("tipologie_cucine").insert({
            "progetto_id": progetto_attivo['id'],
            "nome_cucina": nuova_cucina_nome,
            "quantita_lotto": unita_lotto
        }).execute()
        st.rerun()

# =========================================================================
# LOGICA DI CALCOLO COSTI DETTAGLIATA (BACKGROUND MATH ENGINE)
# =========================================================================
totale_generale_commessa = 0.0
conteggio_appartamenti = 0
dettaglio_costi_cucine = []

# Mappatura materiali in un dizionario per velocizzare i lookup in Python
prezzi_materiali_dict = df_materiali.set_index('id')[['prezzo_mq', 'prezzo_ml']].to_dict('index')
prezzi_accessori_dict = df_accessori.set_index('id')['prezzo'].to_dict()

for idx, cucina in df_cucine.iterrows():
    cucina_dict = cucina.to_dict()
    conteggio_appartamenti += cucina_dict['quantita_lotto']
    istanze = load_istanze_blocchi(cucina_dict['id'])
    
    costo_totale_singola_cucina = 0.0
    
    for ist in istanze:
        modello_master = ist['catalogo_modelli']
        qta_blocco = ist['quantita']
        
        # Identifica il costo dei materiali in base al metodo di computo
        if modello_master['metodo_calcolo'] == 'lineare':
            # 1. COMPUTO A METRO LINEARE (ML) - Es. Gole, Zoccoli
            mat_lineare_id = risolvi_materiale_effettivo(ist, cucina_dict, progetto_attivo, "lineare")
            prezzo_ml = float(prezzi_materiali_dict.get(mat_lineare_id, {}).get("prezzo_ml") or 0.0)
            
            sviluppo_metrico = ist['l'] / 100.0  # Converte la larghezza L da cm a metri lineari
            costo_materiali = sviluppo_metrico * prezzo_ml
        else:
            # 2. COMPUTO TRADIZIONALE A SUPERFICIE (MQ) - Es. Basi, Colonne
            mat_cassa_id = risolvi_materiale_effettivo(ist, cucina_dict, progetto_attivo, "cassa")
            mat_sch_id = risolvi_materiale_effettivo(ist, cucina_dict, progetto_attivo, "schiena")
            mat_anta_id = risolvi_materiale_effettivo(ist, cucina_dict, progetto_attivo, "ante")
            
            p_cassa = float(prezzi_materiali_dict.get(mat_cassa_id, {}).get("prezzo_mq") or 0.0)
            p_schiena = float(prezzi_materiali_dict.get(mat_sch_id, {}).get("prezzo_mq") or 0.0)
            p_ante = float(prezzi_materiali_dict.get(mat_anta_id, {}).get("prezzo_mq") or 0.0)
            
            # Calcola mq reali in base alle dimensioni impostate
            mq_reali = calcola_mq_reali(modello_master, ist['l'], ist['p'], ist['h'])
            
            costo_materiali = (
                (mq_reali['cassa'] * p_cassa) + 
                (mq_reali['schiena'] * p_schiena) + 
                (mq_reali['ante'] * p_ante)
            )
            
        # 3. COMPUTO FERRAMENTA ED ACCESSORI ASSOCIATI (Molti-a-Molti)
        costo_ferramenta = 0.0
        accessori_associati = load_blocchi_accessori(ist['id'])
        for acc in accessori_associati:
            prezzo_un_acc = float(prezzi_accessori_dict.get(acc['accessorio_id']) or 0.0)
            costo_ferramenta += prezzo_un_acc * acc['quantita']
            
        costo_totale_singolo_modulo = costo_materiali + costo_ferramenta
        costo_totale_singola_cucina += costo_totale_singolo_modulo * qta_blocco
        
    costo_lotto_cucina = costo_totale_singola_cucina * cucina_dict['quantita_lotto']
    totale_generale_commessa += costo_lotto_cucina
    
    dettaglio_costi_cucine.append({
        "id": cucina_dict['id'],
        "nome": cucina_dict['nome_cucina'],
        "unita": cucina_dict['quantita_lotto'],
        "singola": costo_totale_singola_cucina,
        "lotto": costo_lotto_cucina,
        "raw_dict": cucina_dict
    })

# =========================================================================
# INDICATORI STATISTICI (KPIs)
# =========================================================================
col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
with col_kpi1:
    st.markdown(f"""
        <div class="stMetric">
            <div class="kpi-title">Valore Totale Commessa</div>
            <div class="kpi-value">€ {totale_generale_commessa:,.2f}</div>
        </div>
    """, unsafe_allow_html=True)
with col_kpi2:
    st.markdown(f"""
        <div class="stMetric">
            <div class="kpi-title">Totale Cucine nel Cantiere</div>
            <div class="kpi-value">{conteggio_appartamenti} Cucine</div>
        </div>
    """, unsafe_allow_html=True)
with col_kpi3:
    costo_medio = totale_generale_commessa / conteggio_appartamenti if conteggio_appartamenti > 0 else 0
    st.markdown(f"""
        <div class="stMetric">
            <div class="kpi-title">Costo Medio per Cucina</div>
            <div class="kpi-value">€ {costo_medio:,.2f}</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# =========================================================================
# SEZIONE PRINCIPALE: COMPOSIZIONI E GESTIONE GRIGLIA MODULI
# =========================================================================
st.header("2. Composizioni Attive")

# Loop sulle diverse cucine nel progetto
for cucina_data in dettaglio_costi_cucine:
    c_id = cucina_data['id']
    raw_cucina = cucina_data['raw_dict']
    
    with st.expander(f"📁 {cucina_data['nome']} — {cucina_data['unita']} unità (Lotto: € {cucina_data['lotto']:,.2f})", expanded=True):
        
        # Sotto-colonne per configurare le finiture della cucina (sovrascrittura opzionale)
        st.markdown("**Sovrascritture Finiture per questa Tipologia:**")
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        
        # Mappatura delle dropdown con opzione "Eredita"
        lista_casse = ["default"] + df_materiali[df_materiali['categoria']=='cassa']['nome'].tolist()
        lista_ante = ["default"] + df_materiali[df_materiali['categoria']=='anta']['nome'].tolist()
        lista_lineari = ["default"] + df_materiali[df_materiali['categoria']=='lineare']['nome'].tolist()
        
        # Trova indice corrente o imposta "default"
        def trova_indice(lista, id_materiale):
            if not id_materiale or id_materiale == "default":
                return 0
            mat_nome = df_materiali[df_materiali['id'] == id_materiale]['nome'].tolist()
            return lista.index(mat_nome[0]) if mat_nome and mat_nome[0] in lista else 0

        with col_f1:
            cov_cassa = st.selectbox(
                "Cassa", lista_casse, 
                index=trova_indice(lista_casse, raw_cucina['finitura_cassa_overridden']),
                key=f"sel_cassa_{c_id}"
            )
        with col_f2:
            cov_ante = st.selectbox(
                "Ante", lista_ante, 
                index=trova_indice(lista_ante, raw_cucina['finitura_ante_overridden']),
                key=f"sel_ante_{c_id}"
            )
        with col_f3:
            cov_lineare = st.selectbox(
                "Profili Lineari", lista_lineari, 
                index=trova_indice(lista_lineari, raw_cucina['finitura_lineare_overridden']),
                key=f"sel_lineare_{c_id}"
            )
        with col_f4:
            nuove_unita = st.number_value = st.number_input(
                "Quantità Lotto", min_value=1, 
                value=int(raw_cucina['quantita_lotto']), 
                key=f"units_{c_id}"
            )

        # Rilevamento modifiche finiture a livello cucina per sincronizzare Supabase
        uuid_cov_cassa = "default" if cov_cassa == "default" else df_materiali[df_materiali['nome'] == cov_cassa].iloc[0]['id']
        uuid_cov_ante = "default" if cov_ante == "default" else df_materiali[df_materiali['nome'] == cov_ante].iloc[0]['id']
        uuid_cov_lineare = "default" if cov_lineare == "default" else df_materiali[df_materiali['nome'] == cov_lineare].iloc[0]['id']

        if (uuid_cov_cassa != raw_cucina['finitura_cassa_overridden'] or 
            uuid_cov_ante != raw_cucina['finitura_ante_overridden'] or 
            uuid_cov_lineare != raw_cucina['finitura_lineare_overridden'] or 
            nuove_unita != raw_cucina['quantita_lotto']):
            
            supabase.table("tipologie_cucine").update({
                "finitura_cassa_overridden": None if uuid_cov_cassa == "default" else uuid_cov_cassa,
                "finitura_ante_overridden": None if uuid_cov_ante == "default" else uuid_cov_ante,
                "finitura_lineare_overridden": None if uuid_cov_lineare == "default" else uuid_cov_lineare,
                "quantita_lotto": nuove_unita
            }).eq("id", c_id).execute()
            st.rerun()

        st.markdown("---")
        
        # =========================================================================
        # TABELLA MODULI E EDITOR INTERATTIVO DI STREAMLIT (st.data_editor)
        # =========================================================================
        st.write("📐 **Griglia di Composizione (Moduli standard MQ & Profili ML):**")
        
        istanze_cucina = load_istanze_blocchi(c_id)
        
        # Costruiamo il dataframe da mostrare nell'editor interattivo
        rows = []
        for ist in istanze_cucina:
            rows.append({
                "ID_RECORD": ist['id'],
                "Codice": ist['catalogo_modelli']['codice'],
                "Tipo": ist['catalogo_modelli']['tipo'],
                "Calcolo": ist['catalogo_modelli']['metodo_calcolo'].upper(),
                "Larghezza (L cm)": ist['l'],
                "Profondità (P cm)": ist['p'],
                "Altezza (H cm)": ist['h'],
                "Quantità": ist['quantita'],
            })
            
        df_editor = pd.DataFrame(rows)
        
        # Configurazione colonne per st.data_editor
        edited_df = st.data_editor(
            df_editor,
            column_config={
                "ID_RECORD": None, # Nasconde la chiave primaria
                "Codice": st.column_config.SelectboxColumn("Modulo Master", options=df_modelli['codice'].tolist(), required=True),
                "Tipo": st.column_config.TextColumn("Tipo", disabled=True),
                "Calcolo": st.column_config.TextColumn("Calcolo", disabled=True),
                "Larghezza (L cm)": st.column_config.NumberColumn("L (cm)", min_value=10, max_value=600, step=1),
                "Profondità (P cm)": st.column_config.NumberColumn("P (cm)", min_value=0, max_value=120, step=1),
                "Altezza (H cm)": st.column_config.NumberColumn("H (cm)", min_value=0, max_value=300, step=1),
                "Quantità": st.column_config.NumberColumn("Q.tà", min_value=1, max_value=100, step=1),
            },
            num_rows="dynamic",
            key=f"editor_{c_id}",
            use_container_width=True
        )
        
        # =========================================================================
        # SINCRONIZZAZIONE DATI (SALVATAGGIO SU SUPABASE A SEGUITO DI EDIT DI RIGA)
        # =========================================================================
        # Confronto righe modificate, aggiunte o cancellate dall'editor
        if st.button("Salva modifiche computo", key=f"btn_save_{c_id}"):
            # 1. Rileva eliminazioni
            if len(edited_df) < len(df_editor):
                deleted_ids = set(df_editor['ID_RECORD']) - set(edited_df['ID_RECORD'])
                for d_id in deleted_ids:
                    supabase.table("istanze_blocchi").delete().eq("id", d_id).execute()
                    
            # 2. Rileva inserimenti o modifiche
            for idx, row in edited_df.iterrows():
                modello_selezionato_codice = row['Codice']
                master_row = df_modelli[df_modelli['codice'] == modello_selezionato_codice].iloc[0].to_dict()
                
                payload = {
                    "tipologia_id": c_id,
                    "modello_id": master_row['id'],
                    "L": int(row['Larghezza (L cm)']),
                    "P": int(row['Profondità (P cm)']),
                    "H": int(row['Altezza (H cm)']),
                    "quantita": int(row['Quantità'])
                }
                
                if pd.isna(row.get('ID_RECORD')) or row.get('ID_RECORD') is None:
                    # Riga Nuova -> Inserimento
                    supabase.table("istanze_blocchi").insert(payload).execute()
                else:
                    # Riga Esistente -> Aggiornamento
                    supabase.table("istanze_blocchi").update(payload).eq("id", row['ID_RECORD']).execute()
                    
            st.success("Computo metrico sincronizzato con Supabase!")
            st.rerun()
            
        # =========================================================================
        # CLONAZIONE COMPOSIZIONE (Tasto "Clona Veloce" per Contract)
        # =========================================================================
        st.markdown("")
        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            if st.button("👥 Clona Cucina", key=f"clona_{c_id}", help="Duplica questa tipologia di cucina e tutti i suoi blocchi all'interno della commessa."):
                # 1. Crea la nuova tipologia
                nuova_tipologia = supabase.table("tipologie_cucine").insert({
                    "progetto_id": progetto_attivo['id'],
                    "nome_cucina": f"{cucina_data['nome']} (Copia)",
                    "quantita_lotto": cucina_data['unita'],
                    "finitura_cassa_overridden": raw_cucina['finitura_cassa_overridden'],
                    "finitura_ante_overridden": raw_cucina['finitura_ante_overridden'],
                    "finitura_lineare_overridden": raw_cucina['finitura_lineare_overridden']
                }).execute()
                
                nuovo_tipologia_id = nuova_tipologia.data[0]['id']
                
                # 2. Clona i singoli blocchi associati
                for ist in istanze_cucina:
                    supabase.table("istanze_blocchi").insert({
                        "tipologia_id": nuovo_tipologia_id,
                        "modello_id": ist['modello_id'],
                        "L": ist['l'],
                        "P": ist['p'],
                        "H": ist['h'],
                        "quantita": ist['quantita'],
                        "sovrascrittura_cassa": ist['sovrascrittura_cassa'],
                        "sovrascrittura_ante": ist['sovrascrittura_ante'],
                        "sovrascrittura_lineare": ist['sovrascrittura_lineare']
                    }).execute()
                    
                st.success("Tipologia di cucina duplicata con successo!")
                st.rerun()
                
        with col_btn2:
            if st.button("🗑️ Elimina Intera Tipologia", key=f"del_{c_id}"):
                supabase.table("tipologie_cucine").delete().eq("id", c_id).execute()
                st.success("Tipologia rimossa.")
                st.rerun()

# =========================================================================
# SEZIONE AGGIUNTIVA: CREAZIONE RAPIDA DI UNA NUOVA TIPOLOGIA DI CUCINA
# =========================================================================
st.markdown("---")
st.header("3. Aggiungi Nuova Tipologia di Cucina")
with st.form("nuova_cucina_form"):
    nome_nuova = st.text_input("Nome Tipologia", placeholder="Es. Cucina Monolocale Tipo C")
    unita_nuove = st.number_input("Quantità Lotto (Numero appartamenti)", min_value=1, value=5)
    submit_btn = st.form_submit_button("Crea Nuova Tipologia vuota")
    
    if submit_btn and nome_nuova:
        supabase.table("tipologie_cucine").insert({
            "progetto_id": progetto_attivo['id'],
            "nome_cucina": nome_nuova,
            "quantita_lotto": unita_nuove
        }).execute()
        st.success(f"Tipologia '{nome_nuova}' creata! Ora puoi aggiungere moduli.")
        st.rerun()
