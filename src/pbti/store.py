"""Storage back-ends shared by every evaluated pipeline (so persistence costs are identical).

Three generic structures:
  blobs   (namespace, digest) -> bytes      content-addressed, write-once (raw / quarantine)
  append  (table, seq)        -> row        append-only logs (receipts, evidence, bronze, ledger, ...)
  kv      (table, key)        -> row        mutable materialized views (slots, silver, derived)

MemoryStore keeps everything in Python containers (used by the virtual-time experiments).
SQLiteStore persists with WAL journaling and explicit group commit (used by wall-clock
experiments); `flush()` is the durability point and is what latency measurements wait for.
Immutability of blobs is a *logical* property here (the code never updates a blob); in a
deployment it would be enforced by WORM/object-lock storage. The auditor detects violations.
"""
from __future__ import annotations

import os
import sqlite3
from typing import Any, Iterator, Optional

from .canonical import canonical_bytes


class MemoryStore:
    def __init__(self):
        self.blobs: dict[tuple[str, str], bytes] = {}
        self.logs: dict[str, list[Any]] = {}
        self.kv: dict[str, dict[Any, Any]] = {}
        self.bytes_written = 0

    def put_blob(self, ns: str, digest: str, data: bytes) -> bool:
        k = (ns, digest)
        if k in self.blobs:
            return False
        self.blobs[k] = data
        self.bytes_written += len(data) + len(digest)
        return True

    def get_blob(self, ns: str, digest: str) -> Optional[bytes]:
        return self.blobs.get((ns, digest))

    def append(self, table: str, row: Any, size_hint: int = 0) -> int:
        lst = self.logs.setdefault(table, [])
        lst.append(row)
        self.bytes_written += size_hint
        return len(lst) - 1

    def put(self, table: str, key: Any, row: Any, size_hint: int = 0) -> None:
        self.kv.setdefault(table, {})[key] = row
        self.bytes_written += size_hint

    def get(self, table: str, key: Any) -> Any:
        return self.kv.get(table, {}).get(key)

    def rows(self, table: str) -> list:
        return self.logs.get(table, [])

    def items(self, table: str) -> Iterator:
        return iter(self.kv.get(table, {}).items())

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass


class SQLiteStore(MemoryStore):
    """Write-behind persistence: in-memory working set plus durable SQLite copy (group commit)."""

    def __init__(self, path: str, synchronous: str = "NORMAL"):
        super().__init__()
        if os.path.exists(path):
            os.remove(path)
        self.db = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute(f"PRAGMA synchronous={synchronous}")
        self.db.execute("CREATE TABLE blobs(ns TEXT, d TEXT, data BLOB, PRIMARY KEY(ns,d))")
        self.db.execute("CREATE TABLE alog(tbl TEXT, seq INTEGER, data BLOB, PRIMARY KEY(tbl,seq))")
        self.db.execute("CREATE TABLE kv(tbl TEXT, k TEXT, data BLOB, PRIMARY KEY(tbl,k))")
        self._pb: list = []
        self._pa: list = []
        self._pk: list = []
        self.path = path

    @staticmethod
    def _ser(row: Any) -> bytes:
        if isinstance(row, (bytes, bytearray)):
            return bytes(row)
        return canonical_bytes(row) if isinstance(row, (dict, list, str, int, float)) else repr(row).encode()

    def put_blob(self, ns, digest, data):
        new = super().put_blob(ns, digest, data)
        if new:
            self._pb.append((ns, digest, data))
        return new

    def append(self, table, row, size_hint=0):
        i = super().append(table, row, size_hint)
        self._pa.append((table, i, self._ser(row)))
        return i

    def put(self, table, key, row, size_hint=0):
        super().put(table, key, row, size_hint)
        self._pk.append((table, repr(key), self._ser(row)))

    def flush(self):
        if not (self._pb or self._pa or self._pk):
            return
        cur = self.db.cursor()
        cur.execute("BEGIN")
        if self._pb:
            cur.executemany("INSERT OR IGNORE INTO blobs VALUES (?,?,?)", self._pb)
        if self._pa:
            cur.executemany("INSERT INTO alog VALUES (?,?,?)", self._pa)
        if self._pk:
            cur.executemany("INSERT OR REPLACE INTO kv VALUES (?,?,?)", self._pk)
        cur.execute("COMMIT")
        self._pb.clear(); self._pa.clear(); self._pk.clear()

    def db_bytes(self) -> int:
        self.flush()
        self.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        return os.path.getsize(self.path)

    def close(self):
        try:
            self.flush()
            self.db.close()
        except Exception:  # noqa: BLE001
            pass
