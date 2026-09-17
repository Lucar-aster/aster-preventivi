import streamlit as st


def render_amministrazione(supabase):
  st.title("⚙️ Amministrazione & Configurazione")

  tab1, tab2, tab3 = st.tabs([
      "Materiali & Finiture",
      "Ferramenta & Accessori",
      "📦 Moduli Standard",
  ])

  # --- TAB 1: GESTIONE MATERIALI E FINITURE ---
  with tab1:
    st.subheader("Listino Materiali e Finiture")

    with st.expander("➕ Aggiungi / Modifica Materiale e Finitura"):
      col_m1, col_m2, col_m3 = st.columns(3)
      nome_finitura = col_m1.text_input(
          "Nome Finitura / Collezione", placeholder="es. Laccato Opaco Cat.1"
      )
      spessore = col_m2.number_input(
          "Spessore (mm)", value=18, min_value=8, max_value=50, step=1
      )
      costo_mq = col_m3.number_input(
          "Costo Industriale (€/m²)", value=45.0, step=1.0, format="%.2f"
      )

      if st.button("💾 Salva Materiale"):
        if nome_finitura:
          supabase.table("finiture_materiali").insert({
              "nome_finitura": nome_finitura,
              "spessore_mm": spessore,
              "costo_mq": costo_mq,
          }).execute()
          st.success(f"Finitura '{nome_finitura}' aggiunta con successo!")
          st.rerun()

    res_mat = (
        supabase.table("finiture_materiali")
        .select("*")
        .order("nome_finitura")
        .execute()
    )
    mat_data = res_mat.data
    if mat_data:
      st.dataframe(mat_data, use_container_width=True)

  # --- TAB 2: GESTIONE FERRAMENTA ED ACCESSORI ---
  with tab2:
    st.subheader("Listino Ferramenta e Accessori")

    with st.expander("➕ Aggiungi Accessorio / Ferramenta"):
      col_a1, col_a2, col_a3 = st.columns(3)
      cod_acc = col_a1.text_input("Codice Articolo", placeholder="es. CER-01")
      nome_acc = col_a2.text_input(
          "Descrizione", placeholder="es. Cerniera Salice Soft-Close"
      )
      costo_acc = col_a3.number_input(
          "Costo Unitario (€)", value=3.50, step=0.10, format="%.2f"
      )

      if st.button("💾 Salva Accessorio"):
        if cod_acc and nome_acc:
          supabase.table("accessori_ferramenta").insert({
              "codice": cod_acc,
              "descrizione": nome_acc,
              "costo_unitario": costo_acc,
          }).execute()
          st.success("Accessorio salvato!")
          st.rerun()

    res_acc = supabase.table("accessori_ferramenta").select("*").execute()
    acc_data = res_acc.data
    if acc_data:
      st.dataframe(acc_data, use_container_width=True)

  # --- TAB 3: NUOVA GESTIONE MODULI STANDARD ---
  with tab3:
    st.subheader("📦 Configurazione Moduli Standard")
    st.caption(
        "Crea e gestisci i moduli predefiniti da poter caricare rapidamente"
        " negli ambienti del progetto."
    )

    col_st1, col_st2 = st.columns([2, 1])

    with col_st1:
      st.markdown("### ➕ Aggiungi Modulo Standard")
      with st.form("form_modulo_standard", clear_on_submit=True):
        nome_std = st.text_input(
            "Nome Modulo Standard", placeholder="es. Base 2 Ante L600"
        )
        cat_std = st.selectbox(
            "Categoria",
            ["basi", "pensili", "colonne", "mensole", "zoccoli", "accessori"],
        )
        apertura_std = st.selectbox(
            "Tipo Apertura", ["ante", "cassetti", "vasistas"]
        )

        col_d1, col_d2, col_d3 = st.columns(3)
        L_std = col_d1.number_input("Larghezza (mm)", value=600, step=10)
        H_std = col_d2.number_input("Altezza (mm)", value=720, step=10)
        P_std = col_d3.number_input("Profondità (mm)", value=560, step=10)

        col_a1, col_a2 = st.columns(2)
        num_ante = col_a1.number_input("Numero Ante", value=2, min_value=0)
        num_cassetti = col_a2.number_input(
            "Numero Cassetti", value=0, min_value=0
        )

        submit_std = st.form_submit_button("💾 Salva Modulo Standard")

        if submit_std and nome_std:
          supabase.table("moduli_standard").insert({
              "nome_modulo": nome_std,
              "categoria": cat_std,
              "tipo_apertura": apertura_std,
              "larghezza_mm": L_std,
              "altezza_mm": H_std,
              "profondita_mm": P_std,
              "num_ante": num_ante,
              "num_cassetti": num_cassetti,
          }).execute()
          st.success(f"Modulo Standard '{nome_std}' salvato!")
          st.rerun()

    with col_st2:
      st.markdown("### 📋 Elenco Moduli Standard")
      res_std = supabase.table("moduli_standard").select("*").execute()
      moduli_std_db = res_std.data

      if moduli_std_db:
        for m_std in moduli_std_db:
          with st.expander(
              f"{m_std['nome_modulo']} ({m_std['categoria'].upper()})"
          ):
            st.write(
                f"**Misure:** {m_std['larghezza_mm']}x{m_std['altezza_mm']}x{m_std['profondita_mm']}"
                " mm"
            )
            st.write(
                f"**Apertura:** {m_std['tipo_apertura']} | Ante:"
                f" {m_std['num_ante']} | Cassetti: {m_std['num_cassetti']}"
            )
            if st.button("🗑️ Elimina", key=f"del_std_{m_std['id']}"):
              supabase.table("moduli_standard").delete().eq(
                  "id", m_std["id"]
              ).execute()
              st.rerun()
      else:
        st.info("Nessun modulo standard inserito.")
