# Redictra 🟠

**Un bot Telegram gratuito che ogni mattina alle 6 (ora tua) ti dice cosa vuole il
mercato AI** — letto dalle conversazioni reali su Reddit. Non notizie: *segnali di
mercato*. Per founder che non hanno tempo ma vogliono sapere dove c'è spazio.

> *"In 60 secondi a colazione sai cosa vuole il mercato AI — e dove c'è spazio per te."*

---

## Come funziona (in breve)

1. L'utente fa `/start`, sceglie i suoi **argomenti AI** (agents, models, funding…)
   e il suo **fuso orario**.
2. Ogni mattina alle **06:00 ora sua** riceve un brief con i **segnali di mercato**
   sui suoi argomenti: 😤 dolori · 🙏 richieste · 🔥 momentum · ⚔️ dibattiti · 💡 gap.
3. I segnali sono estratti da post **e commenti** Reddit (la voce della community),
   come **umore aggregato** — mai citazioni di singoli.

## Perché costa quasi zero
Una **sola** chiamata Gemini al giorno genera il "digest madre" (tutti gli argomenti
insieme), condiviso da tutti gli utenti e tutti i fusi. Il brief personale di ognuno
è solo un **filtro in codice** sul digest → $0 per utente. 1 utente o 10.000: sempre
1 chiamata/giorno.

## Stack
Python · Gemini Flash Lite (`google-genai`) · Reddit (PRAW) · Supabase · Telegram ·
GitHub Actions (cron orario, gratis).

---

## Setup rapido (vedi SETUP_TODO.md per i dettagli)

1. **Credenziali** (in `.env` locale o nei Secret di GitHub):
   - `GEMINI_API_KEY` — da Google AI Studio.
   - `TELEGRAM_BOT_TOKEN` / `TELEGRAM_BOT_USERNAME` — da @BotFather.
   - `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` — app "script" su reddit.com/prefs/apps.
   - `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` — dal progetto Supabase.
2. **Database**: esegui `schema.sql` nell'SQL Editor di Supabase (crea 2 tabelle).
3. **Dipendenze**: `pip install -r requirements.txt`.
4. **Bot interattivo** (onboarding): `python bot_handler.py` (deve girare always-on:
   un piccolo VPS/PaaS, o localmente per i test).
5. **Consegna giornaliera**: il workflow `.github/workflows/cron_runner.yml` gira
   ogni ora su GitHub Actions e consegna a chi ha le 6 locali. Imposta gli stessi
   segreti tra i Secret del repository.

## Comandi del bot
- `/start` — iscriviti: scegli argomenti + fuso.
- `/topics` — cambia gli argomenti.
- `/timezone` — cambia il fuso.
- `/preview` — vedi subito il brief di oggi (se già generato).
- `/stop` — cancella iscrizione e dati (GDPR).

## Note legali (sintesi)
Usa l'**API ufficiale** di Reddit nel free tier. Il brief è **analisi originale**
(non ripubblicazione di post): solo umore aggregato, mai citazioni o nomi utente.
Unico dato personale: l'`id_telegram` dato volontariamente al `/start`, cancellabile
con `/stop`. Per un lead magnet gratuito a basso volume è difendibile; una consulenza
legale serve solo se un domani si monetizza. **Non è consulenza legale.**
