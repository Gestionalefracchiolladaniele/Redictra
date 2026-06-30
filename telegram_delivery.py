# -*- coding: utf-8 -*-
"""
Redictra — Composizione + consegna del brief su Telegram (DISACCOPPIATA).

`componi_brief()` trasforma il digest madre (condiviso) nel brief PERSONALE di un
utente: prende solo le sezioni dei SUOI argomenti, mostra solo i segnali presenti
(adattivo), e nei giorni magri è onesto ("se ne parla ma niente di rilevante").
È codice puro → costo $0 per utente (l'AI ha già lavorato 1 volta nel digest).

`consegna_brief()` invia. Punto unico di consegna: domani si aggiunge un canale
(email/web) senza toccare main.py.

Markdown pulito + emoji come ancore visive. Output in inglese.
"""

import asyncio
from datetime import date
from typing import Optional, TYPE_CHECKING

import config

# `python-telegram-bot` serve SOLO per la CONSEGNA (consegna_brief), che gira su
# GitHub Actions / bot in polling. NON è installato nel webhook serverless (Vercel),
# che importa questo modulo solo per componi_brief (codice puro, niente Telegram).
# Quindi importiamo `telegram` in modo LAZY, dentro le funzioni che lo usano: così
# importare telegram_delivery non fallisce dove python-telegram-bot manca.
if TYPE_CHECKING:  # solo per i type checker, non a runtime
    from telegram import Bot

# Telegram ha un limite ~4096 caratteri per messaggio.
MAX_LEN_MSG = 3900


# ============================================================================
# COMPOSIZIONE DEL BRIEF (dal digest madre → testo personale dell'utente)
# ============================================================================
def componi_brief(digest: dict, argomenti: Optional[list[str]] = None) -> str:
    """Compone il testo del brief dagli ARGOMENTI FISSI (uguali per tutti).

    - Mostra tutti gli argomenti fissi, nell'ordine di config.
    - Per ogni argomento, mostra solo i segnali presenti (adattivo).
    - Se un argomento è 'quiet', mostra la nota onesta (niente filler).

    `argomenti` è opzionale e di norma None (si usano gli argomenti fissi). Resta
    accettato per compatibilità/testing, ma il brief è editoriale: non si filtra
    più per utente.
    """
    if not argomenti:
        argomenti = config.argomenti_fissi()
    topics = (digest or {}).get("topics", {}) or {}
    labels = ", ".join(
        config.ARGOMENTI[a]["label"] for a in argomenti if a in config.ARGOMENTI
    )
    intestazione = (
        f"☀️ *AI Market Signals — {date.today().strftime('%a %d %b')}*\n"
        f"_Today's pulse: {labels}_"
    )

    sezioni: list[str] = []
    for chiave in argomenti:
        meta = config.ARGOMENTI.get(chiave)
        if not meta:
            continue
        topic = topics.get(chiave, {}) or {}
        segnali = topic.get("signals") or []

        riga_titolo = f"{meta['emoji']} *{meta['label'].upper()}*"

        if not segnali:
            # Giorno magro su questo argomento: onestà, niente invenzioni.
            nota = topic.get("quiet_note") or "Being discussed, but nothing concrete or new today."
            sezioni.append(f"{riga_titolo}\n_{nota}_")
            continue

        righe_segnali = []
        for s in segnali[:3]:
            tipo = (s.get("type") or "").lower()
            meta_seg = config.SEGNALI.get(tipo, {"emoji": "•", "label": ""})
            testo = (s.get("text") or "").strip()
            if not testo:
                continue
            etichetta = f"_{meta_seg['label']}_ — " if meta_seg.get("label") else ""
            righe_segnali.append(f"{meta_seg['emoji']} {etichetta}{testo}")
        sezioni.append(riga_titolo + "\n" + "\n".join(righe_segnali))

    corpo = "\n\n".join(sezioni) if sezioni else \
        "_Quiet day across your topics — nothing worth your time today._"
    chiusura = "—\n_That's the pulse. You're caught up._ ☕"

    return f"{intestazione}\n\n{corpo}\n\n{chiusura}"


# ============================================================================
# CONSEGNA
# ============================================================================
def _spezza(testo: str, max_len: int = MAX_LEN_MSG) -> list[str]:
    """Spezza un testo lungo in più messaggi rispettando i limiti Telegram."""
    if len(testo) <= max_len:
        return [testo]
    pezzi, corrente = [], ""
    for paragrafo in testo.split("\n\n"):
        if len(corrente) + len(paragrafo) + 2 > max_len:
            if corrente:
                pezzi.append(corrente.strip())
            corrente = paragrafo
        else:
            corrente = f"{corrente}\n\n{paragrafo}" if corrente else paragrafo
    if corrente:
        pezzi.append(corrente.strip())
    return pezzi


async def consegna_brief(chat_id: int, testo: str, bot: "Optional[Bot]" = None) -> None:
    """Invia il brief a un utente. Punto unico da cui passa ogni invio.

    Import di `telegram` LAZY (qui dentro): consegna_brief gira solo dove
    python-telegram-bot è installato (GitHub Actions / polling), non nel webhook.
    """
    from telegram import Bot
    from telegram.constants import ParseMode
    from telegram.error import TelegramError

    proprietario_bot = bot is None
    if bot is None:
        bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
    try:
        for pezzo in _spezza(testo):
            try:
                await bot.send_message(chat_id=chat_id, text=pezzo,
                                       parse_mode=ParseMode.MARKDOWN)
            except TelegramError:
                # Fallback senza Markdown (a volte il testo generato rompe il parser).
                await bot.send_message(chat_id=chat_id, text=pezzo, parse_mode=None)
    finally:
        if proprietario_bot:
            try:
                await bot.shutdown()
            except Exception:
                pass


def consegna_brief_sync(*args, **kwargs) -> None:
    """Wrapper sincrono per chiamare consegna_brief da codice non-async."""
    asyncio.run(consegna_brief(*args, **kwargs))
