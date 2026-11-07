"""Retrieve knowledge chunks using hybrid semantic and keyword search."""

import argparse
import hashlib
import json
import re
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

DEFAULT_TOP_K = 5
DEFAULT_MINIMUM_SCORE = 0.25

SEMANTIC_WEIGHT = 0.70
LEXICAL_WEIGHT = 0.30


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "for",
    "from",
    "had",
    "has",
    "have",
    "how",
    "i",
    "in",
    "into",
    "is",
    "it",
    "its",
    "may",
    "of",
    "on",
    "or",
    "our",
    "should",
    "that",
    "the",
    "their",
    "them",
    "these",
    "this",
    "to",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "will",
    "with",
}


TERM_ALIASES = {
    "segments": "cluster",
    "segment": "cluster",
    "segmentation": "cluster",
    "clusters": "cluster",
    "clustering": "cluster",
    "selected": "select",
    "selection": "select",
    "selecting": "select",
    "choose": "select",
    "choosing": "select",
    "chosen": "select",
    "recommendations": "recommendation",
    "recommended": "recommendation",
    "recommending": "recommendation",
    "customers": "customer",
    "transactions": "transaction",
    "balances": "balance",
    "products": "product",
    "scores": "score",
    "scoring": "score",
    "metrics": "metric",
    "evaluated": "evaluate",
    "evaluation": "evaluate",
    "evaluating": "evaluate",
}


def calculate_file_sha256(file_path):
    """Calculate the SHA-256 checksum for a file."""

    sha256_hash = hashlib.sha256()

    with file_path.open("rb") as input_file:
        for file_block in iter(
            lambda: input_file.read(1024 * 1024),
            b"",
        ):
            sha256_hash.update(file_block)

    return sha256_hash.hexdigest()


def normalize_search_terms(text):
    """Convert text into normalized terms for keyword matching."""

    raw_terms = re.findall(
        r"[a-zA-Z0-9]+",
        str(text).lower(),
    )

    normalized_terms = []

    for term in raw_terms:
        if term in STOPWORDS:
            continue

        normalized_term = TERM_ALIASES.get(
            term,
            term,
        )

        normalized_terms.append(normalized_term)

    return set(normalized_terms)


def calculate_overlap_score(
    query_terms,
    candidate_terms,
):
    """Calculate the proportion of query terms in candidate text."""

    if not query_terms:
        return 0.0

    matching_terms = (
        query_terms & candidate_terms
    )

    return len(matching_terms) / len(query_terms)


class KnowledgeRetriever:
    """Load the RAG index and retrieve relevant knowledge chunks."""

    def __init__(
        self,
        chunks_file=CHUNKS_FILE,
        embeddings_file=EMBEDDINGS_FILE,
        metadata_file=METADATA_FILE,
    ):
        self.chunks_file = Path(chunks_file)
        self.embeddings_file = Path(embeddings_file)
        self.metadata_file = Path(metadata_file)

        self.chunk_data = None
        self.embeddings = None
        self.metadata = None
        self.model = None

        self._load_index()

    def _validate_files_exist(self):
        """Verify that required RAG index files exist."""

        required_files = [
            self.chunks_file,
            self.embeddings_file,
            self.metadata_file,
        ]

        missing_files = [
            str(file_path)
            for file_path in required_files
            if not file_path.exists()
        ]

        if missing_files:
            raise FileNotFoundError(
                "Missing RAG index files: "
                + ", ".join(missing_files)
                + ". Build the knowledge base and embeddings first."
            )

    def _load_metadata(self):
        """Load and validate embedding metadata."""

        with self.metadata_file.open(
            "r",
            encoding="utf-8",
        ) as metadata_file:
            metadata = json.load(metadata_file)

        required_fields = [
            "embedding_model",
            "embedding_dimension",
            "chunk_count",
            "normalized_embeddings",
            "knowledge_chunks_sha256",
            "embeddings_sha256",
        ]

        missing_fields = [
            field
            for field in required_fields
            if field not in metadata
        ]

        if missing_fields:
            raise ValueError(
                "Embedding metadata is missing fields: "
                + ", ".join(missing_fields)
            )

        return metadata

    def _validate_checksums(self):
        """Confirm that chunks and embeddings match the metadata."""

        chunks_checksum = calculate_file_sha256(
            self.chunks_file
        )

        if (
            chunks_checksum
            != self.metadata["knowledge_chunks_sha256"]
        ):
            raise ValueError(
                "The knowledge chunks changed after embedding "
                "generation. Regenerate the embeddings."
            )

        embeddings_checksum = calculate_file_sha256(
            self.embeddings_file
        )

        if (
            embeddings_checksum
            != self.metadata["embeddings_sha256"]
        ):
            raise ValueError(
                "The embeddings file does not match its metadata. "
                "Regenerate the embeddings."
            )

    def _validate_loaded_index(self):
        """Validate chunk records and embedding alignment."""

        if self.chunk_data.empty:
            raise ValueError(
                "The knowledge chunks file is empty."
            )

        required_columns = [
            "chunk_id",
            "source_file",
            "document_title",
            "section_path",
            "content",
            "searchable_text",
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in self.chunk_data.columns
        ]

        if missing_columns:
            raise ValueError(
                "Knowledge chunks are missing columns: "
                + ", ".join(missing_columns)
            )

        if self.embeddings.ndim != 2:
            raise ValueError(
                "Expected a two-dimensional embedding matrix."
            )

        if len(self.chunk_data) != self.embeddings.shape[0]:
            raise ValueError(
                "Knowledge chunk count does not match "
                "embedding row count."
            )

        if (
            self.embeddings.shape[0]
            != int(self.metadata["chunk_count"])
        ):
            raise ValueError(
                "Embedding row count does not match metadata."
            )

        if (
            self.embeddings.shape[1]
            != int(self.metadata["embedding_dimension"])
        ):
            raise ValueError(
                "Embedding dimension does not match metadata."
            )

        if not np.isfinite(self.embeddings).all():
            raise ValueError(
                "Embedding matrix contains invalid values."
            )

        vector_norms = np.linalg.norm(
            self.embeddings,
            axis=1,
        )

        if not np.allclose(
            vector_norms,
            1.0,
            atol=1e-4,
        ):
            raise ValueError(
                "Stored embeddings are not normalized."
            )

    def _load_index(self):
        """Load and validate the complete RAG index."""

        self._validate_files_exist()

        self.metadata = self._load_metadata()

        self._validate_checksums()

        self.chunk_data = pd.read_csv(
            self.chunks_file
        )

        self.embeddings = np.load(
            self.embeddings_file,
            allow_pickle=False,
        ).astype(np.float32)

        self._validate_loaded_index()

        self.model = SentenceTransformer(
            self.metadata["embedding_model"]
        )

    def encode_question(self, question):
        """Convert a user question into a normalized vector."""

        normalized_question = str(question).strip()

        if not normalized_question:
            raise ValueError(
                "The retrieval question cannot be empty."
            )

        question_embedding = self.model.encode(
            normalized_question,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        question_embedding = np.asarray(
            question_embedding,
            dtype=np.float32,
        )

        if question_embedding.ndim != 1:
            raise ValueError(
                "Expected a one-dimensional question embedding."
            )

        if (
            question_embedding.shape[0]
            != self.embeddings.shape[1]
        ):
            raise ValueError(
                "Question embedding dimension does not match "
                "stored knowledge embeddings."
            )

        return question_embedding

    def calculate_lexical_scores(self, question):
        """Calculate keyword relevance for every knowledge chunk."""

        query_terms = normalize_search_terms(
            question
        )

        lexical_scores = []

        for _, chunk in self.chunk_data.iterrows():
            section_terms = normalize_search_terms(
                chunk["section_path"]
            )

            content_terms = normalize_search_terms(
                chunk["content"]
            )

            title_terms = normalize_search_terms(
                chunk["document_title"]
            )

            section_overlap = calculate_overlap_score(
                query_terms,
                section_terms,
            )

            content_overlap = calculate_overlap_score(
                query_terms,
                content_terms,
            )

            title_overlap = calculate_overlap_score(
                query_terms,
                title_terms,
            )

            lexical_score = (
                section_overlap * 0.50
                + content_overlap * 0.35
                + title_overlap * 0.15
            )

            lexical_scores.append(lexical_score)

        return np.asarray(
            lexical_scores,
            dtype=np.float32,
        )

    def retrieve(
        self,
        question,
        top_k=DEFAULT_TOP_K,
        minimum_score=DEFAULT_MINIMUM_SCORE,
    ):
        """Return the highest-ranked hybrid retrieval results."""

        if not isinstance(top_k, int) or top_k <= 0:
            raise ValueError(
                "top_k must be a positive integer."
            )

        if not 0 <= minimum_score <= 1:
            raise ValueError(
                "minimum_score must be between 0 and 1."
            )

        question_embedding = self.encode_question(
            question
        )

        semantic_scores = (
            self.embeddings @ question_embedding
        )

        lexical_scores = self.calculate_lexical_scores(
            question
        )

        hybrid_scores = (
            semantic_scores * SEMANTIC_WEIGHT
            + lexical_scores * LEXICAL_WEIGHT
        )

        ranked_indices = np.argsort(
            hybrid_scores
        )[::-1]

        retrieved_chunks = []

        for row_index in ranked_indices:
            hybrid_score = float(
                hybrid_scores[row_index]
            )

            if hybrid_score < minimum_score:
                continue

            chunk_record = self.chunk_data.iloc[
                int(row_index)
            ]

            retrieved_chunks.append(
                {
                    "rank": len(retrieved_chunks) + 1,
                    "chunk_id": chunk_record["chunk_id"],
                    "source_file": chunk_record[
                        "source_file"
                    ],
                    "document_title": chunk_record[
                        "document_title"
                    ],
                    "section_path": chunk_record[
                        "section_path"
                    ],
                    "content": chunk_record["content"],
                    "semantic_score": float(
                        semantic_scores[row_index]
                    ),
                    "lexical_score": float(
                        lexical_scores[row_index]
                    ),
                    "hybrid_score": hybrid_score,
                }
            )

            if len(retrieved_chunks) >= top_k:
                break

        return retrieved_chunks

    def format_context(self, retrieved_chunks):
        """Format retrieved chunks for an LLM prompt."""

        if not retrieved_chunks:
            return (
                "No sufficiently relevant verified context "
                "was retrieved."
            )

        context_sections = []

        for chunk in retrieved_chunks:
            context_sections.append(
                "\n".join(
                    [
                        (
                            f"[Source {chunk['rank']}] "
                            f"{chunk['source_file']}"
                        ),
                        (
                            "Section: "
                            f"{chunk['section_path']}"
                        ),
                        (
                            "Hybrid relevance score: "
                            f"{chunk['hybrid_score']:.4f}"
                        ),
                        "",
                        chunk["content"],
                    ]
                )
            )

        return "\n\n---\n\n".join(
            context_sections
        )


def display_results(question, retrieved_chunks):
    """Print hybrid retrieval results for local testing."""

    print("RAG HYBRID RETRIEVAL")
    print("-" * 72)
    print(f"Question: {question}")
    print(
        f"Results returned: "
        f"{len(retrieved_chunks):,}"
    )
    print(
        f"Weights: semantic={SEMANTIC_WEIGHT:.2f}, "
        f"lexical={LEXICAL_WEIGHT:.2f}"
    )
    print("-" * 72)

    if not retrieved_chunks:
        print(
            "No chunks met the minimum hybrid score."
        )
        return

    for chunk in retrieved_chunks:
        content_preview = (
            chunk["content"]
            .replace("\n", " ")
            .strip()
        )

        if len(content_preview) > 300:
            content_preview = (
                content_preview[:297] + "..."
            )

        print(f"Rank: {chunk['rank']}")
        print(
            "Hybrid score: "
            f"{chunk['hybrid_score']:.4f}"
        )
        print(
            "Semantic score: "
            f"{chunk['semantic_score']:.4f}"
        )
        print(
            "Lexical score: "
            f"{chunk['lexical_score']:.4f}"
        )
        print(
            f"Source: {chunk['source_file']}"
        )
        print(
            f"Section: {chunk['section_path']}"
        )
        print(
            f"Preview: {content_preview}"
        )
        print("-" * 72)


def parse_arguments():
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Retrieve relevant banking-project "
            "knowledge chunks."
        )
    )

    parser.add_argument(
        "question",
        type=str,
        help="Question to search for.",
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help="Maximum number of chunks to return.",
    )

    parser.add_argument(
        "--minimum-score",
        type=float,
        default=DEFAULT_MINIMUM_SCORE,
        help=(
            "Minimum hybrid relevance score "
            "between 0 and 1."
        ),
    )

    return parser.parse_args()


def main():
    """Run a local hybrid retrieval test."""

    arguments = parse_arguments()

    retriever = KnowledgeRetriever()

    retrieved_chunks = retriever.retrieve(
        question=arguments.question,
        top_k=arguments.top_k,
        minimum_score=arguments.minimum_score,
    )

    display_results(
        arguments.question,
        retrieved_chunks,
    )


if __name__ == "__main__":
    main()