# -*- coding: utf-8 -*-
"""
Redictra — Lettura Reddit + pulizia testo.

SOLO Python (regex), NIENTE AI in questo file (costo $0).

DUE MODALITÀ (scelte automaticamente da config.modalita_reddit()):
  • "rss"  → feed pubblici .rss di Reddit. NESSUNA chiave, nessuna approvazione,
             funziona SUBITO. Dà i POST (titolo + estratto), NON i commenti.
             È il default finché non hai l'app API Reddit approvata.
  • "api"  → PRAW (client_id/secret). Dà anche i COMMENTI (la voce della gente),
             ma richiede l'app Reddit APPROVATA. Si attiva da sola quando le chiavi
             sono presenti nel .env / nei secret.

In entrambi i casi l'output è lo stesso formato → `ai_engine` non cambia.

NB legale/privacy: NON conserviamo autori né ripubblichiamo testo verbatim.
Gemini ne estrae un UMORE/segnale AGGREGATO; i grezzi non vengono archiviati.
"""

import html
import json
import re
import time
from typing import Optional
from urllib.request import Request, urlopen

import feedparser

import config

# ----------------------------------------------------------------------------
# REGEX di pulizia (compilate una volta)
# ----------------------------------------------------------------------------
_RE_URL = re.compile(r"https?://\S+|www\.\S+")
_RE_MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")     # [testo](url) -> testo
_RE_HTML_TAG = re.compile(r"<[^>]+>")
_RE_MULTISPAZIO = re.compile(r"[ \t]{2,}")
_RE_MULTI_NEWLINE = re.compile(r"\n{3,}")

_RE_EMOJI = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "\U00002190-\U000021FF"
    "]+",
    flags=re.UNICODE,
)

_AUTORI_BOT = {"automoderator", "[deleted]", "[removed]"}
_RE_BOT_BOILERPLATE = re.compile(
    r"(i am a bot|this action was performed automatically|please contact the moderators)",
    re.IGNORECASE,
)


def _rimuovi_emoji_eccessive(testo: str) -> str:
    return _RE_EMOJI.sub("", testo)


def pulisci_testo(testo: Optional[str], max_caratteri: Optional[int] = None) -> str:
    """Pulizia generica: HTML entities, tag, link, emoji eccessive, spazi."""
    if not testo:
        return ""
    t = html.unescape(testo)
    t = _RE_MARKDOWN_LINK.sub(r"\1", t)
    t = _RE_URL.sub("", t)
    t = _RE_HTML_TAG.sub("", t)
    t = _rimuovi_emoji_eccessive(t)
    t = _RE_MULTISPAZIO.sub(" ", t)
    t = _RE_MULTI_NEWLINE.sub("\n\n", t)
    t = t.strip()
    if max_caratteri and len(t) > max_caratteri:
        t = t[:max_caratteri].rstrip() + "…"
    return t


# ============================================================================
# MODALITÀ RSS (default — nessuna chiave, funziona subito)
# ============================================================================
# URL feed: top del giorno di un subreddit. NB: niente commenti, solo post.
_RSS_URL = "https://www.reddit.com/r/{sub}/top/.rss?t=day&limit={limit}"

# Rate limit RSS di Reddit (2025): ~1 richiesta/minuto. Pausa prudente tra i feed.
_RSS_PAUSA_SEC = 2.0  # tra subreddit diversi; basso perché 1 feed = 1 richiesta sola


def _fetch_rss(url: str) -> Optional[str]:
    """Scarica il feed RSS con un User-Agent onesto (Reddit blocca UA vuoti)."""
    try:
        req = Request(url, headers={"User-Agent": config.REDDIT_USER_AGENT})
        with urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[reddit_scraper/rss] fetch fallito {url}: {e}")
        return None


def _scrap_subreddit_rss(nome_subreddit: str) -> list[dict]:
    """Top post 24h di un subreddit via RSS pubblico (niente commenti)."""
    nome = nome_subreddit.strip().lstrip("r/").lstrip("/")
    if not nome:
        return []
    xml = _fetch_rss(_RSS_URL.format(sub=nome, limit=config.N_POST_PER_SUBREDDIT))
    if not xml:
        return []
    feed = feedparser.parse(xml)
    risultati: list[dict] = []
    for entry in feed.entries[: config.N_POST_PER_SUBREDDIT]:
        # feedparser: 'summary' contiene l'HTML del post; lo ripuliamo a testo.
        corpo = pulisci_testo(getattr(entry, "summary", ""), 1200)
        risultati.append({
            "subreddit": nome,
            "titolo": pulisci_testo(getattr(entry, "title", "")),
            "testo": corpo,
            "score": 0,            # l'RSS non espone lo score → 0 (ordine = ranking RSS)
            "n_commenti": 0,       # l'RSS non dà i commenti
            "commenti": [],        # vuoto in modalità RSS
        })
    return risultati


# ============================================================================
# MODALITÀ API / PRAW (quando avrai l'app Reddit approvata → dà i commenti)
# ============================================================================
def _client_reddit():
    """Crea il client PRAW (read-only). Import locale: praw serve solo in modalità api."""
    import praw  # import locale → non obbligatorio se usi solo RSS
    if config.manca(config.REDDIT_CLIENT_ID) or config.manca(config.REDDIT_CLIENT_SECRET):
        raise RuntimeError("Credenziali Reddit mancanti (modalità api).")
    reddit = praw.Reddit(
        client_id=config.REDDIT_CLIENT_ID,
        client_secret=config.REDDIT_CLIENT_SECRET,
        user_agent=config.REDDIT_USER_AGENT,
        check_for_async=False,
    )
    reddit.read_only = True
    return reddit


def _e_commento_valido(commento) -> bool:
    autore = (str(commento.author).lower() if commento.author else "[deleted]")
    if autore in _AUTORI_BOT:
        return False
    corpo = getattr(commento, "body", "") or ""
    if not corpo.strip():
        return False
    if _RE_BOT_BOILERPLATE.search(corpo):
        return False
    return True


def _scrap_subreddit_api(reddit, nome_subreddit: str) -> list[dict]:
    """Top post 24h + top commenti di un subreddit via PRAW (la voce della gente)."""
    risultati: list[dict] = []
    nome = nome_subreddit.strip().lstrip("r/").lstrip("/")
    if not nome:
        return risultati
    try:
        subreddit = reddit.subreddit(nome)
        for post in subreddit.top(time_filter=config.REDDIT_TIME_FILTER,
                                  limit=config.N_POST_PER_SUBREDDIT):
            if getattr(post, "stickied", False):
                continue
            commenti_puliti: list[str] = []
            try:
                post.comment_sort = "top"
                post.comments.replace_more(limit=0)
                for c in post.comments[: config.N_COMMENTI_PER_POST * 3]:
                    if not _e_commento_valido(c):
                        continue
                    testo_c = pulisci_testo(c.body, config.MAX_CARATTERI_COMMENTO)
                    if testo_c:
                        commenti_puliti.append(testo_c)
                    if len(commenti_puliti) >= config.N_COMMENTI_PER_POST:
                        break
            except Exception:
                pass
            risultati.append({
                "subreddit": nome,
                "titolo": pulisci_testo(post.title),
                "testo": pulisci_testo(getattr(post, "selftext", ""), 1200),
                "score": int(getattr(post, "score", 0) or 0),
                "n_commenti": int(getattr(post, "num_comments", 0) or 0),
                "commenti": commenti_puliti,
            })
    except Exception as e:
        print(f"[reddit_scraper/api] subreddit '{nome}' saltato: {e}")
    return risultati


# ============================================================================
# MODALITÀ APIFY (PRIMARIA — post + commenti, nessuna approvazione Reddit)
# ============================================================================
_APIFY_RUN_URL = (
    "https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items?token={token}"
)


def _scrap_apify(subreddit_unici: list[str]) -> dict[str, list[dict]]:
    """UNA run Apify per TUTTI i subreddit → post + commenti. Ritorna per-subreddit.

    Usa l'actor config.APIFY_REDDIT_ACTOR (pay-per-result). Limiti hard dai parametri
    config (4 post, 3 commenti, depth 1) → costo controllato (~$3.5/mese, free tier $5).
    Se fallisce, solleva → il chiamante fa fallback a RSS.
    """
    actor = config.APIFY_REDDIT_ACTOR.replace("/", "~")  # Apify vuole author~name nell'URL
    url = _APIFY_RUN_URL.format(actor=actor, token=config.APIFY_TOKEN)

    # Nomi parametri dallo schema ufficiale dell'actor automation-lab/reddit-scraper:
    # `urls` (non startUrls), `includeComments` (non skipComments), `maxPostsPerSource`,
    # `maxCommentsPerPost`, `commentDepth`. Nomi sbagliati = limiti ignorati + 0 commenti.
    payload = {
        "urls": [
            f"https://www.reddit.com/r/{s}/top/?t={config.REDDIT_TIME_FILTER}"
            for s in subreddit_unici
        ],
        "maxPostsPerSource": config.N_POST_PER_SUBREDDIT,
        "includeComments": True,
        "maxCommentsPerPost": config.N_COMMENTI_PER_POST,
        "commentDepth": config.COMMENT_DEPTH,
        "sort": "top",
    }
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=300) as resp:
        items = json.loads(resp.read().decode("utf-8", errors="replace"))

    # L'actor ritorna una lista mista di post e commenti. Li raggruppiamo per
    # subreddit e annidiamo i commenti sotto il loro post.
    per_sub: dict[str, list[dict]] = {s: [] for s in subreddit_unici}
    post_per_id: dict[str, dict] = {}

    # Schema reale actor: post = {type:'post', id, title, selfText, score, numComments,
    # subreddit}; comment = {type:'comment', postId, body, score}.
    for it in items if isinstance(items, list) else []:
        tipo = (it.get("type") or "").lower()

        if tipo == "comment":
            pid = str(it.get("postId") or "")
            corpo = pulisci_testo(it.get("body") or "", config.MAX_CARATTERI_COMMENTO)
            if pid in post_per_id and corpo:
                lst = post_per_id[pid]["commenti"]
                if len(lst) < config.N_COMMENTI_PER_POST:
                    lst.append(corpo)
        elif tipo == "post":
            sub = (it.get("subreddit") or "").lstrip("r/").strip()
            sub_match = next((s for s in subreddit_unici if s.lower() == sub.lower()), None)
            if not sub_match:
                continue
            post = {
                "subreddit": sub_match,
                "titolo": pulisci_testo(it.get("title") or ""),
                "testo": pulisci_testo(it.get("selfText") or "", 1200),
                "score": int(it.get("score") or 0),
                "n_commenti": int(it.get("numComments") or 0),
                "commenti": [],
            }
            pid = str(it.get("id") or "")
            if pid:
                post_per_id[pid] = post
            per_sub[sub_match].append(post)

    # L'ordine del feed Apify È già il ranking 'top' → non riordino (score spesso 0).
    return per_sub


# ============================================================================
# PUNTO D'INGRESSO — raccoglie per argomento, scegliendo la modalità da config
# ============================================================================
def raccogli_per_argomenti() -> dict[str, list[dict]]:
    """Raccoglie i post puliti PER ARGOMENTO (digest madre, 1 volta/giorno).

    Modalità (config.modalita_reddit()): apify > api > rss. Cache dei subreddit
    condivisi tra argomenti → ogni subreddit si legge una volta sola. Se Apify
    fallisce, fallback automatico a RSS (il bot non si ferma mai).
    """
    modalita = config.modalita_reddit()
    print(f"[reddit_scraper] modalità: {modalita}")

    unici = config.subreddit_unici()
    cache_subreddit: dict[str, list[dict]] = {}

    if modalita == "apify":
        try:
            cache_subreddit = _scrap_apify(unici)
        except Exception as e:
            print(f"[reddit_scraper/apify] FALLITO ({e}) → fallback a RSS.")
            modalita = "rss"

    if modalita in ("api", "rss") and not cache_subreddit:
        reddit = _client_reddit() if modalita == "api" else None
        for nome_sub in unici:
            if modalita == "api":
                cache_subreddit[nome_sub] = _scrap_subreddit_api(reddit, nome_sub)
            else:
                cache_subreddit[nome_sub] = _scrap_subreddit_rss(nome_sub)
            time.sleep(_RSS_PAUSA_SEC)  # gentile col rate-limit

    # Da cache per-subreddit → raggruppa per argomento (un subreddit può servirne più).
    per_argomento: dict[str, list[dict]] = {}
    for chiave, meta in config.ARGOMENTI.items():
        post_argomento: list[dict] = []
        for nome_sub in meta.get("subreddit", []):
            post_argomento.extend(cache_subreddit.get(nome_sub, []))
        post_argomento.sort(key=lambda p: p.get("score", 0), reverse=True)
        per_argomento[chiave] = post_argomento

    return per_argomento
