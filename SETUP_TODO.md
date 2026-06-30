# SETUP_TODO — Redictra

Azioni umane residue per portare Redictra dal codice (già scritto) al funzionamento.
Spuntare man mano. Le voci marcate **DA CONFERMARE** sono scelte ragionevoli da
validare insieme.

---

## 1. Credenziali (segreti)
Metterle in `.env` (locale) e/o nei **Secret** del repo GitHub (Actions). Mai committarle.

- [ ] `GEMINI_API_KEY` — Google AI Studio → "Get API key". Free tier sufficiente.
- [ ] `TELEGRAM_BOT_TOKEN` — @BotFather → `/newbot` → copia il token.
- [ ] `TELEGRAM_BOT_USERNAME` — lo username del bot (senza @), es. `RedictraBot`.
- [ ] `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` — https://www.reddit.com/prefs/apps
      → "create app" → tipo **script** → copia id e secret.
- [ ] `REDDIT_USER_AGENT` — onesto, es. `Redictra/1.0 (by u/tuo_utente)`.
- [ ] `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` — Supabase → Project Settings →
      API. **Service role** (non l'anon key): bypassa RLS, è un segreto del backend.

## 2. Database
- [ ] Eseguire `schema.sql` nell'SQL Editor di Supabase (crea `utenti` e
      `digest_giornaliero`, abilita RLS deny-all).

## 3. Dipendenze
- [ ] `pip install -r requirements.txt` (Python 3.11+).

## 4. Avvio
- [ ] **Onboarding bot** (`bot_handler.py`): deve girare always-on per rispondere a
      /start, /topics, ecc. Per i test va bene locale; in produzione un piccolo
      VPS/PaaS (Railway, Fly.io, una VM). NB: il cron NON serve il bot interattivo —
      sono due processi distinti.
- [ ] **Cron di consegna** (`main.py` via GitHub Actions): impostare gli stessi
      Secret tra i Secret del repository. Il workflow gira ogni ora.

## 5. Da testare insieme (end-to-end)
- [ ] `/start` → scelta argomenti (toggle) → scelta fuso → messaggio "all set".
- [ ] Lanciare manualmente il workflow (`workflow_dispatch`) o `python main.py`:
      - se è il primo run del giorno → genera il digest (1 chiamata Gemini) e lo salva;
      - verifica che `digest_giornaliero` abbia una riga con `contenuto` JSON valido.
- [ ] `/preview` → arriva un brief coerente con gli argomenti scelti.
- [ ] Verifica **fuso**: impostare un utente con timezone tale che ORA siano le 6
      locali → deve essere servito; un altro fuso → non servito in quel run.
- [ ] Giorno magro / argomento vuoto → compare la nota onesta, niente filler.
- [ ] `/stop` → la riga utente sparisce da `utenti`.

## 6. DA CONFERMARE (scelte di default, non bloccanti)
- [ ] **Subreddit per argomento** (`config.ARGOMENTI`): alcuni nomi vanno verificati
      che esistano e siano pubblici (es. `Rag`, `Oobabooga`, `AutoGenAI`,
      `ArtificialInteligence` — quest'ultimo è scritto così su Reddit). Aggiustare i
      mancanti; uno sbagliato viene saltato (log soft), non rompe nulla.
- [ ] **ID modello Gemini**: `gemini-2.5-flash-lite` via `google-genai`
      (`client.models.generate_content`, `GenerateContentConfig`,
      `response_mime_type="application/json"`). Confermare al primo run reale: se
      l'SDK/ID cambia, `genera_digest_madre` degrada a "quiet" (nessun crash) ma il
      brief sarebbe vuoto → va sistemato l'ID, non ignorato.
- [ ] **Lista fusi** (`bot_handler.FUSI`): ~8 fusi comuni. Aggiungerne se servono.
- [ ] **N. post/commenti** (`config.N_POST_PER_SUBREDDIT`, `N_COMMENTI_PER_POST`):
      tarati per dare materiale ai segnali senza gonfiare i token. Regolabili.
- [ ] **Testi dei messaggi** del bot (in inglese): default ragionevoli, rifinibili.

## 7. Note operative
- Il **cron orario** con 0 utenti in fascia esce in pochi secondi → costo Actions
  trascurabile.
- Il **digest** si genera UNA volta/giorno (primo fuso che si sveglia) e gli altri
  fusi lo riusano. Se vuoi forzare la rigenerazione, cancella la riga di oggi da
  `digest_giornaliero`.
- **Privacy**: aggiungere (consigliato) una riga di privacy nel messaggio /start già
  presente ("conserviamo solo il tuo ID Telegram; /stop per cancellarti").
