# 🪑 Preventivatore Arredi Su Misura (Streamlit + Supabase + GitHub)

Un'applicazione web open-source progettata per falegnamerie, showroom di arredamento e produttori di cucine su misura per calcolare preventivi basati su superfici (mq), metri lineari (ml) o quantità fisse.

## 🚀 Funzionalità principali
- **Modulo Calcolo Su Misura**: Calcolo automatico di metri quadri (Base x Altezza) e metri lineari per top, pannelli e zoccoli.
- **Anagrafica Clienti e Catalogo Listini**: Gestione prodotti, finiture e manodopera.
- **Gestione Preventivi**: Stato preventivi (In Attesa, Approvato, Rifiutato) e calcolo automatico di Imponibile ed IVA.
- **Pronto per Supabase**: Integrabile con PostgreSQL/Supabase per il salvataggio persistente dei dati.

## 📁 Struttura della repository
```text
├── app.py                # Applicazione principale Streamlit
├── requirements.txt      # Dipendenze Python
└── README.md             # Istruzioni d'uso
```

## 🛠️ Come eseguirlo in locale
1. Clona la repository:
   ```bash
   git clone https://github.com/tuo-utente/preventivatore-arredi.git
   cd preventivatore-arredi
   ```
2. Installa le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```
3. Avvia l'applicazione:
   ```bash
   streamlit run app.py
   ```

## 🗄️ Configurazione Supabase (Database)
Per rendere i dati persistenti tramite Supabase:
1. Crea un progetto su [Supabase](https://supabase.com).
2. Crea le tabelle `clienti`, `catalogo`, e `preventivi`.
3. Aggiungi le credenziali in `.streamlit/secrets.toml` o nelle Environment Variables su Streamlit Community Cloud:
   ```toml
   SUPABASE_URL = "https://tuo-progetto.supabase.co"
   SUPABASE_KEY = "la-tua-chiave-anon"
   ```
