import time
import httpx
import weaviate
from weaviate.classes.config import Property, DataType

COLLECTION_NAME = "VendorContracts"
_schema_ready = False


# ─── HTTP health check ────────────────────────────────────────────────────────
def _is_weaviate_ready():
    try:
        resp = httpx.get("http://localhost:8080/v1/meta", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


# ─── Wait for Weaviate via HTTP ───────────────────────────────────────────────
def _wait_for_weaviate(max_wait=120):
    for i in range(0, max_wait, 2):
        if _is_weaviate_ready():
            print(f"Weaviate HTTP ready after ~{i}s")
            return True
        print(f"Waiting for Weaviate... ({i}s elapsed)")
        time.sleep(2)
    return False


# ─── Fresh client every time ──────────────────────────────────────────────────
def _new_client():
    return weaviate.connect_to_local(
        host="localhost",
        port=8080,
        grpc_port=50051,
        additional_config=weaviate.config.AdditionalConfig(
            timeout=weaviate.config.Timeout(init=30, query=60, insert=120)
        )
    )


# ─── Retry wrapper ────────────────────────────────────────────────────────────
def _with_retry(fn, max_attempts=10, delay=4):
    """
    Retries fn(client) on any transient Weaviate error.
    Re-checks HTTP health before each attempt to handle container restarts.
    """
    last_err = None
    for attempt in range(max_attempts):
        # Before each attempt, verify Weaviate is up via HTTP
        if not _is_weaviate_ready():
            print(f"Weaviate not reachable — waiting for it to come back... (attempt {attempt+1})")
            if not _wait_for_weaviate(max_wait=60):
                print("Weaviate still not reachable after 60s — skipping.")
                return None
            time.sleep(5)  # extra buffer after recovery

        client = None
        try:
            client = _new_client()
            result = fn(client)
            return result
        except Exception as e:
            last_err = e
            err = str(e).lower()
            is_transient = any(x in err for x in [
                "leader not found", "422", "disconnected", "server disconnected",
                "remoteprot", "consistency", "permission", "403", "500",
                "10053", "10054", "aborted", "winError", "startup",
                "connection", "timeout", "refused"
            ])
            if is_transient:
                print(f"Attempt {attempt+1}/{max_attempts} failed: {type(e).__name__} — retrying in {delay}s...")
                time.sleep(delay)
                continue
            raise  # non-transient — don't retry
        finally:
            try:
                if client:
                    client.close()
            except Exception:
                pass

    print(f"All {max_attempts} attempts failed. Last error: {last_err}")
    return None


# ─── Schema ───────────────────────────────────────────────────────────────────
def create_schema():
    global _schema_ready

    if _schema_ready:
        return

    ready = _wait_for_weaviate(max_wait=120)
    if not ready:
        print("Weaviate not reachable after 120s — schema skipped.")
        return

    print("HTTP ready. Waiting 6s for Raft leader to stabilize...")
    time.sleep(15)

    def _do_create_schema(client):
        existing = client.collections.list_all()
        if COLLECTION_NAME not in existing:
            client.collections.create(
                name=COLLECTION_NAME,
                vector_config=None,
                properties=[
                    Property(name="text",          data_type=DataType.TEXT),
                    Property(name="page_number",   data_type=DataType.INT),
                    Property(name="section_title", data_type=DataType.TEXT),
                ]
            )
        return True

    result = _with_retry(_do_create_schema, max_attempts=10, delay=4)
    if result:
        _schema_ready = True
        print("Weaviate schema ready.")
    else:
        print("Schema creation failed — will retry on first use.")


def _ensure_schema():
    global _schema_ready
    if not _schema_ready:
        create_schema()


# ─── Insert ───────────────────────────────────────────────────────────────────
def insert_document(chunk_text, embedding, metadata):
    _ensure_schema()

    def _do_insert(client):
        collection = client.collections.get(COLLECTION_NAME)
        collection.data.insert(
            properties={
                "text":          chunk_text,
                "page_number":   metadata.get("page_number"),
                "section_title": metadata.get("section_title"),
            },
            vector=embedding.tolist()
        )
        return True

    _with_retry(_do_insert, max_attempts=8, delay=4)


# ─── Query ────────────────────────────────────────────────────────────────────
def query_similar_chunks(query_embedding, top_k=5):
    _ensure_schema()

    def _do_query(client):
        collection = client.collections.get(COLLECTION_NAME)
        response = collection.query.near_vector(
            near_vector=query_embedding.tolist(),
            limit=top_k,
            return_properties=["text", "page_number", "section_title"]
        )
        return [obj.properties for obj in response.objects]

    result = _with_retry(_do_query, max_attempts=5, delay=2)
    return result if result is not None else []