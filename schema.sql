-- ============================================================================
-- Redictra — Schema SQL (Supabase / PostgreSQL)
-- ----------------------------------------------------------------------------
-- 2 tabelle: utenti, digest_giornaliero.
-- RLS abilitato SENZA policy pubbliche: il backend accede con la SERVICE ROLE
-- KEY (che bypassa RLS). Nessun accesso anonimo/client.
-- Eseguire questo file una volta nell'SQL Editor di Supabase.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- TABELLA: utenti
-- PK = id_telegram (l'identità dell'utente nel bot, ottenuta al /start).
-- `argomenti` = chiavi degli argomenti AI scelti (vedi config.ARGOMENTI).
-- `timezone`  = IANA (es. 'Asia/Dubai'); serve a consegnare alle 06:00 LOCALI.
-- `attivo`    = false dopo /stop (in pratica la riga viene cancellata: GDPR).
-- Nessun dato personale oltre all'id Telegram volontariamente fornito col /start.
-- ----------------------------------------------------------------------------
create table if not exists utenti (
  id_telegram  bigint primary key,
  username     text   not null default '',             -- @username Telegram → per contattare il lead
  first_name   text   not null default '',             -- nome Telegram → per riconoscerlo
  argomenti    text[] not null default '{}',            -- chiavi argomenti scelti
  timezone     text   not null default 'UTC',           -- IANA, es. 'Asia/Dubai'
  attivo       boolean not null default true,
  created_at   timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- TABELLA: digest_giornaliero
-- Cache del DIGEST MADRE (1 chiamata Gemini/giorno, condiviso da tutti i fusi).
-- Il primo run utile del giorno lo genera e lo salva qui; gli altri run orari
-- (altri fusi) lo RIUSANO senza richiamare l'AI.
-- `contenuto` = JSON { "topics": { "<chiave>": { quiet, quiet_note, signals[] } } }.
-- ----------------------------------------------------------------------------
create table if not exists digest_giornaliero (
  data        date primary key default current_date,
  contenuto   jsonb not null,
  created_at  timestamptz not null default now()
);


-- ----------------------------------------------------------------------------
-- INDICI
-- ----------------------------------------------------------------------------
-- Il cron seleziona gli utenti attivi a ogni run orario.
create index if not exists idx_utenti_attivo on utenti (attivo) where attivo;


-- ----------------------------------------------------------------------------
-- RLS: abilitato ovunque, NESSUNA policy pubblica.
-- Il backend usa la SERVICE ROLE KEY → bypassa RLS. I client anonimi non leggono nulla.
-- ----------------------------------------------------------------------------
alter table utenti              enable row level security;
alter table digest_giornaliero  enable row level security;

-- (Volutamente NESSUNA policy: RLS senza policy = deny-all per chi non è service_role.)
