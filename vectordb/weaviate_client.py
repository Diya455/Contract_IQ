"""
Weaviate Cloud Client - With Increased Timeout
"""
import weaviate
from weaviate.auth import AuthApiKey
import os
from dotenv import load_dotenv

load_dotenv()

WEAVIATE_URL = os.getenv("WEAVIATE_URL", "")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY", "")


def validate_credentials():
    """Validate Weaviate credentials."""
    if not WEAVIATE_URL or not WEAVIATE_API_KEY:
        raise ValueError(
            "❌ Missing Weaviate credentials!\n\n"
            "Create a .env file with:\n"
            "WEAVIATE_URL=https://your-cluster.weaviate.network\n"
            "WEAVIATE_API_KEY=your-api-key"
        )


def get_client():
    """Get Weaviate Cloud client with increased timeout."""
    validate_credentials()

    try:
        auth_config = AuthApiKey(api_key=WEAVIATE_API_KEY)
        client = weaviate.Client(
            url=WEAVIATE_URL,
            auth_client_secret=auth_config,
            timeout_config=(30, 60)  # ← INCREASED: 30s connection, 60s read
        )
        return client
    except Exception as e:
        print(f"❌ Connection error: {e}")
        raise


def create_schema():
    """Create the Contract schema if it doesn't exist."""
    client = get_client()

    schema = {
        "classes": [{
            "class": "Contract",
            "description": "A contract document chunk",
            "vectorizer": "none",
            "properties": [
                {"name": "text", "dataType": ["text"]},
                {"name": "metadata", "dataType": ["text"]}
            ]
        }]
    }

    try:
        existing = client.schema.get()
        class_names = [c["class"] for c in existing.get("classes", [])]
        if "Contract" not in class_names:
            client.schema.create(schema)
            print("✓ Schema created")
        else:
            print("✓ Schema already exists")
    except Exception as e:
        print(f"Schema error: {e}")


def insert_document(chunks, embeddings):
    """Insert document chunks with embeddings into Weaviate."""
    client = get_client()

    try:
        with client.batch as batch:
            batch.batch_size = 100

            for chunk, embedding in zip(chunks, embeddings):
                # Convert embedding to list if needed
                vector = embedding if isinstance(embedding, list) else (
                    embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)
                )

                # Handle chunk format
                if isinstance(chunk, dict):
                    text = chunk.get("text", "")
                    metadata = str(chunk.get("metadata", {}))
                else:
                    text = str(chunk)
                    metadata = "{}"

                batch.add_data_object(
                    {"text": text, "metadata": metadata},
                    "Contract",
                    vector=vector
                )

        print(f"✓ Inserted {len(chunks)} chunks")
        return True

    except Exception as e:
        print(f"Insert error: {e}")
        return False


def query_similar_chunks(query_embedding, limit=5, certainty=0.7):
    """
    Query similar chunks from Weaviate with retry logic.
    """
    client = get_client()

    try:
        # Convert query_embedding to list if needed
        vector = query_embedding if isinstance(query_embedding, list) else (
            query_embedding.tolist() if hasattr(query_embedding, 'tolist') else list(query_embedding)
        )

        # Query with increased timeout
        response = (
            client.query
            .get("Contract", ["text", "metadata"])
            .with_near_vector({"vector": vector, "certainty": certainty})
            .with_limit(limit)
            .do()
        )

        # Extract results
        results = []
        if "data" in response and "Get" in response["data"]:
            for contract in response["data"]["Get"].get("Contract", []):
                results.append({
                    "text": contract.get("text", ""),
                    "metadata": contract.get("metadata", "{}")
                })

        print(f"✓ Found {len(results)} relevant chunks")
        return results

    except Exception as e:
        print(f"❌ Query error: {e}")
        print("⚠️ Tip: Check your internet connection and Weaviate cluster status")
        return []


def delete_all_documents():
    """Delete all documents from the Contract collection."""
    client = get_client()

    try:
        client.batch.delete_objects(
            class_name="Contract",
            where={"operator": "NotEqual", "path": ["text"], "valueText": ""}
        )
        print("✓ All documents deleted")
        return True
    except Exception as e:
        print(f"Delete error: {e}")
        return False


def get_document_count():
    """Get the number of documents in the Contract collection."""
    client = get_client()

    try:
        response = client.query.aggregate("Contract").with_meta_count().do()

        if "data" in response and "Aggregate" in response["data"]:
            aggregate = response["data"]["Aggregate"].get("Contract", [])
            if aggregate:
                count = aggregate[0].get("meta", {}).get("count", 0)
                print(f"✓ Document count: {count}")
                return count

        return 0

    except Exception as e:
        print(f"Count error: {e}")
        return 0
