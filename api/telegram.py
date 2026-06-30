# -*- coding: utf-8 -*-
"""
Redictra — Webhook Telegram (serverless, Vercel).

Questa è la versione SERVERLESS dell'onboarding: invece di girare in polling sul
PC (bot_handler.py), è una funzione che Telegram CHIAMA via HTTP quando arriva un
messaggio. Così l'onboarding funziona 24/7 a PC spento.

Perché HTTP diretto e non python-telegram-bot:
  python-telegram-bot è pensato per girare come processo sempre attivo (polling o
  webhook server). In un ambiente serverless che si sveglia e muore a ogni richiesta
  è scomodo e pesante. Le API di Telegram sono semplici REST → qui parliamo con
  Telegram via `urllib` (zero dipendenze extra). La LOGICA (chi può entrare, cosa
  salvare) resta identica a bot_handler.py e riusa db.py/config.py.

Flusso onboarding (zero attrito, argomenti FISSI):
  /start [CODICE]  → (se invite-only) controlla il codice → salva utente → chiede TIMEZONE
  tap su un fuso  → salva timezone → "All set"
  /timezone       → richiede il fuso
  /preview        → mostra il brief di oggi (se il digest è pronto)
  /stop           → cancella utente (GDPR)

Endpoint Vercel: POST /api/telegram  (è l'URL da registrare come webhook Telegram).
GET /api/telegram → healthcheck ("ok"), utile per verificare che il deploy risponda.
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler

# I moduli condivisi (config/db/telegram_delivery) stanno nella radice del repo.
# Vercel li copia accanto alla funzione (vedi vercel.json "includeFiles"), ma per
# sicurezza aggiungiamo sia la dir della funzione sia la radice del progetto al
# path, così l'import funziona sia in locale sia sul serverless.
_QUI = os.path.dirname(os.path.abspath(__file__))
for _p in (_QUI, os.path.dirname(_QUI)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import config
import db

# Telegram Bot API base (token dal config, che lo legge dalle env di Vercel).
_API = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"

# Stessi fusi del bot in polling (bot_handler.FUSI), duplicati qui per non importare
# python-telegram-bot nel serverless. Se ne aggiungi uno, aggiornalo in ENTRAMBI.
FUSI = [
    ("Asia/Dubai", "🇦🇪 Dubai (UTC+4)"),
    ("Europe/London", "🇬🇧 London (UTC+0/1)"),
    ("Europe/Rome", "🇪🇺 Central Europe (UTC+1/2)"),
    ("America/New_York", "🇺🇸 New York (UTC-5/4)"),
    ("America/Los_Angeles", "🇺🇸 Los Angeles (UTC-8/7)"),
    ("Asia/Singapore", "🇸🇬 Singapore (UTC+8)"),
    ("Asia/Kolkata", "🇮🇳 India (UTC+5:30)"),
    ("Australia/Sydney", "🇦🇺 Sydney (UTC+10/11)"),
]


# ============================================================================
# Chiamate Telegram (HTTP diretto)
# ============================================================================
def _tg(metodo: str, payload: dict) -> None:
    """Chiama un metodo della Bot API (sendMessage, answerCallbackQuery, ...).

    Best-effort: in un webhook un errore di rete non deve far fallire la risposta
    HTTP a Telegram (altrimenti reinvia l'update all'infinito).
    """
    dati = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{_API}/{metodo}", data=dati,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[webhook] errore chiamata {metodo}: {e}")


def _invia(chat_id: int, testo: str, tastiera: dict | None = None) -> None:
    payload = {"chat_id": chat_id, "text": testo, "parse_mode": "Markdown"}
    if tastiera:
        payload["reply_markup"] = tastiera
    _tg("sendMessage", payload)


def _kb_fusi() -> dict:
    """InlineKeyboard coi fusi (un bottone per riga), come dict JSON Telegram."""
    return {"inline_keyboard": [
        [{"text": label, "callback_data": f"tz:{iana}"}] for iana, label in FUSI
    ]}


def _riga_argomenti() -> str:
    return " · ".join(
        f"{m['emoji']} {m['label']}" for m in config.ARGOMENTI.values()
    )


# ============================================================================
# Handler dei comandi / bottoni
# ============================================================================
def _on_start(chat_id: int, utente_tg: dict, args: str) -> None:
    # Accesso a invito: il codice arriva dal deep link "/start CODICE".
    if config.accesso_a_invito():
        codice = (args or "").strip()
        gia_iscritto = db.get_utente(chat_id)
        if codice != config.ACCESS_CODE and not gia_iscritto:
            _invia(chat_id,
                   "🔒 Redictra is invite-only.\n\n"
                   "You need an invite link to join. If you have one, open it again.")
            return

    # Salva username + nome (gratis da Telegram) → per riconoscere/contattare i lead.
    db.crea_o_aggiorna_utente(chat_id, {
        "username": utente_tg.get("username") or "",
        "first_name": utente_tg.get("first_name") or "",
    })

    _invia(
        chat_id,
        "👋 *Welcome to Redictra.*\n\n"
        "Every morning at *6 AM your time*, I read what people really say on Reddit "
        "about AI and send you the *market signals* that matter — what they want, "
        "hate, ask for, and can't find. For founders who have no time but want to "
        "know where the market is moving.\n\n"
        f"You'll get the pulse on: {_riga_argomenti()}.\n\n"
        "One thing only — where are you? I'll deliver at *6 AM your local time*:",
        tastiera=_kb_fusi(),
    )


def _on_timezone_cmd(chat_id: int) -> None:
    db.crea_o_aggiorna_utente(chat_id)
    _invia(chat_id,
           "🌍 *Your timezone* — pick the closest one (delivery is 6 AM local):",
           tastiera=_kb_fusi())


def _on_set_tz(chat_id: int, iana: str, callback_id: str) -> None:
    from zoneinfo import ZoneInfo
    try:
        ZoneInfo(iana)
    except Exception:
        _tg("answerCallbackQuery",
            {"callback_query_id": callback_id, "text": "Invalid timezone.",
             "show_alert": True})
        return
    db.aggiorna_utente(chat_id, {"timezone": iana})
    _tg("answerCallbackQuery", {"callback_query_id": callback_id})
    _invia(chat_id,
           "✅ *All set!*\n\nYou'll get your first AI market brief tomorrow at 6 AM "
           "your time. ☕\n\n"
           "• /preview — see today's brief now\n"
           "• /timezone — change your timezone\n"
           "• /stop — unsubscribe & delete your data")


def _on_preview(chat_id: int) -> None:
    utente = db.get_utente(chat_id)
    if not utente:
        _invia(chat_id, "Start with /start first 🙂")
        return
    riga = db.get_digest_oggi()
    if not riga or not riga.get("contenuto"):
        _invia(chat_id,
               "Today's brief isn't generated yet — it's built at the first 6 AM "
               "delivery around the world. Check back, or wait for tomorrow morning. ☕")
        return
    # componi_brief è codice puro (no python-telegram-bot) → importabile qui.
    import telegram_delivery
    testo = telegram_delivery.componi_brief(riga["contenuto"])
    _invia(chat_id, testo)


def _on_stop(chat_id: int) -> None:
    db.cancella_utente(chat_id)
    _invia(chat_id,
           "✅ You're unsubscribed and your data has been deleted. Come back anytime "
           "with /start. 👋")


# ============================================================================
# Router: smista un update Telegram al handler giusto
# ============================================================================
def gestisci_update(update: dict) -> None:
    # --- Tap su un bottone inline (scelta fuso) ---
    if "callback_query" in update:
        cq = update["callback_query"]
        chat_id = cq["from"]["id"]
        data = cq.get("data") or ""
        if data.startswith("tz:"):
            _on_set_tz(chat_id, data.split(":", 1)[1], cq["id"])
        else:
            _tg("answerCallbackQuery", {"callback_query_id": cq["id"]})
        return

    # --- Messaggio di testo (comandi) ---
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return
    chat_id = msg["chat"]["id"]
    utente_tg = msg.get("from") or {}
    testo = (msg.get("text") or "").strip()
    if not testo.startswith("/"):
        return  # ignoriamo testo libero: l'onboarding è solo comandi + bottoni

    # "/start CODICE" → comando + argomenti
    parti = testo.split(maxsplit=1)
    comando = parti[0].split("@", 1)[0].lower()  # gestisce /start@RedictraBot
    args = parti[1] if len(parti) > 1 else ""

    if comando == "/start":
        _on_start(chat_id, utente_tg, args)
    elif comando == "/timezone":
        _on_timezone_cmd(chat_id)
    elif comando == "/preview":
        _on_preview(chat_id)
    elif comando == "/stop":
        _on_stop(chat_id)
    # altri comandi: ignorati di proposito (onboarding minimalista)


# ============================================================================
# Entry point Vercel (handler HTTP)
# ============================================================================
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Healthcheck: aprire l'URL nel browser deve dare "ok" (deploy vivo).
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Redictra webhook ok")

    def do_POST(self):
        # Telegram invia l'update come JSON nel body.
        lunghezza = int(self.headers.get("Content-Length") or 0)
        corpo = self.rfile.read(lunghezza) if lunghezza else b"{}"
        try:
            update = json.loads(corpo or b"{}")
            gestisci_update(update)
        except Exception as e:
            # Non far fallire la risposta: logghiamo e rispondiamo 200 comunque,
            # così Telegram non reinvia all'infinito lo stesso update.
            print(f"[webhook] errore gestione update: {e}")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')
