import copy
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

import asyncpg


@dataclass
class InsertOneResult:
    inserted_id: Any


@dataclass
class UpdateResult:
    matched_count: int
    modified_count: int
    upserted_id: Optional[Any] = None


@dataclass
class DeleteResult:
    deleted_count: int


def _safe_identifier(value: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_]+", "_", value)
    return clean.lower().strip("_") or "idx"


def _get_doc_value(doc: Dict[str, Any], key: str) -> Any:
    return doc.get(key)


def _matches_condition(doc_value: Any, condition: Any) -> bool:
    if isinstance(condition, dict) and any(k.startswith("$") for k in condition.keys()):
        for op, operand in condition.items():
            if op == "$in":
                if isinstance(doc_value, list):
                    if not any(item in operand for item in doc_value):
                        return False
                elif doc_value not in operand:
                    return False
            elif op == "$ne":
                if doc_value == operand:
                    return False
            elif op == "$lt":
                if doc_value is None or not (doc_value < operand):
                    return False
            elif op == "$regex":
                options = condition.get("$options", "")
                flags = re.IGNORECASE if "i" in options else 0
                pattern = re.compile(operand, flags)
                if not isinstance(doc_value, str) or not pattern.search(doc_value):
                    return False
            elif op == "$options":
                continue
            else:
                return False
        return True

    if isinstance(doc_value, list) and not isinstance(condition, list):
        return condition in doc_value
    return doc_value == condition


def _matches_query(doc: Dict[str, Any], query: Optional[Dict[str, Any]]) -> bool:
    if not query:
        return True

    for key, value in query.items():
        if key == "$or":
            if not isinstance(value, list) or not any(_matches_query(doc, subquery) for subquery in value):
                return False
            continue

        if key.startswith("$"):
            return False

        doc_value = _get_doc_value(doc, key)
        if not _matches_condition(doc_value, value):
            return False

    return True


def _apply_projection(doc: Dict[str, Any], projection: Optional[Dict[str, int]]) -> Dict[str, Any]:
    if not projection:
        return copy.deepcopy(doc)

    include_fields = [k for k, v in projection.items() if v and k != "_id"]
    exclude_fields = [k for k, v in projection.items() if not v]

    if include_fields:
        projected = {k: copy.deepcopy(doc[k]) for k in include_fields if k in doc}
        if projection.get("_id", 1) and "_id" in doc:
            projected["_id"] = copy.deepcopy(doc["_id"])
        return projected

    projected = copy.deepcopy(doc)
    for field in exclude_fields:
        projected.pop(field, None)
    return projected


def _apply_update(doc: Dict[str, Any], update_doc: Dict[str, Any]) -> Dict[str, Any]:
    updated = copy.deepcopy(doc)

    for op, payload in update_doc.items():
        if op == "$set":
            for key, value in payload.items():
                updated[key] = value
        elif op == "$inc":
            for key, value in payload.items():
                current = updated.get(key, 0)
                updated[key] = current + value
        elif op == "$pull":
            for key, value in payload.items():
                arr = updated.get(key, [])
                if isinstance(arr, list):
                    updated[key] = [item for item in arr if item != value]
        else:
            # Replacement-style update fallback
            updated = copy.deepcopy(update_doc)
            break

    return updated


def _extract_upsert_seed(query: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    seed: Dict[str, Any] = {}
    if not query:
        return seed

    for key, value in query.items():
        if key.startswith("$"):
            continue
        if isinstance(value, dict):
            continue
        seed[key] = value
    return seed


class PGCursor:
    def __init__(self, docs: List[Dict[str, Any]]):
        self._docs = docs
        self._limit: Optional[int] = None

    def sort(self, key: str, direction: int):
        reverse = direction < 0
        self._docs.sort(
            key=lambda d: (d.get(key) is None, d.get(key)),
            reverse=reverse,
        )
        return self

    def limit(self, value: int):
        self._limit = max(0, int(value))
        return self

    async def to_list(self, length: int):
        docs = self._docs
        if self._limit is not None:
            docs = docs[: self._limit]
        docs = docs[: max(0, int(length))]
        return [copy.deepcopy(d) for d in docs]


class PGCollection:
    def __init__(self, db: "PGDatabase", name: str):
        self.db = db
        self.name = name

    async def _load_rows(self) -> List[asyncpg.Record]:
        await self.db._ensure_schema()
        return await self.db.pool.fetch(
            "SELECT id, data FROM app_documents WHERE collection = $1",
            self.name,
        )

    async def _matching_rows(self, query: Optional[Dict[str, Any]]) -> List[asyncpg.Record]:
        rows = await self._load_rows()
        return [row for row in rows if _matches_query(row["data"], query)]

    async def create_index(self, keys: Any, unique: bool = False):
        await self.db._ensure_schema()
        if isinstance(keys, str):
            fields = [keys]
        elif isinstance(keys, Iterable):
            fields = []
            for item in keys:
                if isinstance(item, tuple):
                    fields.append(item[0])
                else:
                    fields.append(str(item))
        else:
            return

        if not fields:
            return

        idx_name = _safe_identifier(f"idx_{self.name}_{'_'.join(fields)}_{'uniq' if unique else 'idx'}")
        field_expr = ", ".join([f"(data ->> '{field}')" for field in fields])
        uniq = "UNIQUE " if unique else ""
        collection_name = self.name.replace("'", "''")
        sql = (
            f"CREATE {uniq}INDEX IF NOT EXISTS {idx_name} "
            f"ON app_documents ({field_expr}) WHERE collection = '{collection_name}'"
        )
        await self.db.pool.execute(sql)

    async def find_one(self, query: Optional[Dict[str, Any]] = None, projection: Optional[Dict[str, int]] = None):
        rows = await self._matching_rows(query)
        if not rows:
            return None
        return _apply_projection(rows[0]["data"], projection)

    def find(self, query: Optional[Dict[str, Any]] = None, projection: Optional[Dict[str, int]] = None):
        return PGFindOperation(self, query, projection)

    async def insert_one(self, document: Dict[str, Any]):
        await self.db._ensure_schema()
        inserted_id = await self.db.pool.fetchval(
            "INSERT INTO app_documents(collection, data) VALUES($1, $2::jsonb) RETURNING id",
            self.name,
            document,
        )
        return InsertOneResult(inserted_id=inserted_id)

    async def insert_many(self, documents: List[Dict[str, Any]]):
        await self.db._ensure_schema()
        async with self.db.pool.acquire() as conn:
            async with conn.transaction():
                for document in documents:
                    await conn.execute(
                        "INSERT INTO app_documents(collection, data) VALUES($1, $2::jsonb)",
                        self.name,
                        document,
                    )

    async def update_one(self, query: Dict[str, Any], update_doc: Dict[str, Any], upsert: bool = False):
        rows = await self._matching_rows(query)
        if not rows:
            if not upsert:
                return UpdateResult(matched_count=0, modified_count=0)
            new_doc = _extract_upsert_seed(query)
            new_doc = _apply_update(new_doc, update_doc)
            result = await self.insert_one(new_doc)
            return UpdateResult(matched_count=0, modified_count=0, upserted_id=result.inserted_id)

        row = rows[0]
        updated = _apply_update(row["data"], update_doc)
        await self.db.pool.execute(
            "UPDATE app_documents SET data = $1::jsonb WHERE id = $2",
            updated,
            row["id"],
        )
        return UpdateResult(matched_count=1, modified_count=1)

    async def update_many(self, query: Dict[str, Any], update_doc: Dict[str, Any]):
        rows = await self._matching_rows(query)
        if not rows:
            return UpdateResult(matched_count=0, modified_count=0)
        async with self.db.pool.acquire() as conn:
            async with conn.transaction():
                for row in rows:
                    updated = _apply_update(row["data"], update_doc)
                    await conn.execute(
                        "UPDATE app_documents SET data = $1::jsonb WHERE id = $2",
                        updated,
                        row["id"],
                    )
        return UpdateResult(matched_count=len(rows), modified_count=len(rows))

    async def delete_one(self, query: Dict[str, Any]):
        rows = await self._matching_rows(query)
        if not rows:
            return DeleteResult(deleted_count=0)
        await self.db.pool.execute("DELETE FROM app_documents WHERE id = $1", rows[0]["id"])
        return DeleteResult(deleted_count=1)

    async def delete_many(self, query: Dict[str, Any]):
        rows = await self._matching_rows(query)
        if not rows:
            return DeleteResult(deleted_count=0)
        ids = [row["id"] for row in rows]
        await self.db.pool.execute("DELETE FROM app_documents WHERE id = ANY($1::bigint[])", ids)
        return DeleteResult(deleted_count=len(ids))

    async def count_documents(self, query: Optional[Dict[str, Any]] = None) -> int:
        rows = await self._matching_rows(query)
        return len(rows)


class PGFindOperation:
    def __init__(self, collection: PGCollection, query: Optional[Dict[str, Any]], projection: Optional[Dict[str, int]]):
        self.collection = collection
        self.query = query
        self.projection = projection
        self._sort: Optional[Tuple[str, int]] = None
        self._limit: Optional[int] = None

    def sort(self, key: str, direction: int):
        self._sort = (key, direction)
        return self

    def limit(self, value: int):
        self._limit = max(0, int(value))
        return self

    async def to_list(self, length: int):
        rows = await self.collection._matching_rows(self.query)
        docs = [_apply_projection(row["data"], self.projection) for row in rows]
        cursor = PGCursor(docs)
        if self._sort:
            cursor.sort(self._sort[0], self._sort[1])
        if self._limit is not None:
            cursor.limit(self._limit)
        return await cursor.to_list(length)


class PGDatabase:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None
        self._collections: Dict[str, PGCollection] = {}

    async def connect(self):
        if self.pool is None:
            self.pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=10)
            await self._ensure_schema()

    async def _ensure_schema(self):
        if self.pool is None:
            await self.connect()
        await self.pool.execute(
            """
            CREATE TABLE IF NOT EXISTS app_documents (
                id BIGSERIAL PRIMARY KEY,
                collection TEXT NOT NULL,
                data JSONB NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
        await self.pool.execute("CREATE INDEX IF NOT EXISTS idx_app_documents_collection ON app_documents (collection)")

    def __getattr__(self, item: str) -> PGCollection:
        if item.startswith("_"):
            raise AttributeError(item)
        if item not in self._collections:
            self._collections[item] = PGCollection(self, item)
        return self._collections[item]

    async def close(self):
        if self.pool is not None:
            await self.pool.close()
            self.pool = None
