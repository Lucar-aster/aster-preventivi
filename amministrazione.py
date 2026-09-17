import streamlit as st

def render_amministrazione(supabase):
    st.title("⚙️ Amministrazione & Configurazione")

    tab1, tab2, tab3 = st.tabs(["Materiali & Finiture", "Ferramenta & Accessori", "📦 Moduli Standard"])

    # --- TAB 1 e 2 (Gestione Materiali e Ferramenta esistenti) ---
    with tab1:
        st.subheader("Listino Materiali e Finiture")
        # Logica gestione materiali/finiture...

    with tab2:
        st.subheader("Listino Ferramenta e Accessori")
        # Logica gestione accessori/cerniere...

    # --- TAB 3: NUOVA GESTIONE MODULI STANDARD ---
    with tab3:
        st.subheader("📦 Configurazione Moduli Standard")
        st.caption("Crea e gestisci i moduli predefiniti da poter caricare rapidamente negli ambienti del progetto.")

        col_st1, col_st2 = st.columns([2, 1])

        with col_st1:
            st.markdown("### ➕ Aggiungi / Modifica Modulo Standard")
            with st.form("form_modulo_standard", clear_on_submit=True):
                nome_std = st.text_input("Nome Modulo Standard", placeholder="es. Base 2 Ante L600")
                cat_std = st.selectbox("Categoria", ["basi", "pensili", "colonne", "mensole", "zoccoli", "accessori"])
                apertura_std = st.selectbox("Tipo Apertura", ["ante", "cassetti", "vasistas", "gola/gola"])

                col_d1, col_d2, col_d3 = st.columns(3)
                L_std = col_d1.number_input("Larghezza (mm)", value=600, step=10)
                H_std = col_d2.number_input("Altezza (mm)", value=720, step=10)
                P_std = col_d3.number_input("Profondità (mm)", value=560, step=10)

                col_a1, col_a2 = st.columns(2)
                num_ante = col_a1.number_input("Numero Ante", value=2, min_value=0)
                num_cassetti = col_a2.number_input("Numero Cassetti", value=0, min_value=0)

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
                        "num_cassetti": num_cassetti
                    }).execute()
                    st.success(f"Modulo Standard '{nome_std}' salvato!")
                    st.rerun()

        with col_st2:
            st.markdown("### 📋 Elenco Moduli Standard")
            res_std = supabase.table("moduli_standard").select("*").execute()
            moduli_std_db = res_std.data

            if moduli_std_db:
                for m_std in moduli_std_db:
                    with st.expander(f"{m_std['nome_modulo']} ({m_std['categoria']})"):
                        st.write(f"**Dim:** {m_std['larghezza_mm']}x{m_std['altezza_mm']}x{m_std['profondita_mm']} mm")
                        st.write(f"**Apertura:** {m_std['tipo_apertura']} | Ante: {m_std['num_ante']} | Cassetti: {m_std['num_cassetti']}")
                        if st.button("🗑️ Elimina", key=f"del_std_{m_std['id']}"):
                            supabase.table("moduli_standard").delete().eq("id", m_std["id"]).execute()
                            st.rerun()
            else:
                st.info("Nessun modulo standard inserito.")
