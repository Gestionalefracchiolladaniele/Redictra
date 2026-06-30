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
| **ARGOMENTO** (agents, models, tools…) | *di cosa* si parla | **FISSO** — set curato uguale per tutti, NON scelto dall'utente |
| **TIPO DI SEGNALE** (pain, request, momentum, debate, gap) | *che forma* ha l'informazione | **VALORE** — sempre presente, ADATTIVO, NON configurabile |

> ⚠️ **CAMBIO DI MODELLO (giu 2026): argomenti FISSI, non più scelti.** Prima
> l'utente sceglieva i suoi argomenti (filtro). Ora il brief è **editoriale**: 5
> argomenti fissi e curati, uguali per tutti. Motivi: (1) il valore è "ti dico cosa
> conta", non "configura un tool"; (2) il digest madre lavora sempre sullo stesso
> set forte → brief **sempre pieno** (niente giorni vuoti da scelte sfortunate);
> (3) onboarding a zero attrito (solo timezone). Il bot dice sempre **cosa significa
> per il mercato**; i segnali appaiono solo quando quel giorno esistono davvero
> (niente filler). Nei giorni magri è **onesto**: "se ne parla ma niente di
> concreto/nuovo oggi" — mai inventare.

### Argomenti (5 FISSI) — `config.ARGOMENTI` · `config.argomenti_fissi()`
🤖 agents · 🧠 models · 🛠 tools · 🏗 building · 💼 business. Ognuno ha emoji, label e
**3 subreddit** da cui legge. Uguali per tutti, non configurabili.
- **Tolti** rispetto al vecchio modello a 10: `research` e `policy` (a monte, poco
  azionabili da founder, dipendevano da `singularity` = hype) e `multimodal` (di
  nicchia, StableDiffusion porta rumore artistico più che mercato).
- **`funding` fuso dentro `business`** (label "Business & Money"): non "chi ha
  raccolto X" (notizia), ma DOVE vanno i soldi e COME le aziende adottano/pagano
  l'AI (mercato azionabile).

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
  telegram_delivery.componi_brief(digest)
    → tutti i 5 argomenti fissi, solo i segnali presenti (adattivo) → testo
```

**Il numero di chiamate dipende dai contenuti (1/giorno), NON dagli utenti.**
1 utente o 10.000 → sempre **1 chiamata Gemini al giorno**. Free tier abbondante.
> Nota: dal passaggio agli argomenti fissi, `componi_brief` NON prende più
> `argomenti_utente` — il brief è uguale per tutti (editoriale). Il "filtro per
> utente" non esiste più; resta solo il filtro adattivo sui segnali presenti.

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
  Per subreddit/mese: 120 post + 360 commenti ≈ $0.347. **11 subreddit unici ×
  0.347 ≈ $3.82/mese**, sotto i $5 con margine.

### Subreddit (11 unici, 3 per argomento) — logica VOLUME + QUALITÀ
Col passaggio a 5 argomenti fissi i subreddit unici sono scesi (da 12 a 11), e il
budget liberato è stato **reinvestito**: ogni argomento ora ha **3 subreddit**
invece di 2 (segnali più ricchi a parità di consumo). Nomi verificati (ricerca giu
2026), case-sensitive. Si ripetono tra argomenti ma si leggono UNA volta (cache).
- 🤖 **agents**: ai_agents (~212k) · LocalLLaMA (~760k) · **AI_Agents (~296k**, la
  più grande community di agent builders).
- 🧠 **models**: LocalLLaMA · LLMDevs (~125k) · OpenAI (~2.2M).
- 🛠 **tools**: ChatGPTCoding · LLMDevs · LangChain (~90k).
- 🏗 **building**: LocalLLaMA · MLOps (~80k) · LLMDevs.
- 💼 **business**: ArtificialInteligence (una "t", ~1.4M) · startups (~1.5M) ·
  **SaaS (~386k**, revenue/pricing AI reali — "cosa i buyer pagano davvero").
- ⚠️ **Verità da run reale:** gli iscritti sono stime; i ruoli volume/qualità pure.
  Il primo run reale dirà quali rendono davvero (specie i nuovi AI_Agents/LangChain/
  SaaS) → si aggiusta in `config.ARGOMENTI`. Scartati a tavolino perché ridondanti
  o rumorosi: `ArtificialIntelligence` (due "t", non confermato) e `r/artificial`
  (~90k, casual/filosofico, non mercato).

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
/start    → (se accesso a invito) richiede il CODICE dal deep link → benvenuto (mostra
            i 5 argomenti fissi) → scegli TIMEZONE (~8 fusi a bottoni) → "All set, domani alle 6".
/timezone → cambia fuso.
/preview  → vedi subito il brief di oggi (se il digest è già pronto).
/stop     → cancella account e dati (GDPR).
```
Niente menu a livelli, niente form, niente login. **Niente scelta argomenti** (sono
fissi) → onboarding = solo timezone. Tap, fatto.
> ⚠️ `/topics` RIMOSSO col passaggio agli argomenti fissi. La tastiera toggle
> argomenti (`kb_argomenti`) e `db.imposta_argomenti` non esistono più. La colonna
> `argomenti` resta nel DB ma è **inutilizzata** (innocua, non serve toccare lo schema).

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
Today's pulse: Agents · Models · Tools · Building · Business & Money

🤖 AGENTS
😤 Pain — Builders keep hitting agents that lose the thread on long tasks…
💡 Gap — Repeated asks for a clean way to watch an agent step-by-step; no tool owns it.

🛠 AI TOOLS & DEV
🔥 Momentum — A lightweight open-source tool-wiring framework is gaining fast traction…
⚔️ Debate — Sharp split on build-your-own RAG vs managed; no consensus = unsettled market.

💼 BUSINESS & MONEY
🙏 Request — Teams keep asking for predictable AI API costs they can price against…

—
That's the pulse. You're caught up. ☕
```
Gli stessi 5 argomenti fissi per tutti (header "Today's pulse"); solo i segnali
presenti quel giorno (adattivo). Argomenti quiet → nota onesta, niente filler.

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

**Fonte Reddit — TRE modalità** (auto-scelte da `config.modalita_reddit()`, in
ordine: apify > api > rss). Vedi la sezione "📡 Fonte dati Reddit" sopra per i
dettagli. In breve: **Apify primaria** (post+commenti, serve `APIFY_TOKEN`) →
fallback automatico a **RSS** (solo post, gratis) se Apify manca/fallisce; **PRAW**
(`api`) opzionale per il futuro (serve app Reddit approvata).

## 🗄️ Dati (Supabase) — 2 tabelle
**`utenti`**: `id_telegram` (PK), `username` (text, @ Telegram → contattare lead),
`first_name` (text), `argomenti` (text[] — **legacy, inutilizzata** dal modello
fisso; non rimossa per non toccare lo schema), `timezone` (IANA, es. `Asia/Dubai`),
`attivo` (bool), `created_at`.
**`digest_giornaliero`**: `data` (PK), `contenuto` (jsonb = il digest madre del
giorno), `created_at`. RLS on, nessuna policy pubblica (solo service role).

## 🚀 Deploy — FATTO ($0, 24/7, PC spento) ✅
Architettura disaccoppiata: i due processi comunicano SOLO via Supabase. Repo su
GitHub: **`Gestionalefracchiolladaniele/Redictra`** (privato).
- **Onboarding** → **webhook serverless su VERCEL** (`api/telegram.py`). Telegram
  chiama l'URL Vercel a ogni messaggio → scrive utenti su Supabase. Live su
  **`https://redictra-hmks.vercel.app/api/telegram`** (GET = healthcheck "ok").
  Scala a zero, gratis. ✅ Registrato su Telegram via `setWebhook`. `bot_handler.py`
  (polling) resta solo per test locali.
- **Brief giornaliero** → **GitHub Actions** (`.github/workflows/cron_runner.yml`,
  cron orario `0 * * * *`). Legge Supabase, genera/riusa il digest, invia. ✅ Secret
  configurati. **Primo run reale: domani mattina (validare qualità segnali).**

### ⚠️ Webhook Vercel — note per non rompere il deploy
- **Polling e webhook NON insieme** (Telegram Conflict 409): se accendi
  `bot_handler.py` in locale, prima togli il webhook (o ri-registralo dopo). Una
  sola istanza alla volta.
- **Vercel CLI 54.x** richiede l'entrypoint esplicito in `pyproject.toml`
  (`[tool.vercel] entrypoint = "api.telegram:handler"`), altrimenti scambia
  `main.py` per l'app e il build fallisce.
- `.vercelignore` esclude da Vercel tutto il runtime solo-cron (main.py, scraper,
  ai_engine, ...): Vercel ospita SOLO il webhook. `vercel.json` `includeFiles`
  porta config/db/telegram_delivery accanto alla funzione.
- **`telegram_delivery` importa `telegram` in modo LAZY** (dentro `consegna_brief`):
  così `componi_brief` (usato dal webhook) è importabile dove python-telegram-bot
  NON è installato (il webhook ha `api/requirements.txt` minimale: supabase/dotenv/tzdata).
- Env su Vercel (meno che su GitHub, il webhook fa solo onboarding):
  `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `SUPABASE_URL`,
  `SUPABASE_SERVICE_ROLE_KEY`, `ACCESS_CODE`.

## 📦 File del progetto
- `config.py` — env + ARGOMENTI (**5 fissi**, con 3 subreddit verificati ciascuno) +
  SEGNALI (5) + orario 06:00 + parametri costo Apify + `modalita_reddit()` +
  `subreddit_unici()` + **`argomenti_fissi()`** (punto unico per "quali argomenti").
- `reddit_scraper.py` — 3 modalità (apify/api/rss) con fallback automatico a RSS;
  top post 24h + commenti, pulizia, raggruppa per argomento (cache). Zero AI.
- `ai_engine.py` — Gemini: **1 funzione** `genera_digest_madre()` (1 chiamata,
  JSON segnali per argomento). Degrada con grazia (digest "quiet" se l'AI fallisce).
- `db.py` — Supabase: utenti (CRUD minimo, /stop) + cache digest giornaliero.
  (`imposta_argomenti` RIMOSSA col modello fisso.)
- `telegram_delivery.py` — `componi_brief(digest)` (digest → brief, argomenti fissi,
  adattivo) + `consegna_brief()` (invio disaccoppiato; import `telegram` lazy).
- `main.py` — cron: chi ha le 6 locali? → assicura_digest (genera 1 volta o riusa)
  → componi+invia per utente. try-except per utente. (Non filtra più per argomenti.)
- `bot_handler.py` — onboarding POLLING (test locali): /start (→ solo timezone),
  /timezone, /preview, /stop. **No più /topics.**
- `api/telegram.py` — onboarding WEBHOOK (Vercel, produzione): stessa logica via
  HTTP diretto a Telegram (no python-telegram-bot). GET=healthcheck, POST=update.
- `vercel.json` + `pyproject.toml` + `api/requirements.txt` + `.vercelignore` —
  config deploy Vercel (entrypoint, includeFiles, deps minime, esclusioni).
- `schema.sql` — 2 tabelle + RLS deny-all. `.github/workflows/cron_runner.yml` —
  cron orario `0 * * * *` (Secret: + APIFY_TOKEN, ACCESS_CODE). `requirements.txt`,
  `.env.example`.

## 🔁 Cosa è cambiato rispetto a Dictra (questi file SOVRASCRIVONO l'eredità)
- **Prodotto:** da "ghostwriter di post X/LinkedIn nella tua voce" (SaaS a pagamento)
  → "bot gratuito di segnali di mercato AI dalla voce di Reddit" (lead magnet).
- **AI:** da Anthropic/Claude (Haiku+Sonnet+Opus, N chiamate) → **Gemini Flash Lite,
  1 chiamata/giorno totale** (digest madre condiviso).
- **Output:** da report+post nei formati social → **un brief di market signals**,
  diretto, adattivo, senza conteggi fissi né "why it matters" come label.
- **Categorie:** da nicchia/subreddit liberi → **5 argomenti FISSI** (curati, uguali
  per tutti, NON scelti) × 5 **tipi di segnale** (valore, adattivi, non configurabili).
  (Inizialmente 10 argomenti scelti dall'utente → ridotti a 5 fissi giu 2026.)
- **Orario:** da 3 fasce (07/13/19) → **06:00 locale fisso**.
- **Fonte dati:** da PRAW-only → **Apify (primaria) + API + RSS (fallback)**, per
  aggirare la Responsible Builder Policy di Reddit (pre-approvazione 2-4 settimane).
- **RIMOSSO:** voce/file (`file_voce.py`), post X/LinkedIn/Other, archivio/preferiti,
  Stripe/piani/trial/FOMO, menu a livelli, YouTube, **scelta argomenti + /topics**.
- **AGGIUNTO:** `digest_giornaliero` (cache), `/stop` (GDPR), onboarding a bottoni,
  modalità Apify + fallback RSS, **accesso a invito** (`ACCESS_CODE`), salvataggio
  **username/first_name** per i lead, **webhook Vercel** (`api/telegram.py`),
  **argomenti fissi** (`config.argomenti_fissi()`).
- **FIX runtime:** Python 3.14 non crea l'event loop implicito → in `bot_handler.main`
  lo creiamo a mano prima di `run_polling()` (altrimenti crash all'avvio).

## 🔐 Variabili d'ambiente
`GEMINI_API_KEY` (obbl.) · `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` (obbl., usare
la **service_role**, NON l'anon) · `TELEGRAM_BOT_TOKEN` + `TELEGRAM_BOT_USERNAME`
(obbl.) · `APIFY_TOKEN` (consigliato: abilita commenti) · `ACCESS_CODE` (opz.: se
presente → bot invite-only) · `REDDIT_CLIENT_ID/SECRET/USER_AGENT` (opz., futura API).
Senza Apify né Reddit-API → fallback RSS automatico (solo post, ma gratis e subito).

## ✅ Stato — DEPLOYATO in produzione (giu 2026)
MVP completo e online. Onboarding live su Vercel (24/7, PC spento), brief via GitHub
Actions. Mancava solo il primo run reale del brief in produzione (atteso domani 6:00).
- ✅ **Modello a 5 argomenti fissi** + subreddit potenziati (11 unici, ~$3.82/mese).
- ✅ **Onboarding webhook** live: `https://redictra-hmks.vercel.app/api/telegram`,
  `setWebhook` registrato, `/start` testato e funzionante a PC spento.
- ✅ **GitHub Actions** cron attivo, Secret configurati (incl. APIFY_TOKEN, ACCESS_CODE).
- ✅ **Routing fusi verificato** (test): ogni utente servito alle SUE 6:00 locali.
- ✅ **Bot in inglese** (testi utente) + **BotFather** configurato (About/Description/Commands).
- ✅ Repo GitHub privato `Gestionalefracchiolladaniele/Redictra`; `.env` escluso (verificato).
- ⏳ **Da validare domani:** qualità dei segnali al primo run reale; quali dei nuovi
  subreddit (AI_Agents, LangChain, SaaS) rendono davvero.
- 🔐 **Da fare (sicurezza):** rigenerare il `TELEGRAM_BOT_TOKEN` (era visibile in
  screenshot durante il setup) → BotFather `/revoke`, poi aggiornare Vercel + GitHub
  Secret + `.env`.

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
   `deleteWebhook?drop_pending_updates=true` per pulire la coda. **In produzione: o
   polling (locale) O webhook (Vercel), MAI entrambi.**
9. **Vercel: `main.py` scambiato per l'app** → "does not export a top-level app/
   handler". Risolto con `pyproject.toml` `[tool.vercel] entrypoint =
   "api.telegram:handler"` + `.vercelignore` che esclude i file solo-cron.
10. **Vercel: `componi_brief` crashava all'import** perché `telegram_delivery`
    importava `from telegram import Bot` a livello di modulo, ma python-telegram-bot
    NON è nel webhook. Risolto rendendo l'import LAZY dentro `consegna_brief`.
11. **PowerShell vs `curl`:** in PowerShell `curl` è alias di `Invoke-WebRequest` e
    rompe gli URL con `&` (404). Per `setWebhook` usare `Invoke-RestMethod` con URL
    tra apici singoli, oppure Git Bash col vero `curl`.

## 🔜 Prossimi passi
1. ✅ ~~Deploy~~ **FATTO** (webhook Vercel + GitHub Actions). Vedi sezione "Deploy".
2. **VALIDARE il primo run reale** (domani 6:00): qualità dei segnali Gemini; quali
   subreddit rendono davvero (specie i nuovi AI_Agents/LangChain/SaaS) → aggiustare
   `config.ARGOMENTI` se serve.
3. **🔐 Sicurezza (priorità):** rigenerare il `TELEGRAM_BOT_TOKEN` (visibile in
   screenshot al setup) via BotFather `/revoke`, poi aggiornare Vercel env + GitHub
   Secret + `.env`. Valutare anche le altre chiavi passate in chat.
4. (Opzionale) Notifica lead: avvisare il dev quando un nuovo utente si iscrive.
5. (Marketing) usare i brief reali come contenuto LinkedIn / build-in-public.
