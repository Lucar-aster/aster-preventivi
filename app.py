from amministrazione import render_amministrazione
from engine import calcola_modulo_parametrico
import pandas as pd
from supabase import create_client
import streamlit as st

st.set_page_config(
    page_title='Preventivatore Arredi Modulari', layout='wide'
)

# Connessione Supabase
URL = st.secrets.get('SUPABASE_URL', 'https://tuo-id.supabase.co')
KEY = st.secrets.get('SUPABASE_KEY', 'tua-chiave-anon')
supabase = create_client(URL, KEY)

# Navigazione
st.sidebar.title('📍 Navigazione')
modalita = st.sidebar.radio('Seleziona Sezione:', ['Preventivatore', 'Amministrazione'])

if modalita == 'Amministrazione':
  render_amministrazione(supabase)
else:
  st.title('📐 Preventivatore Residenze e Ambienti')

  # 1. DATI PROGETTO
  with st.expander('📋 Dati Residenza / Cliente', expanded=True):
    col_c1, col_c2, col_c3 = st.columns(3)
    cliente = col_c1.text_input('Nome Cliente / Progetto', 'Residenza Rossi')
    sconto_fin = col_c2.slider('Sconto Finale Progetto %', 0, 30, 10)
    ricarico_mont = col_c3.slider('Montaggio & Trasporto %', 0, 25, 10)

  st.divider()

  # 2. INSERIMENTO MODULO
  st.subheader('➕ Aggiungi Modulo')
  c1, c2, c3, c4 = st.columns(4)

  ambiente = c1.selectbox(
      'Ambiente', ['Cucina', 'Zona Giorno', 'Bagno', 'Zona Notte']
  )
  categoria = c2.selectbox(
      'Categoria Modulo',
      ['basi', 'pensili', 'colonne', 'mensole', 'zoccoli', 'accessori'],
  )
  nome_mod = c3.text_input('Nome Modulo', 'Base 2 Ante')
  ricarico_mod = c4.slider('Ricarico Modulo %', 50, 200, 120)

  # Caricamento Dati da Supabase per tendine
  mat_db = supabase.table('finiture_materiali').select('*').execute().data
  finiture_unil = list(set([m['nome_finitura'] for m in mat_db]))
  soglie_db = supabase.table('soglie_cerniere').select('*').execute().data
  acc_db = supabase.table('accessori_ferramenta').select('*').execute().data

  col_d1, col_d2, col_d3, col_d4 = st.columns(4)
  L = col_d1.number_input('Larghezza (mm)', value=600, step=50)
  H = col_d2.number_input('Altezza (mm)', value=720, step=10)
  P = col_d3.number_input('Profondità (mm)', value=560, step=10)
  finitura_sel = col_d4.selectbox('Finitura Materiale', finiture_unil)

  # Opzioni Avanzate per Categoria
  apertura = 'ante'
  n_ante, n_cass, sp_mensola = 1, 0, 30
  eldom_inc, vani_eldom = False, []

  if categoria in ['basi', 'pensili', 'colonne']:
    ca1, ca2, ca3 = st.columns(3)
    apertura = ca1.selectbox('Tipo Apertura', ['ante', 'cassetti', 'vasistas'])
    if apertura == 'ante':
      n_ante = ca2.number_input('N° Ante', value=1, min_value=1)
      if categoria == 'colonne':
        eldom_inc = ca3.checkbox('Colonna Frigo (Incassato)', value=False)
        vano = st.number_input('Vano Eldom (mm) - 0 se nessuno', value=0)
        if vano > 0:
          vani_eldom = [vano]
    elif apertura == 'cassetti':
      n_cass = ca2.number_input('N° Cassetti', value=2, min_value=1)

  elif categoria == 'mensole':
    sp_mensola = st.selectbox(
        'Spessore Mensola (mm)', [8, 12, 18, 22, 25, 30, 40, 50, 60]
    )

  # Mappatura prezzi materiale selezionato
  prezzi_mat_map = {
      m['spessore_mm']: float(m['costo_mq'])
      for m in mat_db
      if m['nome_finitura'] == finitura_sel
  }
  prezzi_acc_map = {a['codice']: float(a['costo_unitario']) for a in acc_db}

  # Calcolo
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

  prezzo_vendita = costo_ind * (1 + (ricarico_mod / 100))

  st.info(
      f'💰 **Costo Industriale:** € {costo_ind:.2f} | 🏷️ **Prezzo'
      f' Vendita Modulo:** € {prezzo_vendita:.2f}'
  )

  if st.button('➕ Salva Modulo nel Progetto'):
    # Inserimento temporaneo in session_state
    if 'carrello' not in st.session_state:
      st.session_state.carrello = []

    st.session_state.carrello.append({
        'Ambiente': ambiente,
        'Categoria': categoria,
        'Modulo': nome_mod,
        'Dimensioni (L x H x P)': f'{L}x{H}x{P}',
        'Costo Ind. €': costo_ind,
        'Ricarico %': ricarico_mod,
        'Prezzo Vendita €': prezzo_vendita,
    })
    st.success('Modulo salvato nel preventivo!')

  # 3. TABELLA RIEPILOGATIVA E TOTALI
  st.divider()
  st.subheader('📊 Riepilogo Preventivo Residenza')

  if 'carrello' in st.session_state and st.session_state.carrello:
    df_prev = pd.DataFrame(st.session_state.carrello)
    st.dataframe(df_prev, use_container_width=True)

    tot_lordo = df_prev['Prezzo Vendita €'].sum()
    tot_scontato = tot_lordo * (1 - (sconto_fin / 100))
    tot_finale = tot_scontato * (1 + (ricarico_mont / 100))

    r1, r2, r3 = st.columns(3)
    r1.metric('Totale Listino Ambienti', f'€ {tot_lordo:.2f}')
    r2.metric(f'Totale con Sconto ({sconto_fin}%)', f'€ {tot_scontato:.2f}')
    r3.metric(
        f'TOTALE RESIDENZA (+{ricarico_mont}% Montaggio)', f'€ {tot_finale:.2f}'
    )
  else:
    st.warning('Nessun modulo ancora inserito nel preventivo.')
