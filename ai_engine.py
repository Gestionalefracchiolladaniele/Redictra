# -*- coding: utf-8 -*-
"""
Redictra — Motore AI (Gemini Flash Lite).

UNA sola chiamata Gemini al giorno per TUTTI: genera il "DIGEST MADRE", cioè i
SEGNALI DI MERCATO per OGNI argomento AI, estratti dalla voce reale di Reddit
(post + commenti). Il digest si salva e i vari fusi orari lo riusano (vedi main.py)
→ il costo non cresce col numero di utenti.

Segnali (ADATTIVI, non configurabili): pain / request / momentum / debate / gap.
Per ogni argomento appaiono SOLO i segnali che quel giorno esistono davvero.
Se un argomento non ha nulla di concreto/nuovo → lo si dichiara onestamente
("oggi se ne parla ma niente di rilevante"), MAI inventare.

Regole di prodotto fondamentali:
  - Output in INGLESE (commenti del codice in italiano).
  - MAI citare un commento/utente Reddit verbatim né salvare autori: si riporta
    solo un UMORE AGGREGATO ("the community is split", "many complain…"). È la
    scelta che ci tiene puliti legalmente (analisi originale, non ripubblicazione).
  - Parsare sempre il JSON con json.loads (mai match su stringa grezza).
"""

import json
from typing import Optional

from google import genai
from google.genai import types

import config

# Client unico (legge la chiave da config). Se manca, le chiamate reali falliranno
# in modo esplicito: lo segnaliamo subito senza sollevare all'import.
if config.manca(config.GEMINI_API_KEY):
    print("[ai_engine] ATTENZIONE: GEMINI_API_KEY non configurata (vedi SETUP_TODO.md).")

_client: Optional[genai.Client] = None


def client() -> genai.Client:
    """Client Gemini lazy-singleton."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


# ============================================================================
# Helpers
# ============================================================================
def _compatta_post(post: list[dict], max_post: int = 6) -> str:
    """Compatta i post di un argomento per il prompt.

    Include i commenti SOLO se presenti (modalità API). In modalità RSS i commenti
    sono assenti → si usano titolo+estratto (cosa la community posta e vota oggi è
    comunque un segnale di mercato valido).
    """
    righe = []
    for i, p in enumerate(post[:max_post], 1):
        commenti = " | ".join(p.get("commenti", [])[:6])
        riga = (
            f"  POST {i} [r/{p['subreddit']}]\n"
            f"    title: {p.get('titolo', '')}\n"
            f"    body: {p.get('testo', '')[:300]}"
        )
        if commenti:
            riga += f"\n    top comments (the community's voice): {commenti[:1200]}"
        righe.append(riga)
    return "\n".join(righe) if righe else "  (no posts today)"


def _blocco_argomenti(per_argomento: dict[str, list[dict]]) -> str:
    """Compone il blocco con TUTTI gli argomenti e i loro post per il prompt."""
    blocchi = []
    for chiave, meta in config.ARGOMENTI.items():
        post = per_argomento.get(chiave, [])
        blocchi.append(
            f"### TOPIC: {chiave} ({meta['label']})\n"
            f"{_compatta_post(post)}"
        )
    return "\n\n".join(blocchi)


def _estrai_json(testo: str) -> Optional[dict]:
    """Estrae e parsa JSON dal testo (ripulendo eventuali ``` fence)."""
    t = (testo or "").strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1] if "```" in t else t
        if t.startswith("json"):
            t = t[4:]
        t = t.strip("` \n")
    try:
        return json.loads(t)
    except (json.JSONDecodeError, ValueError):
        return None


# ============================================================================
# DIGEST MADRE — 1 chiamata Gemini/giorno per TUTTI
# ============================================================================
def _system_prompt() -> str:
    segnali_desc = "\n".join(
        f'  - "{k}": {v["desc"]}' for k, v in config.SEGNALI.items()
    )
    return (
        "You are a market-intelligence analyst for AI founders. You read what the "
        "Reddit community posts and discusses (top posts, and comments when provided) "
        "and distill MARKET SIGNALS a founder can act on. You do NOT summarize news "
        "headlines — you surface what people actually want, hate, ask for, argue "
        "about, and can't find. What the community chooses to post and upvote today "
        "is itself a market signal.\n\n"
        "For each topic, classify what you see into these signal types (include a "
        "signal ONLY if it genuinely shows up today — never force one):\n"
        f"{segnali_desc}\n\n"
        "HARD RULES:\n"
        "- Report only AGGREGATE sentiment ('the community is split', 'many devs "
        "complain'). NEVER quote a specific comment or name any user.\n"
        "- Each signal 'text' is ONE tight sentence: the insight + why it matters, "
        "fused, no labels like 'why it matters'. Factual, no personal opinion/verdict.\n"
        "- If a topic has nothing concrete or new today, return its signals as an "
        "empty list and set 'quiet' true with a one-line honest note "
        "(e.g. 'People are still discussing X, but nothing concrete or new today').\n"
        "- Output STRICT JSON only, English, no prose outside the JSON."
    )


def _user_prompt(per_argomento: dict[str, list[dict]]) -> str:
    chiavi = list(config.ARGOMENTI.keys())
    tipi = list(config.SEGNALI.keys())
    return (
        "Here are today's top Reddit posts and comments, grouped by topic:\n\n"
        f"{_blocco_argomenti(per_argomento)}\n\n"
        "Produce a JSON object with this exact shape:\n"
        "{\n"
        '  "topics": {\n'
        '    "<topic_key>": {\n'
        '      "quiet": <bool>,\n'
        '      "quiet_note": "<one line, only if quiet=true, else empty>",\n'
        '      "signals": [\n'
        '        {"type": "<one of: ' + " | ".join(tipi) + '>", '
        '"text": "<one tight sentence>"}\n'
        "      ]\n"
        "    }\n"
        "  }\n"
        "}\n\n"
        f"Include EVERY topic key exactly once: {chiavi}.\n"
        "For each topic include 0-3 of the strongest signals (most actionable "
        "first). Use empty signals + quiet=true when there is nothing real today."
    )


def genera_digest_madre(per_argomento: dict[str, list[dict]]) -> dict:
    """UNA chiamata Gemini → digest madre (segnali per ogni argomento).

    Ritorna un dict: {"topics": {chiave: {quiet, quiet_note, signals[]}}}.
    In caso di parsing fallito ritorna una struttura "quiet" per ogni argomento
    (degrada con grazia: nessun crash, brief onesto "niente di rilevante").
    """
    import time
    cfg = types.GenerateContentConfig(
        system_instruction=_system_prompt(),
        response_mime_type="application/json",
        temperature=0.4,
    )
    contenuti = _user_prompt(per_argomento)
    # Prova ogni modello della lista (flash → flash-lite), 2 tentativi ciascuno con
    # attesa crescente. Gestisce 503 "high demand" / 429 rate-limit.
    response = None
    for modello in config.MODELLI_DIGEST:
        for tentativo in range(2):
            try:
                response = client().models.generate_content(
                    model=modello, contents=contenuti, config=cfg,
                )
                break
            except Exception as e:
                attesa = 5 * (tentativo + 1)
                print(f"[ai_engine] {modello} errore (try {tentativo+1}/2): "
                      f"{str(e)[:70]} - retry {attesa}s")
                time.sleep(attesa)
        if response is not None:
            print(f"[ai_engine] digest generato con {modello}")
            break
    dati = _estrai_json(getattr(response, "text", "") or "") if response else None
    if isinstance(dati, dict) and isinstance(dati.get("topics"), dict):
        return dati
    # Degrado: digest "vuoto onesto" per ogni argomento.
    return {
        "topics": {
            k: {"quiet": True,
                "quiet_note": "No clear market signal surfaced today.",
                "signals": []}
            for k in config.ARGOMENTI
        }
    }
