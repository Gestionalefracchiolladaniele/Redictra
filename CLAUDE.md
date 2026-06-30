# Redictra — Specifica di progetto

> Nome del prodotto: **Redictra** (Reddit + "dict" → "il dettato di Reddit").
> Cartella di lavoro: `bot reddit notizie`. Eredita codice/infra da Dictra
> (vecchio `xinkedinai`), ma è un PRODOTTO DIVERSO: vedi "Cosa è cambiato".

---

## 🎯 Cos'è
Un **bot Telegram gratuito** che ogni mattina alle **06:00 (ora locale dell'utente)**
legge le conversazioni reali su Reddit (post **+ commenti**) e consegna i
**SEGNALI DI MERCATO** sull'AI: cosa la gente *vuole, odia, chiede, su cosa si
divide e cosa non trova*. Non un news bot — **market intelligence dalla voce della
gente**, per founder che non hanno tempo ma vogliono sapere dove si muove il mercato.

**Promessa:** *"In 60 secondi a colazione sai cosa vuole il mercato AI — e dove c'è
spazio per te."*

## 🧲 Perché esiste (scopo strategico)
È un **lead magnet** per il developer/founder che lo costruisce: attira e qualifica
founder/CTO (ecosistema AI, target Dubai), genera autorità e conversazioni 1:1.
Il valore per l'utente è il brief; il valore per noi è **il contatto** e la
**materia prima per contenuti LinkedIn** (build-in-public + i segnali stessi).
NON è un prodotto da vendere: è gratis, minimalista, senza funnel.

## 👥 Per chi
Founder, indie hacker, builder e CTO nell'AI. Mercato internazionale, in inglese.
Non geo-vincolato (Dubai è il focus personale del developer, non un limite del tool).

---

## 🧠 Il modello (il cuore di tutto)

Due ASSI, ognuno al suo posto:

| Asse | Cos'è | Ruolo |
|---|---|---|
| **ARGOMENTO** (agents, models, tools…) | *di cosa* si parla | **FILTRO** — l'utente sceglie i suoi (≥3 consigliato) |
| **TIPO DI SEGNALE** (pain, request, momentum, debate, gap) | *che forma* ha l'informazione | **VALORE** — sempre presente, ADATTIVO, NON configurabile |

> L'utente sceglie **di cosa** sapere; il bot dice sempre **cosa significa per il
> mercato**. I segnali appaiono solo quando quel giorno esistono davvero per quel
> argomento (niente filler). Nei giorni magri il bot è **onesto**: "se ne parla ma
> niente di concreto/nuovo oggi" — mai inventare.

### Argomenti (10) — `config.ARGOMENTI`
agents · models · tools · funding · research · business · building · policy ·
multimodal · opensource. Ognuno ha emoji, label e i **subreddit** da cui legge.

### Tipi di segnale (5) — `config.SEGNALI`
😤 pain (problema da risolvere) · 🙏 request (prodotto da fare) · 🔥 momentum
(dove va il mercato) · ⚔️ debate (mercato immaturo = spazio) · 💡 gap (white space).

---

## ⚙️ Architettura costi — 1 chiamata AI/giorno per TUTTI

Il lavoro pesante (leggere Reddit + estrarre i segnali) è **identico per tutti** →
si fa **una volta**. Personalizzazione = filtro in codice ($0).

```
DIGEST MADRE (1 chiamata Gemini/giorno, condivisa):
  reddit_scraper.raccogli_per_argomenti()  → post+commenti per OGNI argomento
  ai_engine.genera_digest_madre()          → JSON: segnali per ogni argomento
  db.salva_digest_oggi()                   → salvato in `digest_giornaliero`

PER UTENTE (codice puro, $0):
  telegram_delivery.componi_brief(digest, argomenti_utente)
    → prende solo gli argomenti dell'utente, solo i segnali presenti → testo
```

**Il numero di chiamate dipende dai contenuti (1/giorno), NON dagli utenti.**
1 utente o 10.000 → sempre **1 chiamata Gemini al giorno**. Free tier abbondante.

## 📡 Fonte dati Reddit — TRE modalità (auto-scelte da `config.modalita_reddit()`)

Reddit ha introdotto la **Responsible Builder Policy (nov 2025)**: l'API ufficiale
ora richiede **pre-approvazione** (~2-4 settimane). Per non dipenderne, il codice ha
3 modalità, scelte in automatico in quest'ordine:

| Modalità | Cosa dà | Costo | Quando si attiva |
|---|---|---|---|
| **`apify`** (PRIMARIA) | post **+ commenti** | ~$4/mese (free tier Apify $5) | se c'è `APIFY_TOKEN` |
| `api` (PRAW) | post + commenti | gratis ma serve **app Reddit approvata** | se ci sono `REDDIT_CLIENT_ID/SECRET` |
| `rss` (FALLBACK) | **solo post** (no commenti) | €0, nessuna chiave | sempre disponibile; usato se Apify fallisce |

- **Apify** = actor `automation-lab/reddit-scraper` (pay-per-result, no rental fee:
  $1.15/1k post · $0.58/1k commenti). UNA run/giorno legge tutti i subreddit. Se
  fallisce/esaurito → **fallback automatico a RSS** (il bot non si ferma mai).
- **Costo controllato dai parametri** in `config.py` (NON alzare senza rifare i conti):
  `N_POST_PER_SUBREDDIT=4`, `N_COMMENTI_PER_POST=3`, `COMMENT_DEPTH=1`, `time="day"`.
  12 subreddit unici × 4 post × 3 commenti × 30gg ≈ **$4.16/mese**, sotto i $5.

### Subreddit (12 unici) — logica VOLUME + QUALITÀ
Ogni argomento ha **1 subreddit ad alto volume** (garantisce dati nuovi ogni giorno)
**+ 1 di nicchia-qualità** (dà i segnali pain/richieste/gap migliori). Nomi verificati,
case-sensitive. Si ripetono tra argomenti ma si leggono UNA volta (cache).
- Alto-volume: LocalLLaMA, MachineLearning, ArtificialInteligence, OpenAI, ChatGPTCoding,
  StableDiffusion, startups, singularity.
- Nicchia-qualità (builder, problemi reali): **ai_agents, LLMDevs, MLOps, generativeAI**.
- `singularity` = solo RIEMPITIVO dove serve volume (research/policy): è hype, non mercato.
- ⚠️ Verità da run reale: ruoli volume/qualità sono stime da membri+ricerca; il primo
  run dirà quali rendono davvero → si aggiusta in `config.ARGOMENTI`.

## 🕕 Orari & fusi — un cron, tutto il mondo, alle 6 locali

Il cron GitHub Actions gira **ogni ora UTC** (`0 * * * *`), **fisso**. Gli orari
**non sono nel file**: vivono nel **DB** (timezone per utente). A ogni run, `main.py`
calcola per ogni utente l'ora locale e serve chi ha **le 06:00** in quel momento
(`config.ORA_CONSEGNA_LOCALE = 6`). Aggiungere un fuso NON tocca GitHub.

**Il digest si genera una volta, al PRIMO fuso che si sveglia**, e i fusi successivi
lo **riusano** (`main.assicura_digest`): "esiste il digest di oggi? sì → riuso; no →
genero e salvo". Così l'AI gira 1 volta e tutti gli altri fusi ricevono gratis.

> Nota: il digest è "di oggi" per data **UTC**. Chi è a Ovest, ore dopo, riceve lo
> stesso digest (non rigenerato). Va bene per un brief giornaliero ("oggi", non
> "ultimo minuto"). `REDDIT_TIME_FILTER = "day"` (solo ultime 24h, deciso).

---

## 📲 Esperienza utente (minimalista, zero attrito)
```
/start    → (se accesso a invito) richiede il CODICE dal deep link → poi benvenuto +
            scegli ARGOMENTI (toggle, ≥3 consigliato) → scegli TIMEZONE (~8 fusi a
            bottoni) → "Tutto pronto, domani alle 6".
/topics   → cambia argomenti.
/timezone → cambia fuso.
/preview  → vedi subito il brief di oggi (se il digest è già pronto).
/stop     → cancella account e dati (GDPR).
```
Niente menu a livelli, niente form, niente login. Tap, tap, fatto.

## 🔑 Accesso a INVITO (deep link)
`config.ACCESS_CODE` (da `.env`): se valorizzato, il bot è **invite-only**. Link
d'invito = `t.me/<bot>?start=<ACCESS_CODE>`. Chi apre il link entra; chi fa `/start`
nudo (o codice errato) e non è già iscritto → "🔒 invite-only". Un solo codice
condiviso (semplice, riusabile). Se `ACCESS_CODE` vuoto → bot aperto a tutti.
Al `/start` si salvano **username + first_name** (li dà Telegram, gratis) → servono
a riconoscere e **contattare i lead** (l'`id_telegram` da solo NON è contattabile).
Niente campo "occupazione": ridondante (gli argomenti già qualificano + inviti tu).

## 🧱 Formato del brief (esempio reale)
```
☀️ AI Market Signals — Tue 28 Jan
Your topics: Agents · Tools · Funding

🤖 AGENTS
😤 Pain — Builders keep hitting agents that lose the thread on long tasks…
💡 Gap — Repeated asks for a clean way to watch an agent step-by-step; no tool owns it.

🛠 TOOLS & DEV
🔥 Momentum — A lightweight open-source tool-wiring framework is gaining fast traction…
⚔️ Debate — Sharp split on build-your-own RAG vs managed; no consensus = unsettled market.

💰 FUNDING
📈 (signal)…

—
That's the pulse. You're caught up. ☕
```
Solo gli argomenti dell'utente; solo i segnali presenti quel giorno (adattivo).

---

## ⚠️ Principi non negoziabili (sicurezza & legalità)
1. **Lettura Reddit a basso volume** via Apify (proxy/account loro) o RSS pubblici o
   API ufficiale approvata. Uso non commerciale, lead-gen leggera. 1 run/giorno.
2. **Non ripubblicare contenuto Reddit verbatim.** Reddit è il *segnale*; il brief
   è **analisi originale** generata da Gemini. Mai incollare titoli/commenti.
3. **Solo umore AGGREGATO** ("the community is split"), **mai** citare un commento
   o nominare un utente. Non si salvano autori.
4. **Stateless sui grezzi.** I post/commenti si processano e si scartano; si
   conserva solo il digest derivato (output) + l'iscrizione dell'utente.
5. **Dato personale minimo:** solo `id_telegram` (fornito volontariamente al
   /start). `/stop` cancella tutto (GDPR). Una riga di privacy nel /start basta
   a questa scala.

> NON è consulenza legale. Per un lead magnet gratuito a basso volume il rischio è
> basso e difendibile. Avvocato + privacy policy formale servirebbero SOLO se un
> domani si monetizza con clienti paganti.

## 🛠️ Stack tecnico
Python · Supabase (DB, service role) · `google-genai` (Gemini Flash Lite) ·
python-telegram-bot · GitHub Actions (cron orario). Modello: `gemini-2.5-flash`
(primario, più affidabile) con fallback `gemini-2.5-flash-lite` — vedi `config.MODELLI_DIGEST`.

**Fonte Reddit — due modalità** (auto-scelte da `config.modalita_reddit()`):
- **`rss`** (DEFAULT): feed pubblici `.rss`, **nessuna chiave, nessuna approvazione**,
  funziona subito. Limite: dà i POST (titolo+estratto), NON i commenti. Usa `feedparser`.
- **`api`** (PRAW): dà anche i COMMENTI, ma richiede l'app Reddit **APPROVATA**
  (Responsible Builder Policy 2025, pre-approvazione ~2-4 settimane, free tier).
  Si attiva DA SOLA quando `REDDIT_CLIENT_ID`/`SECRET` sono presenti. `praw` opzionale.

## 🗄️ Dati (Supabase) — 2 tabelle
**`utenti`**: `id_telegram` (PK), `username` (text, @ Telegram → contattare lead),
`first_name` (text), `argomenti` (text[]), `timezone` (IANA, es. `Asia/Dubai`),
`attivo` (bool), `created_at`.
**`digest_giornaliero`**: `data` (PK), `contenuto` (jsonb = il digest madre del
giorno), `created_at`. RLS on, nessuna policy pubblica (solo service role).

## 🚀 Deploy — architettura target ($0, 24/7, PC spento)
Problema: l'utente apre il link d'invito QUANDO vuole → l'onboarding deve essere
sempre raggiungibile, ma non si può tenere il PC acceso. Soluzione disaccoppiata,
i due processi comunicano SOLO via Supabase:
- **Onboarding** → **webhook serverless** (Telegram chiama la function quando arriva
  un messaggio → scrive utenti su Supabase). Scala a zero, gratis. *Da costruire*:
  oggi `bot_handler.py` usa polling (ok solo per i test locali, PC acceso).
- **Brief giornaliero** → **GitHub Actions** (cron orario, legge Supabase, invia).
  Gratis, gira nel cloud, PC spento. *Da attivare*: caricare repo + Secret.
> Per ORA si testa in LOCALE (bot in polling sul PC). Webhook+cron = passo successivo,
> DOPO aver validato che onboarding + brief reale funzionano.

## 📦 File del progetto
- `config.py` — env + ARGOMENTI (10, con subreddit verificati) + SEGNALI (5) +
  orario 06:00 + parametri costo Apify + `modalita_reddit()` + `subreddit_unici()`.
- `reddit_scraper.py` — 3 modalità (apify/api/rss) con fallback automatico a RSS;
  top post 24h + commenti, pulizia, raggruppa per argomento (cache). Zero AI.
- `ai_engine.py` — Gemini: **1 funzione** `genera_digest_madre()` (1 chiamata,
  JSON segnali per argomento). Degrada con grazia (digest "quiet" se l'AI fallisce).
- `db.py` — Supabase: utenti (CRUD minimo, /stop) + cache digest giornaliero.
- `telegram_delivery.py` — `componi_brief()` (digest → brief personale, adattivo) +
  `consegna_brief()` (invio disaccoppiato).
- `main.py` — cron: chi ha le 6 locali? → assicura_digest (genera 1 volta o riusa)
  → componi+invia per utente. try-except per utente.
- `bot_handler.py` — onboarding: /start (argomenti+timezone), /topics, /timezone,
  /preview, /stop.
- `schema.sql` — 2 tabelle + RLS deny-all. `.github/workflows/cron_runner.yml` —
  cron orario `0 * * * *`. `requirements.txt`, `.env.example`.

## 🔁 Cosa è cambiato rispetto a Dictra (questi file SOVRASCRIVONO l'eredità)
- **Prodotto:** da "ghostwriter di post X/LinkedIn nella tua voce" (SaaS a pagamento)
  → "bot gratuito di segnali di mercato AI dalla voce di Reddit" (lead magnet).
- **AI:** da Anthropic/Claude (Haiku+Sonnet+Opus, N chiamate) → **Gemini Flash Lite,
  1 chiamata/giorno totale** (digest madre condiviso).
- **Output:** da report+post nei formati social → **un brief di market signals**,
  diretto, adattivo, senza conteggi fissi né "why it matters" come label.
- **Categorie:** da nicchia/subreddit liberi → 10 **argomenti** (filtro) × 5 **tipi
  di segnale** (valore, adattivi, non configurabili).
- **Orario:** da 3 fasce (07/13/19) → **06:00 locale fisso**.
- **Fonte dati:** da PRAW-only → **Apify (primaria) + API + RSS (fallback)**, per
  aggirare la Responsible Builder Policy di Reddit (pre-approvazione 2-4 settimane).
- **RIMOSSO:** voce/file (`file_voce.py`), post X/LinkedIn/Other, archivio/preferiti,
  Stripe/piani/trial/FOMO, Edge Function webhook, menu a livelli, YouTube.
- **AGGIUNTO:** `digest_giornaliero` (cache), `/stop` (GDPR), onboarding a bottoni,
  modalità Apify + fallback RSS, **accesso a invito** (`ACCESS_CODE`), salvataggio
  **username/first_name** per i lead.
- **FIX runtime:** Python 3.14 non crea l'event loop implicito → in `bot_handler.main`
  lo creiamo a mano prima di `run_polling()` (altrimenti crash all'avvio).

## 🔐 Variabili d'ambiente
`GEMINI_API_KEY` (obbl.) · `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` (obbl., usare
la **service_role**, NON l'anon) · `TELEGRAM_BOT_TOKEN` + `TELEGRAM_BOT_USERNAME`
(obbl.) · `APIFY_TOKEN` (consigliato: abilita commenti) · `ACCESS_CODE` (opz.: se
presente → bot invite-only) · `REDDIT_CLIENT_ID/SECRET/USER_AGENT` (opz., futura API).
Senza Apify né Reddit-API → fallback RSS automatico (solo post, ma gratis e subito).

## ✅ Stato — MVP FUNZIONANTE end-to-end (testato in locale)
Il flusso completo gira: onboarding → scraping Apify (post+commenti) → digest Gemini
(segnali reali) → salvataggio → `/preview` consegna il brief su Telegram. Provato con
utente reale (@Daniele_fracchiolla, argomenti agents/funding/research/tools, tz Europe/Rome).
- ✅ Dipendenze installate (`google-genai`, `python-telegram-bot`, `supabase`, `feedparser`, `tzdata`).
- ✅ `.env` configurato (Gemini, Supabase service_role, Telegram, Apify, ACCESS_CODE).
- ✅ Tabelle Supabase (`utenti` +username/first_name, `digest_giornaliero`).
- ✅ Bot Telegram: onboarding (argomenti+fuso+invito) e `/preview` funzionano.
- ✅ Apify: post + commenti, limiti rispettati. Gemini: digest con segnali reali.

## 🐞 Bug reali risolti al primo test (NON reintrodurre)
1. **Python 3.14 / event loop:** `run_polling()` crasha ("no current event loop") →
   in `bot_handler.__main__` creiamo il loop a mano prima di `main()`.
2. **dotenv non installato** → il `.env` veniva ignorato (config tutto `__TODO_`).
   Risolto con `pip install -r requirements.txt`.
3. **Supabase: anon key invece di service_role** → scritture rifiutate. Usare la
   **service_role** (decodificata deve dire `"role":"service_role"`).
4. **Colonne mancanti** (`first_name`/`username`) → `PGRST204`. Aggiunte con ALTER TABLE.
   Dopo un ALTER, **riavviare il bot** (Supabase cache lo schema).
5. **Apify: parametri sbagliati** → l'actor ignorava i limiti (100 post!) e dava 0
   commenti. Nomi GIUSTI: `urls` (non startUrls), `includeComments:true` (non skipComments),
   `maxPostsPerSource`, `maxCommentsPerPost`. Schema output reale: post = `{type:'post',
   id, title, selfText, score, numComments, subreddit}`; comment = `{type:'comment',
   postId, body, score}`. (`score` spesso 0 → si usa l'ordine del feed.)
6. **`zoneinfo` su Windows** → `ZoneInfoNotFoundError` (manca il DB fusi) → installato
   `tzdata`. Serve anche in produzione su ambienti senza tz DB.
7. **Gemini 503 "high demand"** su `flash-lite` (spesso sovraccarico) → `MODELLI_DIGEST`
   = lista `[gemini-2.5-flash, gemini-2.5-flash-lite]` con retry e fallback automatico.
   flash è più affidabile; costo trascurabile per 1 chiamata/giorno.
8. **Conflict 409** (`getUpdates`) = due istanze del bot insieme → tenerne UNA sola.
   `deleteWebhook?drop_pending_updates=true` per pulire la coda.

## 🔜 Prossimi passi
1. **Deploy** (target $0, 24/7, PC spento) — vedi sezione "Deploy":
   - Onboarding → **webhook serverless** (riscrivere bot da polling). Necessario perché
     l'utente apre il link d'invito quando vuole lui (col PC spento il polling non basta).
   - Brief giornaliero → **GitHub Actions** (repo + Secret). Aggiungere i Secret nuovi
     (`GEMINI_API_KEY`, `APIFY_TOKEN`, `ACCESS_CODE`, Supabase, Telegram).
2. Confermare quali subreddit rendono ogni giorno (oggi funding/research a volte 0 →
   aggiustare `config.ARGOMENTI` se serve).
3. **Sicurezza:** rigenerare le chiavi usate in chat durante il setup.
4. (Marketing) usare i brief reali come contenuto LinkedIn / build-in-public.
