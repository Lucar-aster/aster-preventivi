import pandas as pd
import streamlit as st


def render_amministrazione(supabase):
  st.title('⚙️ Pannello Amministrazione & Regole')

  tab1, tab2, tab3 = st.tabs(
      ['Materiali per Spessore', 'Soglie Cerniere', 'Listino Accessori']
  )

  with tab1:
    st.subheader('Prezzi Finiture e Materiali (€/m²)')
    mat = supabase.table('finiture_materiali').select('*').execute().data
    df_mat = pd.DataFrame(mat)
    df_mat_edit = st.data_editor(
        df_mat, num_rows='dynamic', key='ed_mat', use_container_width=True
    )
    if st.button('💾 Salva Materiali'):
      supabase.table('finiture_materiali').upsert(
          df_mat_edit.to_dict('records')
      ).execute()
      st.success('Materiali aggiornati!')

  with tab2:
    st.subheader('Regola Soglie Cerniere (Altezza Anta)')
    soglie = supabase.table('soglie_cerniere').select('*').execute().data
    df_soglie = pd.DataFrame(soglie)
    df_soglie_edit = st.data_editor(
        df_soglie, num_rows='dynamic', key='ed_soglie', use_container_width=True
    )
    if st.button('💾 Salva Soglie Cerniere'):
      supabase.table('soglie_cerniere').upsert(
          df_soglie_edit.to_dict('records')
      ).execute()
      st.success('Soglie aggiornate!')

  with tab3:
    st.subheader('Listino Ferramenta e Accessori')
    acc = supabase.table('accessori_ferramenta').select('*').execute().data
    df_acc = pd.DataFrame(acc)
    df_acc_edit = st.data_editor(
        df_acc, num_rows='dynamic', key='ed_acc', use_container_width=True
    )
    if st.button('💾 Salva Accessori'):
      supabase.table('accessori_ferramenta').upsert(
          df_acc_edit.to_dict('records')
      ).execute()
      st.success('Accessori aggiornati!')
