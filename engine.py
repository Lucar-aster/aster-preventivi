import math


def ottieni_num_cerniere(h_anta_mm, tabelle_soglie):
  """Rileva il numero di cerniere in base alle soglie dal DB."""
  for soglia in sorted(tabelle_soglie, key=lambda x: x['h_max_mm']):
    if h_anta_mm <= soglia['h_max_mm']:
      return soglia['num_cerniere']
  return 6


def calcola_modulo_parametrico(
    categoria,
    L_mm,
    H_mm,
    P_mm,
    spessore_mensola_mm=30,
    tipo_apertura='ante',
    num_ante=1,
    num_cassetti=0,
    vani_eldom=[],
    eldom_incassato=False,
    prezzi_mat={},
    prezzi_acc={},
    soglie_cerniere=[],
    sfrido=1.15,
):
  """Engine di calcolo distinto per le 6 categorie di moduli."""
  L, H, P = L_mm / 1000, H_mm / 1000, P_mm / 1000
  sp_18, sp_8, sp_22 = 0.018, 0.008, 0.022

  costo_mat_tot = 0.0
  costo_acc_tot = 0.0
  dettaglio = {}

  # --- 1. BASI, PENSILI, COLONNE ---
  if categoria in ['basi', 'pensili', 'colonne']:
    mq_18 = 0.0
    fianchi_18 = 2 * (H * P)

    if categoria == 'basi':
      fondo_18 = (L - 2 * sp_18) * P
      catene_18 = 2 * ((L - 2 * sp_18) * 0.10)
      mq_18 = fianchi_18 + fondo_18 + catene_18
      costo_acc_tot += 4 * prezzi_acc.get('PIED-01', 0.80)  # 4 Piedini

    elif categoria in ['pensili', 'colonne']:
      cielo_fondo_18 = 2 * ((L - 2 * sp_18) * P)
      mq_18 = fianchi_18 + cielo_fondo_18
      if categoria == 'pensili':
        costo_acc_tot += prezzi_acc.get('ATT-01', 4.50)  # Attaccaglie

    # Schiena 8mm
    mq_8 = H * L

    # Eldom e Ripiani (18mm)
    h_eldom = sum(vani_eldom)
    if vani_eldom:
      mq_18 += (len(vani_eldom) * 2) * ((L - 2 * sp_18) * (P - 0.02))

    h_utile = H_mm - h_eldom
    num_ripiani = max(0, math.floor(h_utile / 450) - 1)
    mq_18 += num_ripiani * ((L - 2 * sp_18) * (P - 0.02))

    # Ante (22mm) e Cerniere
    if tipo_apertura == 'ante':
      h_anta = H_mm if eldom_incassato else (H_mm - h_eldom)
      mq_22 = (h_anta / 1000) * L
      h_singola_anta = h_anta / num_ante if num_ante > 0 else 0
      n_cerniere = (
          ottieni_num_cerniere(h_singola_anta, soglie_cerniere) * num_ante
      )
      costo_acc_tot += n_cerniere * prezzi_acc.get('CER-01', 3.50)
    elif tipo_apertura == 'vasistas':
      mq_22 = H * L
      costo_acc_tot += prezzi_acc.get('VASIS-01', 65.00)
    else:  # cassetti
      mq_22 = H * L
      costo_acc_tot += num_cassetti * prezzi_acc.get('GUIDA-01', 18.00)

    # Calcolo Costi Materia Prima (18mm, 8mm, 22mm)
    costo_mat_tot = (
        (mq_18 * sfrido * prezzi_mat.get(18, 25.0))
        + (mq_8 * sfrido * prezzi_mat.get(8, 15.0))
        + (mq_22 * sfrido * prezzi_mat.get(22, 30.0))
    )

  # --- 2. PANNELLI E MENSOLE ---
  elif categoria == 'mensole':
    mq = (L * P) * sfrido
    costo_sq = prezzi_mat.get(spessore_mensola_mm, 40.0)
    costo_mat_tot = mq * costo_sq

  # --- 3. GOLE E ZOCCOLI ---
  elif categoria == 'zoccoli':
    ml = L * sfrido
    costo_mat_tot = ml * prezzi_acc.get('ZOC-01', 8.50)

  # --- 4. ACCESSORI / FERRAMENTA ---
  elif categoria == 'accessori':
    costo_acc_tot = L_mm * prezzi_acc.get('GENERICO', 10.0)  # Usato come Qta

  costo_industriale = costo_mat_tot + costo_acc_tot
  return round(costo_industriale, 2)
