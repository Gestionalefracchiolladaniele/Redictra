# -*- coding: utf-8 -*-
"""
Redictra — Helper di accesso a Supabase.

Due tabelle soltanto (lead magnet minimalista):
  - `utenti`: id_telegram (PK), argomenti scelti, timezone, stato. Niente piani,
    niente trial, niente voce, niente archivio.
  - `digest_giornaliero`: cache del DIGEST MADRE del giorno (1 riga/giorno). Lo
    genera il primo run utile della giornata; tutti gli altri fusi lo riusano.

Il backend usa la SERVICE ROLE KEY → bypassa RLS. Mai esporla al client.
"""

from datetime import date, datetime
from typing import Optional

from supabase import create_client, Client

import config


def _client() -> Client:
    if config.manca(config.SUPABASE_URL) or config.manca(config.SUPABASE_SERVICE_ROLE_KEY):
        raise RuntimeError(
            "Credenziali Supabase mancanti: imposta SUPABASE_URL / "
            "SUPABASE_SERVICE_ROLE_KEY (vedi SETUP_TODO.md)."
        )
    return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_ROLE_KEY)


_supabase: Optional[Client] = None


def supabase() -> Client:
    global _supabase
    if _supabase is None:
        _supabase = _client()
    return _supabase


# ============================================================================
# UTENTI
# ============================================================================
def utenti_attivi() -> list[dict]:
    """Tutti gli utenti iscritti e attivi (ricevono il brief)."""
    resp = (
        supabase()
        .table("utenti")
        .select("*")
        .eq("attivo", True)
        .execute()
    )
    return resp.data or []


def get_utente(id_telegram: int) -> Optional[dict]:
    resp = (
        supabase().table("utenti").select("*").eq("id_telegram", id_telegram).limit(1).execute()
    )
    righe = resp.data or []
    return righe[0] if righe else None


def crea_o_aggiorna_utente(id_telegram: int, campi: Optional[dict] = None) -> dict:
    """Upsert dell'utente. Al primo /start crea la riga; poi aggiorna i campi."""
    record = {"id_telegram": id_telegram, "attivo": True}
    if campi:
        record.update(campi)
    if not get_utente(id_telegram):
        record.setdefault("created_at", datetime.utcnow().isoformat())
    supabase().table("utenti").upsert(record).execute()
    return get_utente(id_telegram)


def aggiorna_utente(id_telegram: int, campi: dict) -> None:
    supabase().table("utenti").update(campi).eq("id_telegram", id_telegram).execute()


def cancella_utente(id_telegram: int) -> None:
    """/stop — GDPR: cancella del tutto l'utente dal DB."""
    supabase().table("utenti").delete().eq("id_telegram", id_telegram).execute()


# ============================================================================
# DIGEST GIORNALIERO (cache del digest madre — 1 riga/giorno, condivisa)
# ============================================================================
def get_digest_oggi() -> Optional[dict]:
    """Ritorna il digest madre di OGGI (UTC) se già generato, altrimenti None."""
    oggi = date.today().isoformat()
    resp = (
        supabase()
        .table("digest_giornaliero")
        .select("*")
        .eq("data", oggi)
        .limit(1)
        .execute()
    )
    righe = resp.data or []
    return righe[0] if righe else None


def salva_digest_oggi(contenuto: dict) -> None:
    """Salva (upsert) il digest madre di oggi. Idempotente sulla data."""
    supabase().table("digest_giornaliero").upsert({
        "data": date.today().isoformat(),
        "contenuto": contenuto,
        "created_at": datetime.utcnow().isoformat(),
    }).execute()
