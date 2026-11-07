"""Generate normalized vector embeddings for RAG knowledge chunks."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAG_DATA_DIRECTORY = PROJECT_ROOT / "data" / "rag"

CHUNKS_FILE = (
    RAG_DATA_DIRECTORY / "knowledge_chunks.csv"
)

EMBEDDINGS_FILE = (
    RAG_DATA_DIRECTORY / "knowledge_embeddings.npy"
)

METADATA_FILE = (
    RAG_DATA_DIRECTORY / "embedding_metadata.json"
)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

TEXT_COLUMN = "searchable_text"

BATCH_SIZE = 32


def calculate_file_sha256(file_path):
    """Calculate a SHA-256 checksum for a file."""

    sha256_hash = hashlib.sha256()

    with file_path.open("rb") as input_file:
        for file_block in iter(
            lambda: input_file.read(1024 * 1024),
            b"",
        ):
            sha256_hash.update(file_block)

    return sha256_hash.hexdigest()


def load_knowledge_chunks():
    """Load and validate the searchable knowledge chunks."""

    if not CHUNKS_FILE.exists():
        raise FileNotFoundError(
            "Knowledge chunks file does not exist: "
            f"{CHUNKS_FILE}. Run "
            "`python -m src.rag.build_knowledge_base` first."
        )

    chunk_data = pd.read_csv(CHUNKS_FILE)

    required_columns = [
        "chunk_id",
        "source_file",
        "section_path",
        TEXT_COLUMN,
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in chunk_data.columns
    ]

    if missing_columns:
        raise ValueError(
            "Knowledge chunks are missing columns: "
            + ", ".join(missing_columns)
        )

    if chunk_data.empty:
        raise ValueError(
            "The knowledge chunks file contains no records."
        )

    missing_values = int(
        chunk_data[required_columns]
        .isna()
        .sum()
        .sum()
    )

    if missing_values:
        raise ValueError(
            "Knowledge chunks contain "
            f"{missing_values} missing required values."
        )

    duplicate_chunk_ids = int(
        chunk_data["chunk_id"].duplicated().sum()
    )

    if duplicate_chunk_ids:
        raise ValueError(
            "Knowledge chunks contain "
            f"{duplicate_chunk_ids} duplicate chunk IDs."
        )

    empty_searchable_text = int(
        chunk_data[TEXT_COLUMN]
        .astype(str)
        .str.strip()
        .eq("")
        .sum()
    )

    if empty_searchable_text:
        raise ValueError(
            "Knowledge chunks contain "
            f"{empty_searchable_text} empty searchable values."
        )

    return chunk_data


def generate_embeddings(model, searchable_text):
    """Convert searchable text into normalized embedding vectors."""

    embeddings = model.encode(
        searchable_text,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    embeddings = np.asarray(
        embeddings,
        dtype=np.float32,
    )

    return embeddings


def validate_embeddings(embeddings, chunk_data):
    """Validate embedding count, shape, values, and normalization."""

    if embeddings.ndim != 2:
        raise ValueError(
            "Expected a two-dimensional embedding matrix, "
            f"but received shape {embeddings.shape}."
        )

    if embeddings.shape[0] != len(chunk_data):
        raise ValueError(
            "Embedding count does not match knowledge chunk count. "
            f"Embeddings: {embeddings.shape[0]:,}; "
            f"chunks: {len(chunk_data):,}."
        )

    if embeddings.shape[1] <= 0:
        raise ValueError(
            "The embedding dimension must be greater than zero."
        )

    if not np.isfinite(embeddings).all():
        raise ValueError(
            "Embedding matrix contains NaN or infinite values."
        )

    vector_norms = np.linalg.norm(
        embeddings,
        axis=1,
    )

    zero_length_vectors = int(
        np.isclose(vector_norms, 0).sum()
    )

    if zero_length_vectors:
        raise ValueError(
            f"Embedding matrix contains {zero_length_vectors} "
            "zero-length vectors."
        )

    normalized_vectors = np.isclose(
        vector_norms,
        1.0,
        atol=1e-4,
    )

    unnormalized_count = int(
        (~normalized_vectors).sum()
    )

    if unnormalized_count:
        raise ValueError(
            f"Embedding matrix contains {unnormalized_count} "
            "vectors that are not normalized."
        )


def save_embedding_metadata(
    chunk_data,
    embeddings,
    model,
):
    """Save metadata required to validate and reproduce embeddings."""

    metadata = {
        "embedding_model": MODEL_NAME,
        "embedding_dimension": int(
            embeddings.shape[1]
        ),
        "chunk_count": int(
            embeddings.shape[0]
        ),
        "batch_size": BATCH_SIZE,
        "normalized_embeddings": True,
        "text_column": TEXT_COLUMN,
        "sentence_transformers_version": (
            getattr(
                model,
                "__version__",
                None,
            )
        ),
        "generated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "knowledge_chunks_file": str(
            CHUNKS_FILE.relative_to(PROJECT_ROOT)
        ),
        "knowledge_chunks_sha256": (
            calculate_file_sha256(CHUNKS_FILE)
        ),
        "embeddings_file": str(
            EMBEDDINGS_FILE.relative_to(PROJECT_ROOT)
        ),
        "embeddings_sha256": (
            calculate_file_sha256(EMBEDDINGS_FILE)
        ),
        "source_documents": sorted(
            chunk_data["source_file"]
            .dropna()
            .unique()
            .tolist()
        ),
    }

    with METADATA_FILE.open(
        "w",
        encoding="utf-8",
    ) as metadata_file:
        json.dump(
            metadata,
            metadata_file,
            indent=2,
        )


def main():
    """Generate, validate, and save RAG embeddings."""

    print("RAG EMBEDDING GENERATION")
    print("-" * 72)

    chunk_data = load_knowledge_chunks()

    print(
        f"Knowledge chunks loaded: "
        f"{len(chunk_data):,}"
    )

    print(f"Embedding model: {MODEL_NAME}")
    print(
        "The model may be downloaded during the first run."
    )

    model = SentenceTransformer(MODEL_NAME)

    searchable_text = (
        chunk_data[TEXT_COLUMN]
        .astype(str)
        .tolist()
    )

    embeddings = generate_embeddings(
        model,
        searchable_text,
    )

    validate_embeddings(
        embeddings,
        chunk_data,
    )

    RAG_DATA_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    np.save(
        EMBEDDINGS_FILE,
        embeddings,
        allow_pickle=False,
    )

    save_embedding_metadata(
        chunk_data,
        embeddings,
        model,
    )

    print("-" * 72)
    print(
        f"Embedding rows: "
        f"{embeddings.shape[0]:,}"
    )
    print(
        f"Embedding dimensions: "
        f"{embeddings.shape[1]:,}"
    )
    print(
        f"Embedding data type: "
        f"{embeddings.dtype}"
    )
    print(
        "Normalized embeddings: Yes"
    )
    print(
        f"Embeddings file: "
        f"{EMBEDDINGS_FILE}"
    )
    print(
        f"Metadata file: "
        f"{METADATA_FILE}"
    )
    print(
        "RAG embedding generation completed successfully."
    )


if __name__ == "__main__":
    main()