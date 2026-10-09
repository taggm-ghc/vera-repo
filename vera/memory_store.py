"""Item #84 Path A: durable memory storage and recall (existing tables only, no DDL, no DELETE).

Stores only claims that passed the claim check and the write gate (vera/memory_gate.py) and whose cited source is
ALREADY in the corpus (else skipped as `source_not_in_corpus`). Privacy (#74): the question, any identity, session
id or preference is never written; the question is only a bound read parameter (and gate input) in memory, and
recall is the same for everyone. Writes use the write-only account (URL in the env var named by config
memory.store.db_url_wo_env), reads the read-only account (memory.store.db_url_ro_env); never the rw account.
Forgetting: TTL and recency decay at read time on claims.created_at; tombstone via claims.detailed_status. There is
no DELETE path here (deletes need R1 approval). Every error is logged host-free and never fails /ask.
"""
import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timezone

from vera.corpus_admission import SCHEMA, WoCorpusStore, canonical_url
from vera.memory_gate import SourceRef, check_memory_write, normalise_claim

logger = logging.getLogger("vera")

STAGE_FINAL = "final"
VERIFICATION_SUPPORTED = "supported"
SKIP_NOT_IN_CORPUS = "source_not_in_corpus"
SKIP_DUPLICATE = "duplicate"
SKIP_CAP = "cap_reached"
SKIP_DISABLED = "memory_disabled"
_WORD = re.compile(r"[A-Za-z0-9]{3,}")


def _sql(sql: str) -> str:
    return sql.replace("{S}", SCHEMA)


class RoMemoryReader:
    """Read-only lookups: recall, dedupe, source and answer resolution. hide_parameters keeps bound values
    (including the question) out of SQLAlchemy error text."""

    def __init__(self, engine, cfg: dict):
        self.engine, self.cfg = engine, cfg

    def _rows(self, sql: str, params: dict):
        from sqlalchemy import text
        with self.engine.connect() as c:
            return c.execute(text(_sql(sql)), params).fetchall()

    def query_terms(self, question: str) -> str:
        stop = {w.lower() for w in self.cfg["query_stopwords"]}
        short = int(self.cfg["min_query_word_len"])
        words = list(dict.fromkeys(w for w in (x.lower() for x in _WORD.findall(question or ""))
                                   if len(w) >= short and w not in stop))
        return " or ".join(words[: int(self.cfg["max_query_terms"])])

    def recall(self, question: str) -> list[dict]:
        q = self.query_terms(question)
        if not q:
            return []
        terms = q.split(" or ")
        rows = self._rows(
            "SELECT claim_text, created_at, title, url FROM ("
            "SELECT DISTINCT ON (c.claim_id) c.claim_text, c.created_at, s.provenance ->> 'title' AS title, "
            "COALESCE(s.provenance ->> 'url', cs.canonical_url) AS url, "
            "ts_rank(to_tsvector('english', c.claim_text), websearch_to_tsquery('english', :q)) "
            "* power(0.5, extract(epoch FROM now() - c.created_at) / 86400.0 / :hl) AS score "
            "FROM {S}.claims c JOIN {S}.answers a ON a.answer_id = c.answer_id "
            "JOIN LATERAL jsonb_array_elements_text(c.evidence_span_ids) AS sp(span_id) ON true "
            "JOIN {S}.evidence_spans e ON e.span_id = sp.span_id::bigint "
            "JOIN {S}.sources s ON s.source_id = e.source_id "
            "JOIN {S}.canonical_sources cs ON cs.canonical_source_id = s.canonical_source_id "
            "WHERE a.response_text = :qt AND c.detailed_status = :live "
            "AND c.created_at > now() - make_interval(days => :ttl) "
            "AND to_tsvector('english', c.claim_text) @@ websearch_to_tsquery('english', :q) "
            "AND ts_rank(to_tsvector('english', c.claim_text), websearch_to_tsquery('english', :q)) >= :floor "
            "AND (SELECT count(*) FROM unnest(CAST(:terms AS text[])) AS tm(w) "
            "WHERE to_tsvector('english', c.claim_text) @@ plainto_tsquery('english', tm.w)) >= :minterms "
            "ORDER BY c.claim_id) t ORDER BY score DESC LIMIT :k",
            {"qt": self.cfg["question_text"], "live": self.cfg["status_live"], "ttl": int(self.cfg["ttl_days"]),
             "q": q, "terms": terms, "minterms": int(self.cfg["min_matched_terms"]), "floor": float(self.cfg["min_rank"]), "hl": float(self.cfg["half_life_days"]), "k": int(self.cfg["recall_k"])})
        return [{"claim_text": r[0], "source_title": r[2] or "", "source_url": r[3] or "",
                 "saved_at": r[1].isoformat() if r[1] else ""} for r in rows]

    def source(self, canonical: str):
        """(source_id, content length) of an already-admitted source, or None."""
        rows = self._rows(
            "SELECT s.source_id, length(s.content) FROM {S}.sources s "
            "JOIN {S}.canonical_sources cs ON cs.canonical_source_id = s.canonical_source_id "
            "WHERE cs.canonical_url = :u ORDER BY s.version DESC LIMIT 1", {"u": canonical})
        return (rows[0][0], rows[0][1]) if rows else None

    def span(self, source_id: int, end: int):
        rows = self._rows("SELECT span_id FROM {S}.evidence_spans WHERE source_id = :s AND start_index = 0 "
                          "AND end_index = :e LIMIT 1", {"s": source_id, "e": end})
        return rows[0][0] if rows else None

    def answer(self):
        rows = self._rows("SELECT answer_id FROM {S}.answers WHERE response_text = :qt AND model = :m "
                          "ORDER BY answer_id LIMIT 1",
                          {"qt": self.cfg["question_text"], "m": self.cfg["gate_version"]})
        return rows[0][0] if rows else None

    def duplicate(self, claim_text: str, span_ids: list) -> bool:
        rows = self._rows("SELECT c.claim_id FROM {S}.claims c JOIN {S}.answers a ON a.answer_id = c.answer_id "
                          "WHERE a.response_text = :qt AND c.claim_text = :t AND c.detailed_status = :live "
                          "AND c.evidence_span_ids @> CAST(:e AS jsonb) LIMIT 1",
                          {"qt": self.cfg["question_text"], "t": claim_text, "live": self.cfg["status_live"],
                           "e": json.dumps(list(span_ids))})
        return bool(rows)


class WoMemoryStore(WoCorpusStore):
    """INSERT ... RETURNING in savepoints (helpers inherited from the corpus store). Only INSERT and the
    operator tombstone UPDATE; no DELETE."""

    def __init__(self, engine, cfg: dict):
        super().__init__(engine, cfg["question_text"])
        self.cfg = cfg

    def answer_id(self) -> int:
        with self._lock, self.engine.begin() as c:
            qid = self._one(c, "INSERT INTO {S}.questions (research_question) VALUES (:q) RETURNING question_id",
                            {"q": self.question_text})
            rid = self._one(c, "INSERT INTO {S}.runs (question_id, question) VALUES (:q, :t) RETURNING run_id",
                            {"q": qid, "t": self.question_text})
            return self._one(c, "INSERT INTO {S}.answers (run_id, stage, response_text, model) "
                                "VALUES (:r, :st, :t, :m) RETURNING answer_id",
                             {"r": rid, "st": STAGE_FINAL, "t": self.question_text, "m": self.cfg["gate_version"]})

    def span_id(self, source_id: int, end: int) -> int | None:
        with self.engine.begin() as c:
            return self._insert_new(c, "INSERT INTO {S}.evidence_spans (source_id, text, start_index, end_index) "
                                       "VALUES (:s, :t, 0, :e) RETURNING span_id",
                                    {"s": source_id, "t": self.cfg["span_text"], "e": end})

    def add_claim(self, answer_id: int, claim_text: str, span_ids: list) -> int:
        with self.engine.begin() as c:
            return self._one(c, "INSERT INTO {S}.claims (answer_id, claim_text, evidence_span_ids, "
                                "verification_status, detailed_status) "
                                "VALUES (:a, :t, CAST(:e AS jsonb), :v, :d) RETURNING claim_id",
                             {"a": answer_id, "t": claim_text, "e": json.dumps(list(span_ids)),
                              "v": VERIFICATION_SUPPORTED, "d": self.cfg["status_live"]})

    def tombstone(self, claim_id: int):
        """Operator use only (not called by the app)."""
        with self.engine.begin() as c:
            return self._one(c, "UPDATE {S}.claims SET detailed_status = :d WHERE claim_id = :id RETURNING claim_id",
                             {"d": self.cfg["status_tombstone"], "id": claim_id})


class MemoryService:
    def __init__(self, cfg: dict, gate_cfg, reader: RoMemoryReader | None, store: WoMemoryStore | None,
                 clock=time.time):
        self.cfg, self.gate_cfg, self.reader, self.store, self.clock = cfg, gate_cfg, reader, store, clock
        self._answer_id, self._day, self._day_n, self._lock = None, None, 0, threading.Lock()

    def recall(self, question: str) -> list[dict]:
        if self.reader is None:
            return []
        try:
            return self.reader.recall(question)
        except Exception as exc:  # noqa: BLE001  (memory never fails /ask)
            logger.warning("memory recall failed (%s)", type(exc).__name__)
            return []

    def _reserve(self) -> bool:
        """Check-and-increment the daily cap under one lock acquisition (released if the write is skipped)."""
        day = int(self.clock() // 86400)
        with self._lock:
            if self._day != day:
                self._day, self._day_n = day, 0
            if self._day_n >= int(self.cfg["max_writes_per_day"]):
                return False
            self._day_n += 1
            return True

    def _release(self):
        with self._lock:
            self._day_n = max(0, self._day_n - 1)

    def write_claims(self, records, sources, question: str) -> tuple[int, dict]:
        """(rows written, {skip reason: count}). Never raises."""
        skipped: dict = {}
        written = 0
        if self.reader is None or self.store is None:
            return 0, {SKIP_DISABLED: 1}
        try:
            for rec in records or ():
                if written >= int(self.cfg["max_writes_per_answer"]) or not self._reserve():
                    skipped[SKIP_CAP] = skipped.get(SKIP_CAP, 0) + 1
                    continue
                try:
                    reason = self._write_one(rec, sources, question)
                except Exception:
                    self._release()
                    raise
                if reason is None:
                    written += 1
                else:
                    self._release()
                    skipped[reason] = skipped.get(reason, 0) + 1
        except Exception as exc:  # noqa: BLE001
            skipped["error"] = type(exc).__name__
            logger.warning("memory write failed (%s)", type(exc).__name__)
        if skipped:
            logger.info("memory write skipped: %s", skipped)
        return written, skipped

    def _write_one(self, rec: dict, sources, question: str):
        cited = [sources[n - 1] for n in rec["citations"] if 1 <= n <= len(sources)]
        refs = [SourceRef(provider=s.get("provider") or "", licence_decision=s.get("licence_decision") or "",
                          identifier=s.get("identifier") or "", url=s.get("url") or "") for s in cited]
        res = check_memory_write(self.cfg["fact_type"], rec["sentence"], rec["verdict"], refs, question,
                                 self.gate_cfg)
        if not res.allowed:
            return res.reasons[0]
        text = normalise_claim(rec["sentence"], self.gate_cfg)
        spans = []  # one whole-abstract evidence span per distinct cited source
        for canon in dict.fromkeys(canonical_url(s) for s in cited):
            found = self.reader.source(canon)
            if found is None or not found[1]:
                return SKIP_NOT_IN_CORPUS
            source_id, length = found
            span = self.reader.span(source_id, length) or self.store.span_id(source_id, length) \
                or self.reader.span(source_id, length)
            if span is None:
                return "span_unavailable"
            spans.append(span)
        if self.reader.duplicate(text, spans):
            return SKIP_DUPLICATE
        if self._answer_id is None:
            self._answer_id = self.reader.answer() or self.store.answer_id()
        self.store.add_claim(self._answer_id, text, spans)
        return None


_SERVICE: dict = {}


def memory_from_env(block: dict | None, env=os.environ, engine_factory=None, gate_cfg=None):
    """The process-wide MemoryService, or None when memory is disabled or neither DB URL is set."""
    cfg = (block or {}).get("store")
    if not cfg or not cfg.get("enabled"):
        return None
    if "svc" not in _SERVICE:
        if engine_factory is None:
            from sqlalchemy import create_engine as engine_factory
        ro_url = (env.get(cfg["db_url_ro_env"]) or "").strip()
        wo_url = (env.get(cfg["db_url_wo_env"]) or "").strip()
        if not ro_url:
            return None
        if gate_cfg is None:
            from vera.memory_gate import gate_config_from_dict
            gate_cfg = gate_config_from_dict(block)
        kw = {"pool_pre_ping": True, "hide_parameters": True,
              "connect_args": {"connect_timeout": int(cfg["connect_timeout_s"]),
                               "options": f"-c statement_timeout={int(cfg['statement_timeout_ms'])}"}}
        reader = RoMemoryReader(engine_factory(ro_url, **kw), cfg)
        store = WoMemoryStore(engine_factory(wo_url, **kw), cfg) if wo_url else None
        _SERVICE["svc"] = MemoryService(cfg, gate_cfg, reader, store)
    return _SERVICE["svc"]


def load_memory_block(path=None) -> dict | None:
    from vera.memory_gate import CONFIG_KEY, CONFIG_PATH
    try:
        return json.loads(open(path or CONFIG_PATH).read()).get(CONFIG_KEY)
    except (OSError, ValueError):
        return None
