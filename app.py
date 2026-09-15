import pandas as pd
from supabase import create_client
import streamlit as st
from amministrazione import render_amministrazione
from engine import calcola_modulo_parametrico
from exports import genera_excel_preventivo, genera_pdf_preventivo

st.set_page_config(page_title="Preventivatore Arredi Modulari", layout="wide")

URL = st.secrets.get("SUPABASE_URL", "https://tuo-id.supabase.co")
KEY = st.secrets.get("SUPABASE_KEY", "tua-chiave")
supabase = create_client(URL, KEY)

st.sidebar.title("📍 Navigazione")
modalita = st.sidebar.radio("Sezione:", ["Preventivatore", "Amministrazione"])

if modalita == "Amministrazione":
  render_amministrazione(supabase)
else:
  # ==========================================
  # SELEZIONE PROGETTO E VARIANTE IN SIDEBAR
  # ==========================================
  st.sidebar.divider()
  st.sidebar.header("📁 Progetti & Varianti")

  res_progetti = (
      supabase.table("progetti")
      .select("*")
      .order("created_at", desc=True)
      .execute()
  )
  lista_progetti = res_progetti.data

  if not lista_progetti:
    st.warning("Crea un progetto in Amministrazione o nella Sidebar per iniziare.")
    st.stop()

  opzioni_p = {p["nome_cliente"]: p for p in lista_progetti}
  proj_sel_label = st.sidebar.selectbox("📂 Progetto:", list(opzioni_p.keys()))
  progetto_attuale = opzioni_p[proj_sel_label]
  progetto_id = progetto_attuale["id"]

  # Gestione Varianti del Progetto
  res_var = (
      supabase.table("varianti_progetto")
      .select("*")
      .eq("progetto_id", progetto_id)
      .execute()
  )
  varianti = res_var.data

  # Se non esistono varianti, crea quella di default
  if not varianti:
    v_def = (
        supabase.table("varianti_progetto")
        .insert({
            "progetto_id": progetto_id,
            "nome_variante": "Variante Base",
            "is_principale": True,
        })
        .execute()
    )
    varianti = v_def.data

  opzioni_v = {v["nome_variante"]: v for v in varianti}
  var_sel_label = st.sidebar.selectbox(
      "🔀 Variante Attiva:", list(opzioni_v.keys())
  )
  variante_attuale = opzioni_v[var_sel_label]
  variante_id = variante_attuale["id"]

  # Form Nuova Variante
  with st.sidebar.expander("➕ Nuova Variante Finiture"):
    nome_nuova_var = st.text_input("Nome Variante (es. Laccato Premium)")
    if st.button("Crea Variante"):
      if nome_nuova_var:
        supabase.table("varianti_progetto").insert({
            "progetto_id": progetto_id,
            "nome_variante": nome_nuova_var,
        }).execute()
        st.success("Variante creata!")
        st.rerun()

  # ==========================================
  # GESTIONE AMBIENTI
  # ==========================================
  st.title(
      f"📐 {progetto_attuale['nome_cliente']} — Variante:"
      f" {variante_attuale['nome_variante']}"
  )

  res_amb = (
      supabase.table("ambienti")
      .select("*")
      .eq("progetto_id", progetto_id)
      .execute()
  )
  ambienti = res_amb.data

  col_a1, col_a2 = st.columns([3, 1])
  with col_a1:
    st.subheader("🏠 Ambienti del Progetto")
  with col_a2:
    with st.popover("➕ Aggiungi Ambiente"):
      nuovo_amb_nome = st.text_input("Nome Ambiente (es. Cucina)")
      if st.button("Salva Ambiente"):
        if nuovo_amb_nome:
          supabase.table("ambienti").insert({
              "progetto_id": progetto_id,
              "nome_ambiente": nuovo_amb_nome,
          }).execute()
          st.rerun()

  if not ambienti:
    st.info("Crea almeno un ambiente (es. 'Cucina', 'Soggiorno') per inserire i moduli.")
    st.stop()

  # ==========================================
  # INSERIMENTO MODULO (Legato all'Ambiente e Condiviso)
  # ==========================================
  with st.expander("➕ Aggiungi Modulo Geometrico Base", expanded=False):
    amb_m = st.selectbox(
        "Seleziona Ambiente Destinazione",
        options=[a["id"] for a in ambienti],
        format_func=lambda x: [
            a["nome_ambiente"] for a in ambienti if a["id"] == x
        ][0],
    )
    c1, c2, c3 = st.columns(3)
    categoria = c1.selectbox(
        "Categoria Modulo",
        ["basi", "pensili", "colonne", "mensole", "zoccoli", "accessori"],
    )
    nome_mod = c2.text_input("Nome Modulo", "Base 2 Ante")
    apertura = c3.selectbox("Tipo Apertura", ["ante", "cassetti", "vasistas"])

    d1, d2, d3 = st.columns(3)
    L = d1.number_input("Larghezza (mm)", value=600, step=10)
    H = d2.number_input("Altezza (mm)", value=720, step=10)
    P = d3.number_input("Profondità (mm)", value=560, step=10)

    # Carica Materiali per assegnare la finitura in questa variante
    mat_db = supabase.table("finiture_materiali").select("*").execute().data
    finiture_unil = list(set([m["nome_finitura"] for m in mat_db]))
    finitura_sel = st.selectbox("Finitura per la Variante Attiva", finiture_unil)

    if st.button("💾 Salva Modulo Base (Valido per TUTTE le Varianti)"):
      # 1. Salva la geometria del modulo base
      mod_base = (
          supabase.table("moduli_base")
          .insert({
              "ambiente_id": amb_m,
              "categoria": categoria,
              "nome_modulo": nome_mod,
              "larghezza_mm": L,
              "altezza_mm": H,
              "profondita_mm": P,
              "tipo_apertura": apertura,
          })
          .execute()
          .data[0]
      )

      # 2. Collega la finitura scelta alla variante corrente
      fin_obj = next(
          m for m in mat_db if m["nome_finitura"] == finitura_sel
      )  # Prende il primo spessore valido
      supabase.table("configurazione_modulo_variante").insert({
          "variante_id": variante_id,
          "modulo_base_id": mod_base["id"],
          "finitura_id": fin_obj["id"],
      }).execute()

      st.success("Modulo salvato ed integrato nel progetto!")
      st.rerun()

  # ==========================================
  # VISUALIZZAZIONE E CALCOLO PER AMBIENTI
  # ==========================================
  st.divider()

  # Recupera tutti i moduli base del progetto attraversando gli ambienti
  res_mod_base = (
      supabase.table("moduli_base")
      .select("*, ambienti!inner(progetto_id, nome_ambiente)")
      .eq("ambienti.progetto_id", progetto_id)
      .execute()
  )
  moduli_totali = res_mod_base.data

  # Recupera finiture assegnate alla variante corrente
  res_cfg = (
      supabase.table("configurazione_modulo_variante")
      .select("*, finiture_materiali(*)")
      .eq("variante_id", variante_id)
      .execute()
  )
  cfg_map = {c["modulo_base_id"]: c["finiture_materiali"] for c in res_cfg.data}

  soglie_db = supabase.table("soglie_cerniere").select("*").execute().data
  acc_db = supabase.table("accessori_ferramenta").select("*").execute().data
  prezzi_acc_map = {a["codice"]: float(a["costo_unitario"]) for a in acc_db}

  righe_preventivo = []

  for m in moduli_totali:
    m_id = m["id"]
    # Se la variante non ha una finitura specifica per questo modulo, usa una di default
    fin_info = cfg_map.get(m_id)
    nome_fin = (
        fin_info["nome_finitura"] if fin_info else "Da Configurare (Standard)"
    )

    # Mappa prezzi materiale
    prezzi_mat_map = (
        {
            mat["spessore_mm"]: float(mat["costo_mq"])
            for mat in mat_db
            if mat["nome_finitura"] == nome_fin
        }
        if fin_info
        else {18: 25.0, 8: 15.0, 22: 30.0}
    )

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
        soglie_cerniere=soglie_db,
    )

    righe_preventivo.append({
        "Modulo ID": m_id,
        "Ambiente": m["ambienti"]["nome_ambiente"],
        "Categoria": m["categoria"],
        "Modulo": m["nome_modulo"],
        "Dimensioni": f"{m['larghezza_mm']}x{m['altezza_mm']}x{m['profondita_mm']}",
        "Finitura Variante": nome_fin,
        "Costo Ind. (€)": costo_ind,
    })

  if righe_preventivo:
    df_prev = pd.DataFrame(righe_preventivo)

    # Mostra i moduli divisi per Ambiente
    for amb_nome in df_prev["Ambiente"].unique():
      st.subheader(f"📍 Ambiente: {amb_nome}")
      df_amb = df_prev[df_prev["Ambiente"] == amb_nome]
      st.dataframe(
          df_amb[
              [
                  "Categoria",
                  "Modulo",
                  "Dimensioni",
                  "Finitura Variante",
                  "Costo Ind. (€)",
              ]
          ],
          use_container_width=True,
      )

    # Rimuovi modulo (la rimozione cancella il modulo dall'Ambiente e da TUTTE le varianti)
    with st.expander("🗑️ Elimina Modulo dall'Ambiente"):
      id_del = st.selectbox(
          "Seleziona modulo da eliminare definitivamente:",
          options=df_prev["Modulo ID"].tolist(),
          format_func=lambda x: (
              f"{df_prev[df_prev['Modulo ID'] == x]['Modulo'].values[0]}"
              f" ({df_prev[df_prev['Modulo ID'] == x]['Ambiente'].values[0]})"
          ),
      )
      if st.button("Elimina Modulo"):
        supabase.table("moduli_base").delete().eq("id", id_del).execute()
        st.success("Modulo eliminato dall'Ambiente e da tutte le varianti!")
        st.rerun()

    # Totali della Variante Selezionata
    ricarico_p = float(variante_attuale.get("ricarico_progetto_perc", 120.0))
    sconto_f = float(variante_attuale.get("sconto_finale_perc", 0.0))
    mont_p = float(variante_attuale.get("ricarico_montaggio_perc", 10.0))

    tot_costo_ind = df_prev["Costo Ind. (€)"].sum()
    tot_ricarici = tot_costo_ind * (1 + (ricarico_p / 100))
    tot_scontato = tot_ricarici * (1 - (sconto_f / 100))
    tot_finale = tot_scontato * (1 + (mont_p / 100))

    st.markdown("---")
    st.subheader(
        f"📊 Totali Economici — {variante_attuale['nome_variante']}"
    )
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Costo Industriale Totale", f"€ {tot_costo_ind:.2f}")
    r2.metric(f"Listino (Ricarico {ricarico_p}%)", f"€ {tot_ricarici:.2f}")
    r3.metric(f"Scontato ({sconto_f}%)", f"€ {tot_scontato:.2f}")
    r4.metric(
        f"PREZZO FINALE (+{mont_p}% Mont.)",
        f"€ {tot_finale:.2f}",
    )
  else:
    st.info("Nessun modulo ancora inserito negli ambienti di questo progetto.")
