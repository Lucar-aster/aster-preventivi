import streamlit as st
from supabase import create_client, Client

# 1. Configurazione globale della pagina (DEVE essere l'unica nell'intero progetto)
st.set_page_config(page_title="K-Contract ERP", page_icon="🍳", layout="wide")

# 2. Inizializzazione unica di Supabase
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"].strip()
    key = st.secrets["SUPABASE_KEY"].strip()
    if url.endswith("/"): url = url[:-1]
    return create_client(url, key)

supabase = init_supabase()

# Passiamo il client Supabase alle sottopagine tramite il session_state
if "supabase" not in st.session_state:
    st.session_state["supabase"] = supabase


# 3. Definizione dei percorsi dei file per ogni pagina
page_preventivatore = st.Page("views/preventivatore.py", title="Preventivatore Commesse", icon="📊", default=True)
page_materiali = st.Page("views/materiali.py", title="Gestionale Materiali", icon="🪵")
page_accessori = st.Page("views/accessori.py", title="Catalogo Accessori", icon="🛠️")
page_modelli = st.Page("views/modelli.py", title="Libreria Modelli (Blocchi)", icon="🧱")

# 4. Creazione della navigazione con raggruppamenti eleganti nella sidebar
pg = st.navigation({
    "Operativo": [page_preventivatore],
    "Anagrafiche & Listini": [page_materiali, page_accessori, page_modelli]
})

# 5. Avvio dell'applicazione
pg.run()
