# -*- coding: utf-8 -*-
"""
Redictra — Configurazione centralizzata.

Legge TUTTE le variabili d'ambiente in un unico posto. Se una variabile manca,
NON inventiamo un valore reale: usiamo un placeholder nel formato `__TODO_NOME__`
(tracciato in SETUP_TODO.md). Così il codice è importabile/leggibile anche senza
credenziali, ma fallisce in modo esplicito quando prova davvero a usarle.

Prodotto: Redictra = bot Telegram che ogni mattina (06:00 ora locale dell'utente)
consegna i SEGNALI DI MERCATO estratti dalla voce reale di Reddit (pain, richieste,
momentum, dibattiti, gap) sugli ARGOMENTI AI scelti dall'utente.
Lead magnet gratuito · 1 chiamata Gemini/giorno (digest madre condiviso).

Commenti in italiano; output generato per gli utenti in inglese.
"""

import os

# In locale carichiamo un eventuale .env (in CI/GitHub Actions si usano i secret).
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # python-dotenv assente o .env mancante: nessun problema, si usano le env reali.
    pass


def _env(nome: str) -> str:
    """Ritorna la env var, o un placeholder __TODO_NOME__ se assente.

    Il placeholder è volutamente NON un valore valido: se finisce in una chiamata
    reale (es. API), l'errore è evidente e rimanda a SETUP_TODO.md.
    """
    return os.environ.get(nome) or f"__TODO_{nome}__"


def manca(valore: str) -> bool:
    """True se il valore è ancora un placeholder (credenziale non configurata)."""
    return isinstance(valore, str) and valore.startswith("__TODO_")


# ============================================================================
# CREDENZIALI / SEGRETI  (tutti da env — mai hardcoded)
# ============================================================================

# --- Gemini (Google GenAI) ---
GEMINI_API_KEY = _env("GEMINI_API_KEY")

# --- Supabase (backend con SERVICE ROLE KEY → bypassa RLS) ---
SUPABASE_URL = _env("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = _env("SUPABASE_SERVICE_ROLE_KEY")

# --- Telegram ---
TELEGRAM_BOT_TOKEN = _env("TELEGRAM_BOT_TOKEN")
TELEGRAM_BOT_USERNAME = _env("TELEGRAM_BOT_USERNAME")  # es. "RedictraBot" (senza @)

# --- Accesso a invito (deep link t.me/Bot?start=CODICE) ---
# Se vuoto/placeholder → bot APERTO a tutti. Se valorizzato → serve il codice.
ACCESS_CODE = os.environ.get("ACCESS_CODE", "")


def accesso_a_invito() -> bool:
    """True se l'accesso è protetto da codice d'invito."""
    return bool(ACCESS_CODE.strip())

# --- Reddit: TRE modalità di lettura (vedi reddit_scraper.py) ---
#   "apify" → Apify actor (PRIMARIA): post + COMMENTI, nessuna approvazione Reddit.
#             A pagamento ma dentro il free tier Apify ($5/mese). Serve APIFY_TOKEN.
#   "api"   → PRAW (client_id/secret): post + commenti, ma richiede l'app Reddit
#             APPROVATA (Responsible Builder Policy 2025). Per il futuro.
#   "rss"   → feed pubblici .rss: GRATIS, nessuna chiave, ma SOLO post (no commenti).
#             Fallback se Apify si esaurisce/fallisce → il bot non si ferma mai.
# Scelta automatica (vedi modalita_reddit()): apify > api > rss.

# Apify
APIFY_TOKEN = _env("APIFY_TOKEN")
# Actor scelto: pay-per-result, no rental fee, più economico per il mix post+commenti.
APIFY_REDDIT_ACTOR = os.environ.get("APIFY_REDDIT_ACTOR", "automation-lab/reddit-scraper")

# Reddit API (PRAW) — opzionale, per il futuro
REDDIT_CLIENT_ID = _env("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = _env("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT", "Redictra/1.0 (by u/your_reddit_user)")


def modalita_reddit() -> str:
    """Sceglie la fonte: apify (se token) > api (se chiavi PRAW) > rss (fallback gratis)."""
    if not manca(APIFY_TOKEN):
        return "apify"
    if not manca(REDDIT_CLIENT_ID) and not manca(REDDIT_CLIENT_SECRET):
        return "api"
    return "rss"


# ============================================================================
# COSTANTI DI PRODOTTO  (NON sono segreti)
# ============================================================================

# --- Modello Gemini (1 sola chiamata/giorno: il digest madre) ---
# Lista in ordine di preferenza: si prova il primo, se dà 503/429 si passa al
# successivo. flash-lite è il più economico ma spesso sovraccarico (503) → flash
# come fallback affidabile (più capace, costo comunque trascurabile per 1/giorno).
MODELLI_DIGEST = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
MODELLO_DIGEST = MODELLI_DIGEST[0]  # compat: primo della lista

# --- Orario di consegna: 06:00 ORA LOCALE dell'utente (fisso, minimalista) ---
# Il cron gira ogni ora UTC; per ogni utente si calcola l'ora locale via timezone
# IANA (zoneinfo) e si consegna a chi in QUEL momento ha localmente le 06:00.
ORA_CONSEGNA_LOCALE = 6

# --- ARGOMENTI (set FISSO, uguale per tutti: niente scelta in onboarding) --
# DECISIONE DI PRODOTTO: il brief è EDITORIALE, non configurabile. Gli argomenti
# sono 5, fissi e curati → il digest madre lavora sempre sullo stesso set forte,
# così il brief è SEMPRE pieno (niente "giorno vuoto" da scelte sfortunate) e
# l'onboarding è a zero attrito (/start → solo timezone → fatto).
# I 5 sono i più AZIONABILI per un founder/builder + con subreddit ad alto volume
# che rendono ogni giorno. Tolti rispetto al vecchio modello: research e policy
# (a monte, poco azionabili, dipendevano da 'singularity' = hype) e multimodal
# (di nicchia, StableDiffusion porta rumore artistico più che mercato). 'funding'
# fuso dentro 'business' (= dove vanno i soldi E come le aziende pagano l'AI).
#
# chiave (stabile, salvata nel DB) -> (emoji, etichetta UI, subreddit di sourcing)
# I subreddit sono il "pool" da cui il digest madre legge ogni giorno. SI RIPETONO
# tra argomenti di proposito (es. LocalLLaMA copre più temi): lo scraper li legge
# UNA volta sola (cache) → conta solo il numero di subreddit UNICI per il costo
# Apify. Set attuale = 8 subreddit unici (sotto la lista precedente di ~12).
# NOMI VERIFICATI (ricerca, gen 2026). Reddit è case-sensitive negli URL.
# LOGICA per ogni argomento: 1 subreddit ALTO-VOLUME (dati nuovi ogni giorno) +
# 1 di NICCHIA-QUALITÀ (i segnali pain/richieste/gap migliori).
ARGOMENTI: dict[str, dict] = {
    "agents": {  # ai_agents (qualità) · LocalLLaMA (volume) · AI_Agents (volume agentic)
        "emoji": "🤖", "label": "Agents",
        "subreddit": ["ai_agents", "LocalLLaMA", "AI_Agents"],
    },
    "models": {  # LocalLLaMA (volume builder) · LLMDevs (qualità dev) · OpenAI (capability ecosistema)
        "emoji": "🧠", "label": "Models / LLMs",
        "subreddit": ["LocalLLaMA", "LLMDevs", "OpenAI"],
    },
    "tools": {  # ChatGPTCoding (volume dev) · LLMDevs (RAG/integration) · ChatGPTCoding+LangChain (wiring)
        "emoji": "🛠", "label": "AI Tools & Dev",
        "subreddit": ["ChatGPTCoding", "LLMDevs", "LangChain"],
    },
    "building": {  # LocalLLaMA (volume) · MLOps (infra/deploy) · LLMDevs (build pratico)
        "emoji": "🏗", "label": "Building / Infra",
        "subreddit": ["LocalLLaMA", "MLOps", "LLMDevs"],
    },
    "business": {  # ArtificialInteligence (volume AI news) · startups (1.5M, mercato) · SaaS (386k, revenue/pricing reali)
        # Assorbe il vecchio 'funding': non "chi ha raccolto X" (notizia), ma DOVE
        # vanno i soldi e COME le aziende adottano/pagano l'AI. r/SaaS è oro qui:
        # founder che condividono revenue, pricing AI, "cosa i buyer pagano davvero".
        "emoji": "💼", "label": "Business & Money",
        "subreddit": ["ArtificialInteligence", "startups", "SaaS"],
    },
}

# Le chiavi degli argomenti fissi, nell'ordine in cui appaiono nel brief.
# Punto UNICO da cui leggere "quali argomenti": il brief è uguale per tutti, quindi
# non si filtra più per utente. Usato da telegram_delivery e main al posto della
# vecchia lista per-utente.
def argomenti_fissi() -> list[str]:
    return list(ARGOMENTI.keys())


# Subreddit UNICI effettivi (per il conto costi Apify). Calcolato a runtime.
def subreddit_unici() -> list[str]:
    visti: list[str] = []
    for meta in ARGOMENTI.values():
        for s in meta.get("subreddit", []):
            if s not in visti:
                visti.append(s)
    return visti

# --- TIPI DI SEGNALE (il VALORE: sempre presenti, ADATTIVI, NON configurabili)
# L'utente NON li sceglie: appaiono solo quando quel giorno esistono davvero per
# un argomento. chiave -> (emoji, etichetta UI breve, descrizione per il prompt).
SEGNALI: dict[str, dict] = {
    "pain": {
        "emoji": "😤", "label": "Pain",
        "desc": "what frustrates people — an unsolved problem worth fixing",
    },
    "request": {
        "emoji": "🙏", "label": "Request",
        "desc": "what people explicitly ask for or say they'd pay for — a product to build",
    },
    "momentum": {
        "emoji": "🔥", "label": "Momentum",
        "desc": "what is gaining fast adoption or love — where the market is moving",
    },
    "debate": {
        "emoji": "⚔️", "label": "Debate",
        "desc": "what the community is split on — an immature, unsettled market = room",
    },
    "gap": {
        "emoji": "💡", "label": "Gap",
        "desc": "questions asked with no good answer — white space, an opportunity",
    },
}

# --- Scraping Reddit — parametri TARATI sul budget Apify (~$3.8/mese, free tier $5)
# Conto attuale: 11 subreddit unici × 30gg (5 argomenti fissi × 3 fonti, con
# riuso). Per subreddit/mese: 120 post + 360 commenti = ~$0.347. Totale 11 ×
# 0.347 ≈ $3.82/mese, sotto i $5 con margine. Avendo ridotto gli argomenti da 10
# a 5 fissi, il budget liberato è stato REINVESTITO in una 3ª fonte per argomento
# (segnali più ricchi) a parità di consumo. NON alzare N_POST/N_COMMENTI o
# aggiungere subreddit unici senza rifare i conti: i commenti pesano di più.
N_POST_PER_SUBREDDIT = 4        # top post per subreddit
N_COMMENTI_PER_POST = 3         # top commenti per post (la voce della community)
COMMENT_DEPTH = 1               # solo commenti diretti (no thread annidati = no costo extra)
MAX_CARATTERI_COMMENTO = 500    # troncamento commenti lunghi
REDDIT_TIME_FILTER = "day"      # solo le ultime 24h
