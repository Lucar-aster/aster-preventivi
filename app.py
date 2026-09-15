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
  # 1. GESTIONE PROGETTI / CLIENTE IN SIDEBAR
  # ==========================================
  st.sidebar.divider()
  st.sidebar.header("📁 Progetti & Cliente")

  # Carica tutti i progetti dal DB
  res_progetti = (
      supabase.table("progetti")
      .select("*")
      .order("created_at", desc=True)
      .execute()
  )
  lista_progetti = res_progetti.data

  # Form Creazione Nuovo Cliente / Progetto
  with st.sidebar.expander("➕ Nuovo Progetto / Cliente"):
    nuovo_cliente = st.text_input("Nome Cliente / Ragione Soc.")
    nuovo_indirizzo = st.text_input("Indirizzo / Cantiere")
    if st.button("Crea Progetto"):
      if nuovo_cliente:
        # Inserimento nuovo progetto
        p_created = (
            supabase.table("progetti")
            .insert({
                "nome_cliente": nuovo_cliente,
                "indirizzo": nuovo_indirizzo,
            })
            .execute()
            .data[0]
        )

        # Crea automaticamente la prima Variante Base per il nuovo progetto
        supabase.table("varianti_progetto").insert({
            "progetto_id": p_created["id"],
            "nome_variante": "Variante Base",
            "ricarico_progetto_perc": 120.0,
            "sconto_finale_perc": 0.0,
            "ricarico_montaggio_perc": 10.0,
            "is_principale": True,
        }).execute()

        st.success(f"Progetto per '{nuovo_cliente}' creato!")
        st.rerun()

  if not lista_progetti:
    st.warning("Nessun progetto presente. Crea il primo cliente dalla sidebar.")
    st.stop()

  # Menu di Selezione Progetto Attivo
  opzioni_p = {
      f"{p['nome_cliente']} ({p.get('indirizzo') or 'N/D'})": p
      for p in lista_progetti
  }
  proj_sel_label = st.sidebar.selectbox("📂 Seleziona Progetto:", list(opzioni_p.keys()))
  progetto_attuale = opzioni_p[proj_sel_label]
  progetto_id = progetto_attuale["id"]

  # ==========================================
  # 2. GESTIONE VARIANTI DEL PROGETTO
  # ==========================================
  st.sidebar.divider()
  st.sidebar.header("🔀 Varianti Finitura")

  res_var = (
      supabase.table("varianti_progetto")
      .select("*")
      .eq("progetto_id", progetto_id)
      .execute()
  )
  varianti = res_var.data

  opzioni_v = {v["nome_variante"]: v for v in varianti}
  var_sel_label = st.sidebar.selectbox("Variante Attiva:", list(opzioni_v.keys()))
  variante_attuale = opzioni_v[var_sel_label]
  variante_id = variante_attuale["id"]

  # Form Creazione Nuova Variante
  with st.sidebar.expander("➕ Nuova Variante Finiture"):
    nome_nuova_var = st.text_input("Nome Variante (es. Laccato Premium)")
    if st.button("Salva Nuova Variante"):
      if nome_nuova_var:
        supabase.table("varianti_progetto").insert({
            "progetto_id": progetto_id,
            "nome_variante": nome_nuova_var,
            "ricarico_progetto_perc": variante_attuale.get("ricarico_progetto_perc", 120.0),
            "sconto_finale_perc": variante_attuale.get("sconto_finale_perc", 0.0),
            "ricarico_montaggio_perc": variante_attuale.get("ricarico_montaggio_perc", 10.0),
        }).execute()
        st.success("Variante aggiunta!")
        st.rerun()

  # ==========================================
  # SCHERMATA PRINCIPALE - SCHEDA CLIENTE E PARAMETRI
  # ==========================================
  st.title(f"📐 Preventivo: {progetto_attuale['nome_cliente']}")

  # Modifica Dati Anagrafici Cliente e Parametri Economici della Variante
  with st.expander("👤 Scheda Cliente e Parametri Economici Variante", expanded=False):
    col_cli1, col_cli2 = st.columns(2)
    cliente_nome_mod = col_cli1.text_input("Nome Cliente", value=progetto_attuale["nome_cliente"])
    cliente_ind_mod = col_cli2.text_input("Indirizzo / Cantiere", value=progetto_attuale.get("indirizzo") or "")

    st.markdown("---")
    st.write(f"**Parametri Economici per la variante: `{variante_attuale['nome_variante']}`**")
    col_par1, col_par2, col_par3 = st.columns(3)

    ricarico_p = col_par1.number_input(
        "Ricarico Progetto (%)",
        value=float(variante_attuale.get("ricarico_progetto_perc", 120.0)),
        step=1.0,
        format="%.2f",
    )
    sconto_f = col_par2.number_input(
        "Sconto Finale (%)",
        value=float(variante_attuale.get("sconto_finale_perc", 0.0)),
        step=1.0,
        format="%.2f",
    )
    mont_p = col_par3.number_input(
        "Montaggio & Trasporto (%)",
        value=float(variante_attuale.get("ricarico_montaggio_perc", 10.0)),
        step=1.0,
        format="%.2f",
    )

    if st.button("💾 Salva Dati Cliente e Parametri Economici"):
      # Aggiorna Dati Anagrafici Progetto
      supabase.table("progetti").update({
          "nome_cliente": cliente_nome_mod,
          "indirizzo": cliente_ind_mod,
      }).eq("id", progetto_id).execute()

      # Aggiorna Parametri Economici Variante Attiva
      supabase.table("varianti_progetto").update({
          "ricarico_progetto_perc": ricarico_p,
          "sconto_finale_perc": sconto_f,
          "ricarico_montaggio_perc": mont_p,
      }).eq("id", variante_id).execute()

      st.success("Dati aggiornati correttamente!")
      st.rerun()

  st.divider()

  # ==========================================
  # 3. GESTIONE AMBIENTI DEL PROGETTO
  # ==========================================
  res_amb = (
      supabase.table("ambienti")
      .select("*")
      .eq("progetto_id", progetto_id)
      .execute()
  )
  ambienti = res_amb.data

  col_a1, col_a2 = st.columns([3, 1])
  with col_a1:
    st.subheader(f"🏠 Ambienti del Progetto ({len(ambienti)})")
  with col_a2:
    with st.popover("➕ Crea Nuovo Ambiente"):
      nuovo_amb_nome = st.text_input("Nome Ambiente (es. Cucina, Bagno)")
      if st.button("Salva Ambiente"):
        if nuovo_amb_nome:
          supabase.table("ambienti").insert({
              "progetto_id": progetto_id,
              "nome_ambiente": nuovo_amb_nome,
          }).execute()
          st.rerun()

  if not ambienti:
    st.info("Nessun ambiente inserito. Crea il primo ambiente (es. 'Cucina') per poter inserire i moduli.")
    st.stop()

  # ==========================================
  # 4. INSERIMENTO MODULO BASE (Sull'Ambiente)
  # ==========================================
  with st.expander("➕ Inserisci Modulo Geometrico Base nell'Ambiente", expanded=False):
    amb_m = st.selectbox(
        "Seleziona Ambiente Destinazione",
        options=[a["id"] for a in ambienti],
        format_func=lambda x: [a["nome_ambiente"] for a in ambienti if a["id"] == x][0],
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

    # Carica Finiture per la variante corrente
    mat_db = supabase.table("finiture_materiali").select("*").execute().data
    finiture_unil = list(set([m["nome_finitura"] for m in mat_db]))
    finitura_sel = st.selectbox(f"Finitura per la variante '{variante_attuale['nome_variante']}'", finiture_unil)

    if st.button("💾 Salva Modulo (Disponibile su TUTTE le Varianti)"):
      # 1. Inserisce il modulo base legato all'ambiente
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

      # 2. Assegna la finitura scelta per la variante attiva
      fin_obj = next(m for m in mat_db if m["nome_finitura"] == finitura_sel)
      supabase.table("configurazione_modulo_variante").insert({
          "variante_id": variante_id,
          "modulo_base_id": mod_base["id"],
          "finitura_id": fin_obj["id"],
      }).execute()

      st.success("Modulo salvato nell'Ambiente!")
      st.rerun()

  # ==========================================
  # 5. VISUALIZZAZIONE E CALCOLO PREVENTIVO
  # ==========================================
  st.divider()

  # Recupera tutti i moduli base del progetto
  res_mod_base = (
      supabase.table("moduli_base")
      .select("*, ambienti!inner(progetto_id, nome_ambiente)")
      .eq("ambienti.progetto_id", progetto_id)
      .execute()
  )
  moduli_totali = res_mod_base.data

  # Recupera finiture assegnate alla variante attiva
  res_cfg = (
      supabase.table("configurazione_modulo_variante")
      .select("*, finiture_materiali(*)")
      .eq("variante_id", variante_id)
      .execute()
  )
  cfg_map = {c["modulo_base_id"]: c["finiture_materiali"] for c in res_cfg.data if c.get("finiture_materiali")}

  soglie_db = supabase.table("soglie_cerniere").select("*").execute().data
  acc_db = supabase.table("accessori_ferramenta").select("*").execute().data
  prezzi_acc_map = {a["codice"]: float(a["costo_unitario"]) for a in acc_db}

  righe_preventivo = []

  for m in moduli_totali:
    m_id = m["id"]
    fin_info = cfg_map.get(m_id)
    nome_fin = fin_info["nome_finitura"] if fin_info else "Laminato Standard"

    prezzi_mat_map = {
        mat["spessore_mm"]: float(mat["costo_mq"])
        for mat in mat_db
        if mat["nome_finitura"] == nome_fin
    }

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

    prezzo_ricaricato = costo_ind * (1 + (ricarico_p / 100))

    righe_preventivo.append({
        "Modulo ID": m_id,
        "Ambiente": m["ambienti"]["nome_ambiente"],
        "Categoria": m["categoria"],
        "Modulo": m["nome_modulo"],
        "larghezza_mm": m["larghezza_mm"],
        "altezza_mm": m["altezza_mm"],
        "profondita_mm": m["profondita_mm"],
        "Dimensioni": f"{m['larghezza_mm']}x{m['altezza_mm']}x{m['profondita_mm']}",
        "Finitura Variante": nome_fin,
        "costo_industriale": costo_ind,
        "Prezzo Ricaricato (€)": prezzo_ricaricato,
    })

  if righe_preventivo:
    df_prev = pd.DataFrame(righe_preventivo)

    # Tabella Moduli divisa per Ambiente
    for amb_nome in df_prev["Ambiente"].unique():
      st.subheader(f"📍 Ambiente: {amb_nome}")
      df_amb = df_prev[df_prev["Ambiente"] == amb_nome]
      st.dataframe(
          df_amb[[
              "Categoria",
              "Modulo",
              "Dimensioni",
              "Finitura Variante",
              "costo_industriale",
              "Prezzo Ricaricato (€)",
          ]],
          use_container_width=True,
      )

    # Elimina modulo
    with st.expander("🗑️ Rimuovi Modulo dall'Ambiente"):
      id_del = st.selectbox(
          "Seleziona modulo da eliminare:",
          options=df_prev["Modulo ID"].tolist(),
          format_func=lambda x: f"{df_prev[df_prev['Modulo ID'] == x]['Modulo'].values[0]} ({df_prev[df_prev['Modulo ID'] == x]['Ambiente'].values[0]})",
      )
      if st.button("Elimina Modulo"):
        supabase.table("moduli_base").delete().eq("id", id_del).execute()
        st.success("Modulo rimosso dall'ambiente e da tutte le varianti!")
        st.rerun()

    # Totali della Variante Attiva
    tot_costo_ind = df_prev["costo_industriale"].sum()
    tot_ricarici = tot_costo_ind * (1 + (ricarico_p / 100))
    tot_scontato = tot_ricarici * (1 - (sconto_f / 100))
    tot_finale = tot_scontato * (1 + (mont_p / 100))

    st.markdown("---")
    st.subheader(f"📊 Totali Preventivo — Variante: {variante_attuale['nome_variante']}")
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Tot. Costo Industriale", f"€ {tot_costo_ind:.2f}")
    r2.metric(f"Tot. Listino (Ricarico {ricarico_p}%)", f"€ {tot_ricarici:.2f}")
    r3.metric(f"Tot. Scontato ({sconto_f}%)", f"€ {tot_scontato:.2f}")
    r4.metric(f"PREZZO FINALE (+{mont_p}% Mont.)", f"€ {tot_finale:.2f}")

    # Esportazioni
    st.divider()
    col_exp1, col_exp2 = st.columns(2)
    excel_data = genera_excel_preventivo(
        df_moduli=df_prev,
        progetto_nome=progetto_attuale["nome_cliente"],
        ricarico_proj=ricarico_p,
        sconto_fin=sconto_f,
        ricarico_mont=mont_p,
    )
    col_exp1.download_button(
        label="📊 Scarica Excel (Uso Interno)",
        data=excel_data,
        file_name=f"Preventivo_{progetto_attuale['nome_cliente']}_{variante_attuale['nome_variante']}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    pdf_data = genera_pdf_preventivo(
        df_moduli=df_prev,
        cliente_nome=progetto_attuale["nome_cliente"],
        indirizzo=progetto_attuale.get("indirizzo", ""),
        sconto_fin=sconto_f,
        ricarico_mont=mont_p,
        ricarico_proj=ricarico_p,
    )
    col_exp2.download_button(
        label="📄 Scarica PDF Offerta Cliente",
        data=pdf_data,
        file_name=f"Offerta_{progetto_attuale['nome_cliente']}_{variante_attuale['nome_variante']}.pdf",
        mime="application/pdf",
    )
  else:
    st.info("Nessun modulo ancora inserito in questo progetto.")
