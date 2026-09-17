import pandas as pd
import streamlit as st

def render_amministrazione(supabase):
    st.title("⚙️ Pannello di Amministrazione & Listini")

    main_tab1, main_tab2, main_tab3, main_tab4 = st.tabs([
        "🎨 Materiali & Finiture",
        "📦 Moduli Standard",
        "🛠️ Ferramenta & Componenti",
        "📐 Soglie Cerniere"
    ])

    # =========================================================
    # TAB 1: MATERIALI & FINITURE
    # =========================================================
    with main_tab1:
        st.subheader("🎨 Gestione Finiture e Materiali")
        mat_db = supabase.table("finiture_materiali").select("*").order("nome_finitura").execute().data
        
        if mat_db:
            df_mat = pd.DataFrame(mat_db)
            st.dataframe(df_mat, use_container_width=True)
        
        with st.expander("➕ Aggiungi Nuova Finitura"):
            with st.form("form_nuova_finitura"):
                col_f1, col_f2 = st.columns(2)
                nome_f = col_f1.text_input("Nome Finitura", "Laccato Opaco")
                spess_f = col_f2.number_input("Spessore (mm)", value=18, step=1)
                
                col_f3, col_f4 = st.columns(2)
                costo_mq = col_f3.number_input("Costo al m² (€)", value=45.0, step=1.0)
                costo_ml = col_f4.number_input("Costo Bordo al ml (€)", value=2.5, step=0.5)
                
                if st.form_submit_button("Salva Finitura"):
                    supabase.table("finiture_materiali").insert({
                        "nome_finitura": nome_f,
                        "spessore_mm": spess_f,
                        "costo_mq": costo_mq,
                        "costo_ml_bordo": costo_ml
                    }).execute()
                    st.success("Finitura salvata!")
                    st.rerun()

    # =========================================================
    # TAB 2: MODULI STANDARD
    # =========================================================
    with main_tab2:
        st.subheader("📦 Gestione Moduli Standard")
        mod_std_db = supabase.table("moduli_standard").select("*").execute().data
        
        if mod_std_db:
            st.dataframe(pd.DataFrame(mod_std_db), use_container_width=True)
            
        with st.expander("➕ Aggiungi Modulo Standard"):
            with st.form("form_nuovo_mod_std"):
                col_m1, col_m2 = st.columns(2)
                nome_m = col_m1.text_input("Nome Modulo", "Base 2 Ante 60")
                cat_m = col_m2.selectbox("Categoria", ["basi", "pensili", "colonne", "mensole"])
                
                col_m3, col_m4, col_m5 = st.columns(3)
                l_m = col_m3.number_input("Larghezza (mm)", value=600, step=10)
                h_m = col_m4.number_input("Altezza (mm)", value=720, step=10)
                p_m = col_m5.number_input("Profondità (mm)", value=560, step=10)
                
                col_m6, col_m7, col_m8 = st.columns(3)
                apert_m = col_m6.selectbox("Apertura", ["ante", "cassetti", "vasistas", "fisso"])
                num_a = col_m7.number_input("Num. Ante", value=2, step=1)
                num_c = col_m8.number_input("Num. Cassetti", value=0, step=1)
                
                if st.form_submit_button("Salva Modulo Standard"):
                    supabase.table("moduli_standard").insert({
                        "nome_modulo": nome_m,
                        "categoria": cat_m,
                        "larghezza_mm": l_m,
                        "altezza_mm": h_m,
                        "profondita_mm": p_m,
                        "tipo_apertura": apert_m,
                        "num_ante": num_a,
                        "num_cassetti": num_c
                    }).execute()
                    st.success("Modulo Standard creato!")
                    st.rerun()

    # =========================================================
    # TAB 3: FERRAMENTA, GOLE, ZOCCOLI & ILLUMINAZIONE
    # =========================================================
    with main_tab3:
        st.subheader("🛠️ Gestione Ferramenta e Componenti")
        
        acc_db = supabase.table("accessori_ferramenta").select("*").order("codice").execute().data or []
        df_acc = pd.DataFrame(acc_db) if acc_db else pd.DataFrame(columns=["id", "codice", "nome", "costo_unitario", "unita_misura", "categoria"])

        f_tab1, f_tab2, f_tab3, f_tab4 = st.tabs([
            "🔩 Ferramenta & Accessori",
            "📐 Gole",
            "🪵 Zoccoli",
            "💡 Illuminazione"
        ])

        def render_sezione_ferramenta(categoria_key, categoria_label, prefix_code, default_um="PZ"):
            st.markdown(f"**Listino: {categoria_label}**")
            
            if not df_acc.empty:
                if "categoria" in df_acc.columns:
                    df_sub = df_acc[df_acc["categoria"] == categoria_key]
                else:
                    df_sub = df_acc[df_acc["codice"].str.startswith(prefix_code, na=False)]
            else:
                df_sub = pd.DataFrame()

            if not df_sub.empty:
                df_edited = st.data_editor(
                    df_sub[["id", "codice", "nome", "costo_unitario", "unita_misura"]],
                    key=f"editor_ferr_{categoria_key}",
                    hide_index=True,
                    column_config={
                        "id": None,
                        "codice": st.column_config.TextColumn("Codice", required=True),
                        "nome": st.column_config.TextColumn("Descrizione / Nome", required=True),
                        "costo_unitario": st.column_config.NumberColumn("Costo (€)", format="%.2f €", min_value=0.0),
                        "unita_misura": st.column_config.SelectboxColumn("U.M.", options=["PZ", "ML", "MQ", "KG", "SET"])
                    },
                    use_container_width=True
                )
                
                if st.button(f"💾 Salva Modifiche {categoria_label}", key=f"btn_save_{categoria_key}"):
                    for _, row in df_edited.iterrows():
                        supabase.table("accessori_ferramenta").update({
                            "codice": row["codice"],
                            "nome": row["nome"],
                            "costo_unitario": float(row["costo_unitario"]),
                            "unita_misura": row["unita_misura"]
                        }).eq("id", row["id"]).execute()
                    st.success(f"Listino {categoria_label} aggiornato!")
                    st.rerun()
            else:
                st.info(f"Nessun elemento presente nel listino {categoria_label}.")

            with st.expander(f"➕ Aggiungi Elemento a {categoria_label}"):
                with st.form(f"form_add_{categoria_key}"):
                    c_col1, c_col2 = st.columns(2)
                    codice_in = c_col1.text_input("Codice Articolo", value=f"{prefix_code}_001")
                    nome_in = c_col2.text_input("Nome / Descrizione", value=f"Nuovo elemento {categoria_label}")
                    
                    p_col1, p_col2 = st.columns(2)
                    costo_in = p_col1.number_input("Costo Unitario (€)", value=10.0, step=0.50, format="%.2f")
                    um_in = p_col2.selectbox("Unità di Misura", ["PZ", "ML", "MQ", "KG", "SET"], index=["PZ", "ML", "MQ", "KG", "SET"].index(default_um))

                    if st.form_submit_button(f"Salva in {categoria_label}"):
                        data_insert = {
                            "codice": codice_in,
                            "nome": nome_in,
                            "costo_unitario": costo_in,
                            "unita_misura": um_in
                        }
                        if "categoria" in df_acc.columns or len(df_acc) == 0:
                            data_insert["categoria"] = categoria_key

                        supabase.table("accessori_ferramenta").insert(data_insert).execute()
                        st.success(f"Elemento aggiunto a {categoria_label}!")
                        st.rerun()

        with f_tab1:
            render_sezione_ferramenta("ferramenta", "Ferramenta & Accessori", "FER", default_um="PZ")

        with f_tab2:
            render_sezione_ferramenta("gole", "Gole", "GOL", default_um="ML")

        with f_tab3:
            render_sezione_ferramenta("zoccoli", "Zoccoli", "ZOC", default_um="ML")

        with f_tab4:
            render_sezione_ferramenta("illuminazione", "Illuminazione", "ILL", default_um="ML")

    # =========================================================
    # TAB 4: SOGLIE CERNIERE
    # =========================================================
    with main_tab4:
        st.subheader("⚙️ Soglie Calcolo Cerniere")
        soglie_db = supabase.table("soglie_cerniere").select("*").order("h_max_mm").execute().data
        
        if soglie_db:
            st.dataframe(pd.DataFrame(soglie_db), use_container_width=True)
            
        with st.expander("➕ Aggiungi Soglia Cerniera"):
            with st.form("form_soglia"):
                col_s1, col_s2 = st.columns(2)
                h_max = col_s1.number_input("Altezza Max (mm)", value=2100, step=100)
                n_cern = col_s2.number_input("Numero Cerniere", value=4, step=1)
                
                if st.form_submit_button("Salva Soglia"):
                    supabase.table("soglie_cerniere").insert({
                        "h_max_mm": h_max,
                        "num_cerniere": n_cern
                    }).execute()
                    st.success("Soglia cerniera salvata!")
                    st.rerun()
