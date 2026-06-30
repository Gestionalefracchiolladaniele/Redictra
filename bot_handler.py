# -*- coding: utf-8 -*-
"""
Redictra — Bot interattivo Telegram (onboarding minimalista).

Esperienza (lead magnet, zero attrito):
  /start    → benvenuto → scegli TIMEZONE (lista di fusi comuni) → fatto.
              (Gli ARGOMENTI sono FISSI e curati, uguali per tutti: niente scelta,
               niente brief vuoto. È un brief editoriale, non un tool da configurare.)
  /timezone → cambia il fuso.
  /preview  → vedi subito un esempio del brief di oggi (se il digest è pronto).
  /stop     → cancella account e dati (GDPR).

Niente menu a livelli, niente scelta argomenti, niente voce, niente archivio, niente Stripe.
Esecuzione: `python bot_handler.py` (polling).
"""

from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

import config
import db
import telegram_delivery

# Fusi orari comuni offerti a bottoni (IANA → etichetta). Coprono il mondo reale
# senza dare all'utente 400 scelte. Chi vuole un fuso preciso lo si aggiunge qui.
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
# TASTIERE
# ============================================================================
def kb_fusi() -> InlineKeyboardMarkup:
    righe = [[InlineKeyboardButton(label, callback_data=f"tz:{iana}")]
             for iana, label in FUSI]
    return InlineKeyboardMarkup(righe)


def _riga_argomenti() -> str:
    """Riga leggibile coi 5 argomenti fissi (per il messaggio di benvenuto)."""
    return " · ".join(
        f"{meta['emoji']} {meta['label']}" for meta in config.ARGOMENTI.values()
    )


# ============================================================================
# /start
# ============================================================================
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    id_tg = update.effective_user.id
    u = update.effective_user

    # --- Accesso a invito: il codice arriva dal deep link /start CODICE ---
    if config.accesso_a_invito():
        codice = (context.args[0] if context.args else "").strip()
        utente_esistente = db.get_utente(id_tg)
        # Passa solo chi presenta il codice giusto, o chi è già iscritto.
        if codice != config.ACCESS_CODE and not utente_esistente:
            await update.message.reply_text(
                "🔒 Redictra is invite-only.\n\n"
                "You need an invite link to join. If you have one, open it again."
            )
            return

    # Salviamo username + nome (li dà Telegram, gratis) → per riconoscere/contattare i lead.
    db.crea_o_aggiorna_utente(id_tg, {
        "username": u.username or "",
        "first_name": u.first_name or "",
    })

    # Onboarding a zero attrito: niente scelta argomenti (sono fissi). Si va dritti
    # al fuso, l'unica cosa che serve davvero sapere per consegnare alle 6 locali.
    await update.message.reply_text(
        "👋 *Welcome to Redictra.*\n\n"
        "Every morning at *6 AM your time*, I read what people really say on Reddit "
        "about AI and send you the *market signals* that matter — what they want, "
        "hate, ask for, and can't find. For founders who have no time but want to "
        "know where the market is moving.\n\n"
        f"You'll get the pulse on: {_riga_argomenti()}.\n\n"
        "One thing only — where are you? I'll deliver at *6 AM your local time*:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb_fusi(),
    )


# ============================================================================
# Router bottoni
# ============================================================================
async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    id_tg = update.effective_user.id

    if data.startswith("tz:"):
        iana = data.split(":", 1)[1]
        try:
            ZoneInfo(iana)
        except Exception:
            await query.answer("Invalid timezone.", show_alert=True)
            return
        db.aggiorna_utente(id_tg, {"timezone": iana})
        await query.edit_message_text(
            "✅ *All set!*\n\nYou'll get your first AI market brief tomorrow at 6 AM "
            "your time. ☕\n\n"
            "• /preview — see today's brief now\n"
            "• /timezone — change your timezone\n"
            "• /stop — unsubscribe & delete your data",
            parse_mode=ParseMode.MARKDOWN,
        )


# ============================================================================
# /timezone — riapre la scelta fuso
# ============================================================================
async def cmd_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db.crea_o_aggiorna_utente(update.effective_user.id)
    await update.message.reply_text(
        "🌍 *Your timezone* — pick the closest one (delivery is 6 AM local):",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb_fusi(),
    )


# ============================================================================
# /preview — mostra subito il brief di oggi (se il digest è pronto)
# ============================================================================
async def cmd_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    id_tg = update.effective_user.id
    utente = db.get_utente(id_tg)
    if not utente:
        await update.message.reply_text("Start with /start first 🙂")
        return
    riga = db.get_digest_oggi()
    if not riga or not riga.get("contenuto"):
        await update.message.reply_text(
            "Today's brief isn't generated yet — it's built at the first 6 AM "
            "delivery around the world. Check back, or wait for tomorrow morning. ☕"
        )
        return
    testo = telegram_delivery.componi_brief(riga["contenuto"])
    await telegram_delivery.consegna_brief(id_tg, testo)


# ============================================================================
# /stop — GDPR
# ============================================================================
async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    db.cancella_utente(update.effective_user.id)
    await update.message.reply_text(
        "✅ You're unsubscribed and your data has been deleted. Come back anytime "
        "with /start. 👋"
    )


def main() -> None:
    if config.manca(config.TELEGRAM_BOT_TOKEN):
        raise RuntimeError("TELEGRAM_BOT_TOKEN mancante (vedi SETUP_TODO.md).")

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("timezone", cmd_timezone))
    app.add_handler(CommandHandler("preview", cmd_preview))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CallbackQueryHandler(on_button))

    print("[bot] Redictra bot in polling…")
    app.run_polling()


if __name__ == "__main__":
    # Python 3.12+ non crea più l'event loop implicito nel MainThread, mentre
    # python-telegram-bot lo assume con asyncio.get_event_loop(). Lo creiamo noi.
    import asyncio
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    main()
