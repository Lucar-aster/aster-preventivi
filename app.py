import pandas as pd
from supabase import create_client
import streamlit as st
from amministrazione import render_amministrazione
from engine import calcola_modulo_parametrico

st.set_page_config(page_title="Preventivatore Arredi", layout="wide")

# Connessione Supabase
URL = st.secrets.get("SUPABASE_URL", "https://tuo-id.supabase.co")
KEY = st.secrets.get("SUPABASE_KEY", "tua-chiave")
supabase = create_client(URL, KEY)

# Navigazione Sezioni
st.sidebar.title("📍 Navigazione")
modalita = st.sidebar.radio(
    "Seleziona Sezione:", ["Preventivatore", "Amministrazione"]
)

if modalita == "Amministrazione":
  render_amministrazione(supabase)
else:
  # ==========================================
  # GESTIONE MULTI-PROGETTO NELLA SIDEBAR
  # ==========================================
  st.sidebar.divider()
  st.sidebar.header("📁 Gestione Progetti")

  # Recupera lista progetti
  res_progetti = (
      supabase.table("progetti")
      .select("*")
      .order("created_at", desc=True)
      .execute()
  )
  lista_progetti = res_progetti.data

  # Form creazione nuovo progetto
  with st.sidebar.expander("➕ Crea Nuovo Progetto"):
    nuovo_cliente = st.text_input("Nome Cliente / Residenza")
    nuovo_indirizzo = st.text_input("Indirizzo / Cantiere")
    if st.button("Crea Progetto"):
      if nuovo_cliente:
        supabase.table("progetti").insert({
            "nome_cliente": nuovo_cliente,
            "indirizzo": nuovo_indirizzo,
            "ricarico_progetto_perc": 120.0,
            "sconto_finale_perc": 0.0,
            "ricarico_montaggio_perc": 10.0,
        }).execute()
        st.success(f"Progetto '{nuovo_cliente}' creato!")
        st.rerun()

  # Selezione Progetto Attivo
  if lista_progetti:
    opzioni_progetti = {
        f"{p['nome_cliente']} ({p['indirizzo'] or 'N/D'})": p
        for p in lista_progetti
    }
    progetto_selezionato_label = st.sidebar.selectbox(
        "📂 Seleziona Progetto Attivo:", list(opzioni_progetti.keys())
    )
    progetto_attuale = opzioni_progetti[progetto_selezionato_label]
    progetto_id = progetto_attuale["id"]
  else:
    st.warning("Crea un progetto per iniziare a preventivare.")
    st.stop()

  # ==========================================
  # SCHERMATA DEL PREVENTIVO ATTIVO
  # ==========================================
  st.title(f"📐 Preventivo: {progetto_attuale['nome_cliente']}")

  # 1. PARAMETRI ECONOMICI DEL PROGETTO (INSERIMENTO MANUALE)
  with st.expander(
      "📋 Parametri Economici e Ricarichi Progetto", expanded=True
  ):
    st.info(
        "I valori inseriti qui sotto vengono applicati a tutti i moduli dell'intero"
        " progetto."
    )
    col_c1, col_c2, col_c3 = st.columns(3)

    # st.number_input al posto di slider per inserimento manuale esatto
    ricarico_proj = col_c1.number_input(
        "Ricarico Progetto (%)",
        value=float(progetto_attuale.get("ricarico_progetto_perc", 120.0)),
        step=1.0,
        format="%.2f",
    )
    sconto_fin = col_c2.number_input(
        "Sconto Finale (%)",
        value=float(progetto_attuale.get("sconto_finale_perc", 0.0)),
        step=1.0,
        format="%.2f",
    )
    ricarico_mont = col_c3.number_input(
        "Montaggio & Trasporto (%)",
        value=float(progetto_attuale.get("ricarico_montaggio_perc", 10.0)),
        step=1.0,
        format="%.2f",
    )

    if st.button("💾 Salva Parametri Economici Progetto"):
      supabase.table("progetti").update({
          "ricarico_progetto_perc": ricarico_proj,
          "sconto_finale_perc": sconto_fin,
          "ricarico_montaggio_perc": ricarico_mont,
      }).eq("id", progetto_id).execute()
      st.success("Parametri economici salvati con successo nel DB!")
      st.rerun()

  st.divider()

  # 2. INSERIMENTO MODULO (SENZA RICARICO SINGOLO)
  st.subheader("➕ Aggiungi Modulo")
  c1, c2, c3 = st.columns(3)

  ambiente = c1.selectbox(
      "Ambiente", ["Cucina", "Zona Giorno", "Bagno", "Zona Notte"]
  )
  categoria = c2.selectbox(
      "Categoria Modulo",
      ["basi", "pensili", "colonne", "mensole", "zoccoli", "accessori"],
  )
  nome_mod = c3.text_input("Nome Modulo", "Base 2 Ante")

  # Caricamento dati da Supabase
  mat_db = supabase.table("finiture_materiali").select("*").execute().data
  finiture_unil = list(set([m["nome_finitura"] for m in mat_db]))
  soglie_db = supabase.table("soglie_cerniere").select("*").execute().data
  acc_db = supabase.table("accessori_ferramenta").select("*").execute().data

  col_d1, col_d2, col_d3, col_d4 = st.columns(4)
  L = col_d1.number_input("Larghezza (mm)", value=600, step=10)
  H = col_d2.number_input("Altezza (mm)", value=720, step=10)
  P = col_d3.number_input("Profondità (mm)", value=560, step=10)
  finitura_sel = col_d4.selectbox("Finitura Materiale", finiture_unil)

  # Opzioni per categoria
  apertura = "ante"
  n_ante, n_cass, sp_mensola = 1, 0, 30
  eldom_inc, vani_eldom = False, []

  if categoria in ["basi", "pensili", "colonne"]:
    ca1, ca2, ca3 = st.columns(3)
    apertura = ca1.selectbox("Tipo Apertura", ["ante", "cassetti", "vasistas"])
    if apertura == "ante":
      n_ante = ca2.number_input("N° Ante", value=1, min_value=1, step=1)
      if categoria == "colonne":
        eldom_inc = ca3.checkbox("Colonna Frigo (Incassato)", value=False)
        vano = st.number_input(
            "Vano Eldom (mm) - 0 se nessuno", value=0, step=10
        )
        if vano > 0:
          vani_eldom = [vano]
    elif apertura == "cassetti":
      n_cass = ca2.number_input("N° Cassetti", value=2, min_value=1, step=1)

  elif categoria == "mensole":
    sp_mensola = st.selectbox(
        "Spessore Mensola (mm)", [8, 12, 18, 22, 25, 30, 40, 50, 60]
    )

  prezzi_mat_map = {
      m["spessore_mm"]: float(m["costo_mq"])
      for m in mat_db
      if m["nome_finitura"] == finitura_sel
  }
  prezzi_acc_map = {a["codice"]: float(a["costo_unitario"]) for a in acc_db}

  # Calcolo Costo Industriale Modulo
  costo_ind = calcola_modulo_parametrico(
      categoria=categoria,
      L_mm=L,
      H_mm=H,
      P_mm=P,
      spessore_mensola_mm=sp_mensola,
      tipo_apertura=apertura,
      num_ante=n_ante,
      num_cassetti=n_cass,
      vani_eldom=vani_eldom,
      eldom_incassato=eldom_inc,
      prezzi_mat=prezzi_mat_map,
      prezzi_acc=prezzi_acc_map,
      soglie_cerniere=soglie_db,
  )

  # Prezzo di vendita stimato per singolo modulo in base al ricarico del progetto
  prezzo_modulo_stimato = costo_ind * (1 + (ricarico_proj / 100))

  st.info(
      f"🛠️ **Costo Industriale (Costo Materiali):** € {costo_ind:.2f}  |  🏷️"
      f" **Prezzo Modulo Ricaricato ({ricarico_proj}%):** €"
      f" {prezzo_modulo_stimato:.2f}"
  )

  if st.button("➕ Salva Modulo nel Progetto"):
    modulo_db = {
        "progetto_id": progetto_id,
        "ambiente": ambiente,
        "categoria": categoria,
        "nome_modulo": nome_mod,
        "larghezza_mm": L,
        "altezza_mm": H,
        "profondita_mm": P,
        "costo_industriale": costo_ind,
        "prezzo_vendita": costo_ind,  # Salviamo il costo base nel DB
    }
    supabase.table("moduli_preventivo").insert(modulo_db).execute()
    st.success("Modulo aggiunto al progetto!")
    st.rerun()

  # 3. RIEPILOGO E TOTALI CALCOLATI CON RICARICO PROGETTO
  st.divider()
  st.subheader(f"📊 Moduli e Totali per {progetto_attuale['nome_cliente']}")

  res_moduli = (
      supabase.table("moduli_preventivo")
      .select("*")
      .eq("progetto_id", progetto_id)
      .execute()
  )
  moduli_salvati = res_moduli.data

  if moduli_salvati:
    df_moduli = pd.DataFrame(moduli_salvati)

    # Calcoliamo il prezzo ricaricato al volo per ogni riga della tabella usando il ricarico progetto
    df_moduli["Prezzo Ricaricato €"] = df_moduli["costo_industriale"].apply(
        lambda c: float(c) * (1 + (ricarico_proj / 100))
    )

    df_mostra = df_moduli[[
        "ambiente",
        "categoria",
        "nome_modulo",
        "larghezza_mm",
        "altezza_mm",
        "profondita_mm",
        "costo_industriale",
        "Prezzo Ricaricato €",
    ]]
    st.dataframe(df_mostra, use_container_width=True)

    # Rimuovi modulo
    with st.expander("🗑️ Rimuovi Modulo dal Preventivo"):
      id_da_elim = st.selectbox(
          "Seleziona modulo da eliminare:",
          options=df_moduli["id"].tolist(),
          format_func=lambda x: (
              f"{df_moduli[df_moduli['id'] == x]['nome_modulo'].values[0]}"
              f" ({df_moduli[df_moduli['id'] == x]['ambiente'].values[0]})"
          ),
      )
      if st.button("Elimina Modulo"):
        supabase.table("moduli_preventivo").delete().eq(
            "id", id_da_elim
        ).execute()
        st.success("Modulo rimosso!")
        st.rerun()

    # --- CALCOLO MATEMATICO DEL TOTALE PROGETTO ---
    tot_costo_industriale = df_moduli["costo_industriale"].sum()
    tot_lordo_ricaricato = tot_costo_industriale * (1 + (ricarico_proj / 100))
    tot_scontato = tot_lordo_ricaricato * (1 - (sconto_fin / 100))
    tot_finale_residenza = tot_scontato * (1 + (ricarico_mont / 100))

    st.markdown("---")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric(
        "Tot. Costo Industriale",
        f"€ {tot_costo_industriale:.2f}",
        help="Costo totale puro dei materiali + accessori",
    )
    r2.metric(
        f"Tot. Listino (Ricarico {ricarico_proj}%)",
        f"€ {tot_lordo_ricaricato:.2f}",
    )
    r3.metric(f"Tot. Scontato ({sconto_fin}%)", f"€ {tot_scontato:.2f}")
    r4.metric(
        f"PREZZO FINALE (+{ricarico_mont}% Mont.)",
        f"€ {tot_finale_residenza:.2f}",
    )

  else:
    st.info("Nessun modulo presente nel progetto.")
