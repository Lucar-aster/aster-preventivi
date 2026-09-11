import streamlit as st
import pandas as pd
from datetime import date
import uuid

st.set_page_config(page_title="Preventivatore Arredi su Misura", page_icon="🪑", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .main-header { font-size: 2.2rem; color: #0F172A; font-weight: 700; margin-bottom: 0.2rem; }
    .sub-header { font-size: 1rem; color: #475569; margin-bottom: 1.5rem; }
    .stButton>button { border-radius: 6px; font-weight: 600; }
    .metric-card { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1rem; text-align: center; }
    .stNumberInput { margin-bottom: 0px; }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if "materials" not in st.session_state:
    st.session_state.materials = [
        {"id": "1", "nome": "Nobilitato Bianco 18mm", "tipo": "Pannello", "costo_unita": 18.0, "unita": "mq"},
        {"id": "2", "nome": "Laminato Legno Rovere 18mm", "tipo": "Pannello", "costo_unita": 35.0, "unita": "mq"},
        {"id": "3", "nome": "MDF Laccato Opaco 18mm", "tipo": "Pannello", "costo_unita": 55.0, "unita": "mq"},
        {"id": "4", "nome": "Bordo ABS 1mm", "tipo": "Bordo", "costo_unita": 0.80, "unita": "ml"},
        {"id": "5", "nome": "Cerniera Soft-Close", "tipo": "Ferramenta", "costo_unita": 3.50, "unita": "Pz"},
        {"id": "6", "nome": "Guide Cassetto Ammortizzate", "tipo": "Ferramenta", "costo_unita": 22.00, "unita": "Pz"},
        {"id": "7", "nome": "Piedini Regolabili + Attacchi", "tipo": "Ferramenta", "costo_unita": 4.00, "unita": "Set"}
    ]

if "clients" not in st.session_state:
    st.session_state.clients = [
        {"id": "1", "nome": "Mario Rossi", "azienda": "Rossi Srl", "email": "mario@rossi.it", "telefono": "+39 333 1234567", "indirizzo": "Via Roma 10, Milano"},
        {"id": "2", "nome": "Laura Bianchi", "azienda": "Studio Bianchi", "email": "laura@bianchi.com", "telefono": "+39 340 7654321", "indirizzo": "Corso Italia 45, Torino"}
    ]

if "quotes" not in st.session_state:
    st.session_state.quotes = []

if "current_items" not in st.session_state:
    st.session_state.current_items = []

# Sidebar Navigation
st.sidebar.image("https://img.icons8.com/isometric/100/null/interior-design.png", width=70)
st.sidebar.title("Gestionale Falegnameria")
st.sidebar.caption("Preventivazione su Misura v2.0")

menu = st.sidebar.radio("Navigazione", [
    "📊 Dashboard", 
    "🧮 Calcolatore Modulo (Costo Materiali)", 
    "📝 Nuovo Preventivo", 
    "📁 Archivio Preventivi", 
    "📦 Gestione Materiali & Costi",
    "👥 Anagrafica Clienti"
])

# ------------------- 1. DASHBOARD -------------------
if menu == "📊 Dashboard":
    st.markdown('<div class="main-header">Dashboard Commerciale</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Panoramica dei preventivi e delle lavorazioni</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    totale_preventivi = len(st.session_state.quotes)
    valore_totale = sum(q["totale_ivato"] for q in st.session_state.quotes)
    in_attesa = sum(1 for q in st.session_state.quotes if q["stato"] == "In Inviato/In Attesa")
    confermati = sum(1 for q in st.session_state.quotes if q["stato"] == "Approvato")

    col1.metric("Preventivi Totali", totale_preventivi)
    col2.metric("Valore Totale (€)", f"€ {valore_totale:,.2f}")
    col3.metric("In Attesa", in_attesa)
    col4.metric("Approvati", confermati)

    st.markdown("---")
    st.subheader("Ultimi Preventivi Creati")
    if st.session_state.quotes:
        df_quotes = pd.DataFrame(st.session_state.quotes)[["numero", "data", "cliente_nome", "totale_imponibile", "totale_ivato", "stato"]]
        st.dataframe(df_quotes, use_container_width=True)
    else:
        st.info("Nessun preventivo in archivio. Calcola un modulo e crea un nuovo preventivo.")

# ------------------- 2. CALCOLATORE MODULO DAL COSTO MATERIALI -------------------
elif menu == "🧮 Calcolatore Modulo (Costo Materiali)":
    st.markdown('<div class="main-header">Calcolo Prezzo Modulo da Costo Materiale</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Calcola la distinta base, la superficie dei pannelli, la ferramenta, il ricarico e la manodopera per Basi, Pensili e Colonne</div>', unsafe_allow_html=True)

    col_m1, col_m2 = st.columns([1, 1])

    with col_m1:
        st.subheader("📐 1. Dimensioni & Tipologia Modulo")
        tipo_modulo = st.selectbox("Tipologia Modulo", ["Base Cucina", "Pensile", "Colonna", "Modulo Personalizzato"])
        
        c_dim1, c_dim2, c_dim3 = st.columns(3)
        larghezza_mm = c_dim1.number_input("Larghezza (mm)", min_value=100, max_value=3000, value=600, step=50)
        altezza_mm = c_dim2.number_input("Altezza (mm)", min_value=100, max_value=3000, value=720 if tipo_modulo != "Colonna" else 2040, step=50)
        profondita_mm = c_dim3.number_input("Profondità (mm)", min_value=100, max_value=1200, value=560 if tipo_modulo != "Pensile" else 340, step=20)

        ripiani = st.number_input("Numero Ripiani Interni", min_value=0, max_value=10, value=1 if tipo_modulo == "Base Cucina" else (2 if tipo_modulo == "Pensile" else 4))
        num_ante = st.number_input("Numero Ante", min_value=0, max_value=4, value=1)
        num_cassetti = st.number_input("Numero Cassetti / Cassettoni", min_value=0, max_value=6, value=0)

        # Calcolo sviluppo mq pannelli (Fianchi, Fondo, Coperchio/Catene, Schienale, Ripiani, Ante)
        # Convertiamo mm in m
        L = larghezza_mm / 1000.0
        H = altezza_mm / 1000.0
        P = profondita_mm / 1000.0

        mq_fianchi = 2 * (H * P)
        mq_fondo_coperchio = 2 * (L * P)
        mq_ripiani = ripiani * (L * P)
        mq_schienale = L * H
        mq_ante = num_ante * (L * H)

        st.markdown("---")
        st.subheader("🪵 2. Selezione Materiali")
        
        pannelli_list = [m["nome"] for m in st.session_state.materials if m["tipo"] == "Pannello"]
        ferramenta_list = [m["nome"] for m in st.session_state.materials if m["tipo"] == "Ferramenta"]
        bordo_list = [m["nome"] for m in st.session_state.materials if m["tipo"] == "Bordo"]

        mat_scocca_name = st.selectbox("Materiale Scocca/Struttura", pannelli_list, index=0)
        mat_anta_name = st.selectbox("Materiale Ante/Frontali", pannelli_list, index=1 if len(pannelli_list)>1 else 0)
        mat_bordo_name = st.selectbox("Materiale Bordo ABS", bordo_list, index=0 if bordo_list else None)

        costo_scocca_mq = next(m["costo_unita"] for m in st.session_state.materials if m["nome"] == mat_scocca_name)
        costo_anta_mq = next(m["costo_unita"] for m in st.session_state.materials if m["nome"] == mat_anta_name)
        costo_bordo_ml = next(m["costo_unita"] for m in st.session_state.materials if m["nome"] == mat_bordo_name) if mat_bordo_name else 0.0

    with col_m2:
        st.subheader("⚙️ 3. Ferramenta & Servizi")
        num_cerniere = st.number_input("Numero Cerniere", min_value=0, value=num_ante * 2)
        costo_cerniera = next((m["costo_unita"] for m in st.session_state.materials if "Cerniera" in m["nome"]), 3.50)

        costo_cassetto = next((m["costo_unita"] for m in st.session_state.materials if "Cassetto" in m["nome"]), 22.00)
        
        st.markdown("---")
        st.subheader("⏱️ 4. Manodopera, Sfrido & Ricarico")
        sfrido_perc = st.slider("Sfrido / Sguardo Legno (%)", min_value=0, max_value=30, value=10, help="Percentuale di materiale perso durante il taglio")
        ore_lavoro = st.number_input("Ore Lavorazione / Taglio / Assemblaggio", min_value=0.0, value=1.5 if tipo_modulo != "Colonna" else 2.5, step=0.5)
        costo_orario = st.number_input("Costo Orario Manodopera (€/h)", min_value=0.0, value=35.0, step=5.0)

        ricarico_perc = st.slider("Margine / Ricarico Aziendale (%)", min_value=0, max_value=200, value=50, help="Percentuale di ricarico sul costo totale dei materiali e lavorazione")

    # --- CALCOLO FINALE DISTINTA MATERIALI & COSTI ---
    st.markdown("---")
    st.subheader("📊 Analisi Dettagliata Costi e Prezzo Finale")

    tot_mq_scocca = round((mq_fianchi + mq_fondo_coperchio + mq_ripiani + mq_schienale) * (1 + sfrido_perc/100.0), 2)
    tot_mq_ante = round(mq_ante * (1 + sfrido_perc/100.0), 2)
    tot_ml_bordo = round(((L + H) * 4) * (1 + sfrido_perc/100.0), 2)

    costo_mat_scocca = tot_mq_scocca * costo_scocca_mq
    costo_mat_ante = tot_mq_ante * costo_anta_mq
    costo_mat_bordo = tot_ml_bordo * costo_bordo_ml
    costo_ferramenta = (num_cerniere * costo_cerniera) + (num_cassetti * costo_cassetto)
    costo_manodopera = ore_lavoro * costo_orario

    costo_totale_produzione = costo_mat_scocca + costo_mat_ante + costo_mat_bordo + costo_ferramenta + costo_manodopera
    prezzo_vendita_calcolato = costo_totale_produzione * (1 + ricarico_perc/100.0)

    # Tabella Distinta
    distinta_df = pd.DataFrame([
        {"Componente": "Pannelli Scocca", "Dettaglio": f"{tot_mq_scocca} mq ({mat_scocca_name})", "Costo (€)": f"€ {costo_mat_scocca:.2f}"},
        {"Componente": "Pannelli Ante/Frontali", "Dettaglio": f"{tot_mq_ante} mq ({mat_anta_name})", "Costo (€)": f"€ {costo_mat_ante:.2f}"},
        {"Componente": "Bordo ABS", "Dettaglio": f"{tot_ml_bordo} ml ({mat_bordo_name})", "Costo (€)": f"€ {costo_mat_bordo:.2f}"},
        {"Componente": "Ferramenta (Cerniere/Cassetti)", "Dettaglio": f"{num_cerniere} cerniere, {num_cassetti} cassetti", "Costo (€)": f"€ {costo_ferramenta:.2f}"},
        {"Componente": "Manodopera & Taglio", "Dettaglio": f"{ore_lavoro} ore x €{costo_orario}/h", "Costo (€)": f"€ {costo_manodopera:.2f}"},
    ])

    col_res1, col_res2 = st.columns([2, 1])
    with col_res1:
        st.dataframe(distinta_df, use_container_width=True)

    with col_res2:
        st.metric("Costo Vivo Produzione", f"€ {costo_totale_produzione:.2f}")
        st.metric(f"Prezzo di Vendita (Ricarico {ricarico_perc}%)", f"€ {prezzo_vendita_calcolato:.2f}")

        nome_articolo = f"{tipo_modulo} {larghezza_mm}x{altezza_mm}x{profondita_mm}mm ({mat_anta_name})"
        
        if st.button("➕ Aggiungi al Preventivo Corrente", type="primary", use_container_width=True):
            st.session_state.current_items.append({
                "codice": f"MOD-{larghezza_mm}x{altezza_mm}",
                "descrizione": nome_articolo,
                "quantita": 1.0,
                "unita": "Pz",
                "prezzo_unitario": round(prezzo_vendita_calcolato, 2),
                "sconto": 0.0,
                "totale": round(prezzo_vendita_calcolato, 2)
            })
            st.success(f"Articolo '{nome_articolo}' aggiunto al preventivo con successo!")

# ------------------- 3. NUOVO PREVENTIVO -------------------
elif menu == "📝 Nuovo Preventivo":
    st.markdown('<div class="main-header">Nuovo Preventivo Su Misura</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Gestisci le voci aggiunte dal calcolatore o inserisci ulteriori servizi/moduli</div>', unsafe_allow_html=True)

    with st.expander("👤 Dati Cliente & Intestazione", expanded=True):
        col_c1, col_c2, col_c3 = st.columns([2, 1, 1])
        client_options = {c["nome"]: c for c in st.session_state.clients}
        selected_client_name = col_c1.selectbox("Seleziona Cliente", list(client_options.keys()))
        selected_client = client_options[selected_client_name]
        data_prev = col_c2.date_input("Data Preventivo", date.today())
        validita_giorni = col_c3.number_input("Validità (giorni)", min_value=7, max_value=120, value=30)

    st.subheader("📋 Articoli nel Preventivo")

    if st.session_state.current_items:
        df_current = pd.DataFrame(st.session_state.current_items)
        st.dataframe(df_current, use_container_width=True)

        if st.button("🗑️ Svuota Voci"):
            st.session_state.current_items = []
            st.rerun()

        imponibile = sum(item["totale"] for item in st.session_state.current_items)
        aliquota_iva = st.selectbox("Aliquota IVA (%)", [22, 10, 4], index=0)
        iva = imponibile * (aliquota_iva / 100)
        totale_ivato = imponibile + iva

        col_tot1, col_tot2, col_tot3 = st.columns(3)
        col_tot1.metric("Totale Imponibile", f"€ {imponibile:,.2f}")
        col_tot2.metric(f"IVA ({aliquota_iva}%)", f"€ {iva:,.2f}")
        col_tot3.metric("TOTALE PREVENTIVO", f"€ {totale_ivato:,.2f}")

        note = st.text_area("Note Commerciali & Condizioni di Pagamento", "Pagamento: 30% all'ordine, 70% a fine montaggio. Tempi di consegna: 30 giorni lavorativi.")

        if st.button("💾 Salva Preventivo", type="primary", use_container_width=True):
            num_prev = f"PREV-2026-{len(st.session_state.quotes) + 1:03d}"
            new_quote = {
                "id": str(uuid.uuid4()),
                "numero": num_prev,
                "data": str(data_prev),
                "cliente_nome": selected_client["nome"],
                "cliente_azienda": selected_client["azienda"],
                "items": st.session_state.current_items,
                "totale_imponibile": imponibile,
                "iva": iva,
                "totale_ivato": totale_ivato,
                "note": note,
                "stato": "In Inviato/In Attesa"
            }
            st.session_state.quotes.append(new_quote)
            st.session_state.current_items = []
            st.success(f"Preventivo {num_prev} salvato con successo!")
    else:
        st.info("Nessun articolo presente nel preventivo. Vai al 'Calcolatore Modulo' per aggiungere articoli calcolati dal costo del materiale.")

# ------------------- 4. ARCHIVIO PREVENTIVI -------------------
elif menu == "📁 Archivio Preventivi":
    st.markdown('<div class="main-header">Archivio Preventivi</div>', unsafe_allow_html=True)
    if not st.session_state.quotes:
        st.info("Nessun preventivo salvato.")
    else:
        for q in st.session_state.quotes:
            with st.expander(f"📌 {q['numero']} - {q['cliente_azienda']} ({q['cliente_nome']}) | € {q['totale_ivato']:.2f} | Stato: {q['stato']}"):
                col_q1, col_q2 = st.columns([2, 1])
                with col_q1:
                    st.write(f"**Data:** {q['data']}")
                    st.write(f"**Note:** {q['note']}")
                    st.dataframe(pd.DataFrame(q['items']), use_container_width=True)
                with col_q2:
                    st.metric("Totale Imponibile", f"€ {q['totale_imponibile']:.2f}")
                    st.metric("Totale Ivato", f"€ {q['totale_ivato']:.2f}")
                    nuovo_stato = st.selectbox("Aggiorna Stato", ["In Inviato/In Attesa", "Approvato", "Rifiutato"], index=["In Inviato/In Attesa", "Approvato", "Rifiutato"].index(q['stato']), key=f"status_{q['id']}")
                    q['stato'] = nuovo_stato

# ------------------- 5. GESTIONE MATERIALI & COSTI -------------------
elif menu == "📦 Gestione Materiali & Costi":
    st.markdown('<div class="main-header">Gestione Listino Materiali & Costi Unitarii</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Definisci i prezzi al mq dei pannelli, al metro lineare dei bordi e della ferramenta</div>', unsafe_allow_html=True)

    st.dataframe(pd.DataFrame(st.session_state.materials), use_container_width=True)

    with st.form("add_material_form"):
        st.subheader("➕ Aggiungi Nuovo Materiale al Listino")
        c_m1, c_m2, c_m3, c_m4 = st.columns(4)
        nome_m = c_m1.text_input("Nome Materiale")
        tipo_m = c_m2.selectbox("Tipo Materiale", ["Pannello", "Bordo", "Ferramenta"])
        costo_m = c_m3.number_input("Costo Unitario (€)", min_value=0.0, value=10.0, step=1.0)
        unita_m = c_m4.selectbox("Unità di Misura", ["mq", "ml", "Pz", "Set"])

        if st.form_submit_button("Salva Materiale"):
            st.session_state.materials.append({
                "id": str(uuid.uuid4()), "nome": nome_m, "tipo": tipo_m,
                "costo_unita": costo_m, "unita": unita_m
            })
            st.success(f"Materiale {nome_m} aggiunto!")
            st.rerun()

# ------------------- 6. ANAGRAFICA CLIENTE -------------------
elif menu == "👥 Anagrafica Clienti":
    st.markdown('<div class="main-header">Anagrafica Clienti</div>', unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(st.session_state.clients), use_container_width=True)
