import json
import os
import sys

# Workaround for ChromaDB + Pydantic v1 on Python 3.14+
# Pydantic v1 cannot infer types from annotations on Python 3.14 due to PEP 649
# deferred evaluation. Patch the field inference to handle this gracefully.
if sys.version_info >= (3, 14):
    import pydantic.v1.fields as _pv1_fields
    _orig_set_default_and_type = _pv1_fields.ModelField._set_default_and_type

    def _patched_set_default_and_type(self):
        try:
            _orig_set_default_and_type(self)
        except _pv1_fields.errors_.ConfigError:
            if self.default is not None:
                self.type_ = type(self.default)
            else:
                self.type_ = type(None)
            self.outer_type_ = self.type_

    _pv1_fields.ModelField._set_default_and_type = _patched_set_default_and_type

import chromadb
from sentence_transformers import SentenceTransformer

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "maintenance_logs.json")
VECTORSTORE_PATH = os.path.join(os.path.dirname(__file__), "vectorstore")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "maintenance_logs"


def load_logs(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def chunk_log(log: dict) -> list[dict]:
    """Split a single maintenance log into meaningful semantic chunks."""
    log_id = log["log_id"]
    base_meta = {
        "log_id": log_id,
        "date": log["date"],
        "equipment_id": log["equipment_id"],
        "equipment_type": log["equipment_type"],
        "severity": log["severity"],
        "repair_time_hours": log["repair_time_hours"],
    }

    chunks = []

    # Chunk 1: Fault overview — what happened and on what equipment
    fault_text = (
        f"Equipment: {log['equipment_type']} ({log['equipment_id']}). "
        f"Date: {log['date']}. Severity: {log['severity']}. "
        f"Fault: {log['fault_description']}. "
        f"Symptoms: {'; '.join(log['symptoms'])}."
    )
    chunks.append({
        "id": f"{log_id}_fault",
        "text": fault_text,
        "metadata": {**base_meta, "chunk_type": "fault_overview"},
    })

    # Chunk 2: Diagnostic procedure
    diag_text = (
        f"Fault: {log['fault_description']} on {log['equipment_type']}. "
        f"Diagnostic steps performed: {'; '.join(log['diagnostic_steps'])}."
    )
    chunks.append({
        "id": f"{log_id}_diagnostic",
        "text": diag_text,
        "metadata": {**base_meta, "chunk_type": "diagnostic"},
    })

    # Chunk 3: Root cause and resolution
    resolution_text = (
        f"Fault: {log['fault_description']} on {log['equipment_type']}. "
        f"Root cause: {log['root_cause']}. "
        f"Resolution: {log['resolution']}. "
        f"Parts replaced: {', '.join(log['parts_replaced'])}. "
        f"Repair time: {log['repair_time_hours']} hours."
    )
    chunks.append({
        "id": f"{log_id}_resolution",
        "text": resolution_text,
        "metadata": {**base_meta, "chunk_type": "resolution"},
    })

    # Chunk 4: Engineer notes and lessons learned
    notes_text = (
        f"Engineer notes for {log['fault_description']} on "
        f"{log['equipment_type']} ({log['equipment_id']}): "
        f"{log['engineer_notes']}"
    )
    chunks.append({
        "id": f"{log_id}_notes",
        "text": notes_text,
        "metadata": {**base_meta, "chunk_type": "engineer_notes"},
    })

    return chunks


def ingest():
    print(f"Loading maintenance logs from {DATA_PATH}...")
    logs = load_logs(DATA_PATH)
    print(f"Loaded {len(logs)} logs.")

    # Chunk all logs
    all_chunks = []
    for log in logs:
        all_chunks.extend(chunk_log(log))
    print(f"Created {len(all_chunks)} chunks ({len(all_chunks) // len(logs)} per log).")

    # Load embedding model
    print(f"Loading embedding model: {EMBEDDING_MODEL}...")
    model = SentenceTransformer(EMBEDDING_MODEL)

    # Generate embeddings
    texts = [chunk["text"] for chunk in all_chunks]
    print("Generating embeddings...")
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)

    # Store in ChromaDB
    print(f"Storing in ChromaDB at {VECTORSTORE_PATH}...")
    client = chromadb.PersistentClient(path=VECTORSTORE_PATH)

    # Delete existing collection if it exists to allow re-ingestion
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "Heavy vehicle fleet maintenance logs"},
    )

    # ChromaDB has batch size limits, so insert in batches
    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i : i + batch_size]
        collection.add(
            ids=[chunk["id"] for chunk in batch],
            documents=[chunk["text"] for chunk in batch],
            embeddings=[embeddings[i + j].tolist() for j in range(len(batch))],
            metadatas=[chunk["metadata"] for chunk in batch],
        )

    print(f"Ingestion complete. {collection.count()} vectors stored in '{COLLECTION_NAME}' collection.")


if __name__ == "__main__":
    ingest()
