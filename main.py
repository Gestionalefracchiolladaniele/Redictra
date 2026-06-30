# -*- coding: utf-8 -*-
"""
Redictra — Orchestratore del cron (GitHub Actions, ogni ora UTC).

Logica (il cuore del sistema, come discusso):
  1. C'è qualche utente che ADESSO ha localmente le 06:00? (timezone IANA)
     - NO  → esci subito (~secondi, run quasi gratis).
  2. Esiste già il DIGEST MADRE di OGGI nel DB?
     - NO  → è il PRIMO run utile della giornata: scraping Reddit (tutti gli
             argomenti) → 1 chiamata Gemini → SALVA il digest.   ← unica chiamata AI
     - SÌ  → RIUSA quello salvato (nessuna chiamata AI).
  3. Per ogni utente da servire: dal digest prendi le sezioni dei SUOI argomenti
     → componi il brief → invia su Telegram. (filtro = codice puro, $0)
  4. try-except PER UTENTE: un fallimento non blocca gli altri.

Così l'AI gira UNA volta al giorno (al primo fuso che si sveglia) e tutti gli
altri fusi ricevono consegne gratis pescando dal digest già pronto.

Esecuzione: `python main.py`
"""

import asyncio
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram import Bot

import config
import db
import reddit_scraper
import ai_engine
import telegram_delivery


def ora_locale_utente(utente: dict, adesso_utc: datetime) -> int | None:
    """Ritorna l'ora locale (0-23) dell'utente, o None se il timezone è invalido."""
    tz_nome = utente.get("timezone") or "UTC"
    try:
        tz = ZoneInfo(tz_nome)
    except (ZoneInfoNotFoundError, ValueError):
        return None
    return adesso_utc.astimezone(tz).hour


def utente_da_servire(utente: dict, adesso_utc: datetime) -> bool:
    """True se per questo utente è ORA (le 06:00 locali).

    Gli argomenti sono fissi (uguali per tutti): basta essere iscritti con un
    timezone valido. L'unico requisito è l'ora locale di consegna.
    """
    return ora_locale_utente(utente, adesso_utc) == config.ORA_CONSEGNA_LOCALE


def assicura_digest(adesso_utc: datetime) -> dict:
    """Ritorna il digest madre di oggi: lo riusa se esiste, altrimenti lo genera.

    GENERA (1 chiamata Gemini) solo al primo run utile del giorno; poi lo salva e
    i run successivi (altri fusi) lo riusano. Degrada con grazia in caso di errori.
    """
    esistente = db.get_digest_oggi()
    if esistente and esistente.get("contenuto"):
        print("[main] digest di oggi già presente — riuso (no chiamata AI).")
        return esistente["contenuto"]

    print("[main] primo run del giorno: genero il digest madre (1 chiamata Gemini).")
    per_argomento = reddit_scraper.raccogli_per_argomenti()
    digest = ai_engine.genera_digest_madre(per_argomento)
    try:
        db.salva_digest_oggi(digest)
    except Exception as e:
        # Se il salvataggio fallisce, serviamo comunque il digest in memoria oggi.
        print(f"[main] ATTENZIONE: salvataggio digest fallito ({e}); uso in memoria.")
    return digest


async def elabora_utente(utente: dict, digest: dict, bot: Bot) -> None:
    """Compone e invia il brief a UN utente (argomenti fissi). Solleva: il
    chiamante cattura per utente."""
    id_tg = utente["id_telegram"]
    testo = telegram_delivery.componi_brief(digest)
    await telegram_delivery.consegna_brief(id_tg, testo, bot=bot)
    print(f"[main] utente {id_tg}: brief consegnato.")


async def run() -> None:
    adesso_utc = datetime.now(timezone.utc)
    print(f"[main] run cron @ {adesso_utc.isoformat()} (UTC hour={adesso_utc.hour})")

    try:
        utenti = db.utenti_attivi()
    except RuntimeError as e:
        print(f"[main] DB non disponibile: {e}")
        return

    da_servire = [u for u in utenti if utente_da_servire(u, adesso_utc)]
    if not da_servire:
        print("[main] nessun utente alle 06:00 locali in questo run. Esco.")
        return

    print(f"[main] {len(da_servire)} utenti da servire.")

    # Digest madre: generato 1 volta/giorno, poi riusato.
    digest = assicura_digest(adesso_utc)

    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
    try:
        for utente in da_servire:
            try:
                await elabora_utente(utente, digest, bot)
            except Exception as e:
                print(f"[main] ERRORE utente {utente.get('id_telegram')}: {e}")
    finally:
        try:
            await bot.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(run())
