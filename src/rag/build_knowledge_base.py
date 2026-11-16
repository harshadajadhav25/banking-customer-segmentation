"""Build searchable text chunks from the RAG knowledge-base documents."""

import hashlib
import re
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

KNOWLEDGE_BASE_DIRECTORY = (
    PROJECT_ROOT / "docs" / "knowledge_base"
)

OUTPUT_DIRECTORY = PROJECT_ROOT / "data" / "rag"

OUTPUT_FILE = OUTPUT_DIRECTORY / "knowledge_chunks.csv"

EXPECTED_DOCUMENTS = {
    "data_dictionary.md",
    "model_card.md",
    "pipeline_architecture.md",
    "recommendation_rules.md",
    "responsible_use.md",
    "segment_profiles.md",
}

MAX_CHUNK_CHARACTERS = 1800
CHUNK_OVERLAP_CHARACTERS = 200


def clean_text(text):
    """Normalize unnecessary whitespace while preserving readable lines."""

    cleaned_lines = []
    previous_line_was_empty = False

    for raw_line in text.splitlines():
        line = raw_line.rstrip()

        if not line:
            if not previous_line_was_empty:
                cleaned_lines.append("")
            previous_line_was_empty = True
            continue

        cleaned_lines.append(line)
        previous_line_was_empty = False

    return "\n".join(cleaned_lines).strip()


def extract_document_title(markdown_text, source_file):
    """Return the first level-one Markdown heading as the document title."""

    for line in markdown_text.splitlines():
        match = re.match(r"^#\s+(.+?)\s*$", line)

        if match:
            return match.group(1).strip()

    return source_file.stem.replace("_", " ").title()


def parse_markdown_sections(markdown_text):
    """
    Split a Markdown document into sections while preserving heading paths.

    A heading path may look like:
    Product Recommendation Rules > Payment Card > Score Calculation
    """

    sections = []
    heading_stack = []
    content_lines = []

    def save_current_section():
        content = clean_text("\n".join(content_lines))

        if not content:
            return

        section_path = " > ".join(heading_stack)

        if not section_path:
            section_path = "Document Introduction"

        sections.append(
            {
                "section_path": section_path,
                "content": content,
            }
        )

    for line in markdown_text.splitlines():
        heading_match = re.match(
            r"^(#{1,6})\s+(.+?)\s*$",
            line,
        )

        if heading_match:
            save_current_section()
            content_lines = []

            heading_level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()

            heading_stack = heading_stack[: heading_level - 1]
            heading_stack.append(heading_text)
        else:
            content_lines.append(line)

    save_current_section()

    return sections


def find_safe_split_position(text, proposed_end):
    """Move a split position to a nearby paragraph or word boundary."""

    if proposed_end >= len(text):
        return len(text)

    paragraph_boundary = text.rfind(
        "\n\n",
        0,
        proposed_end,
    )

    if paragraph_boundary >= proposed_end // 2:
        return paragraph_boundary

    line_boundary = text.rfind(
        "\n",
        0,
        proposed_end,
    )

    if line_boundary >= proposed_end // 2:
        return line_boundary

    word_boundary = text.rfind(
        " ",
        0,
        proposed_end,
    )

    if word_boundary > 0:
        return word_boundary

    return proposed_end


def split_long_section(section_text):
    """Split long sections into overlapping character-based chunks."""

    section_text = clean_text(section_text)

    if len(section_text) <= MAX_CHUNK_CHARACTERS:
        return [section_text]

    chunks = []
    start_position = 0

    while start_position < len(section_text):
        proposed_end = min(
            start_position + MAX_CHUNK_CHARACTERS,
            len(section_text),
        )

        end_position = find_safe_split_position(
            section_text,
            proposed_end,
        )

        if end_position <= start_position:
            end_position = proposed_end

        chunk = section_text[
            start_position:end_position
        ].strip()

        if chunk:
            chunks.append(chunk)

        if end_position >= len(section_text):
            break

        next_start = max(
            end_position - CHUNK_OVERLAP_CHARACTERS,
            start_position + 1,
        )

        nearby_space = section_text.find(
            " ",
            next_start,
            min(
                next_start + 100,
                len(section_text),
            ),
        )

        if nearby_space != -1:
            next_start = nearby_space + 1

        start_position = next_start

    return chunks


def create_chunk_id(
    source_file,
    section_path,
    chunk_index,
    content,
):
    """Create a deterministic identifier for a knowledge chunk."""

    identifier_source = (
        f"{source_file}|"
        f"{section_path}|"
        f"{chunk_index}|"
        f"{content}"
    )

    identifier_hash = hashlib.sha256(
        identifier_source.encode("utf-8")
    ).hexdigest()[:12]

    return (
        f"{Path(source_file).stem}"
        f"_{chunk_index:03d}"
        f"_{identifier_hash}"
    )


def build_document_chunks(document_path):
    """Read one Markdown document and create its chunk records."""

    markdown_text = document_path.read_text(
        encoding="utf-8"
    )

    if not markdown_text.strip():
        raise ValueError(
            f"Knowledge document is empty: {document_path}"
        )

    document_title = extract_document_title(
        markdown_text,
        document_path,
    )

    sections = parse_markdown_sections(markdown_text)

    if not sections:
        raise ValueError(
            f"No readable sections found in: {document_path}"
        )

    document_chunks = []
    document_chunk_index = 1

    for section in sections:
        section_chunks = split_long_section(
            section["content"]
        )

        for section_chunk_index, content in enumerate(
            section_chunks,
            start=1,
        ):
            searchable_text = (
                f"Document: {document_title}\n"
                f"Section: {section['section_path']}\n\n"
                f"{content}"
            )

            chunk_id = create_chunk_id(
                source_file=document_path.name,
                section_path=section["section_path"],
                chunk_index=document_chunk_index,
                content=content,
            )

            document_chunks.append(
                {
                    "chunk_id": chunk_id,
                    "source_file": document_path.name,
                    "document_title": document_title,
                    "section_path": section["section_path"],
                    "document_chunk_index": (
                        document_chunk_index
                    ),
                    "section_chunk_index": (
                        section_chunk_index
                    ),
                    "content": content,
                    "searchable_text": searchable_text,
                    "character_count": len(content),
                    "word_count": len(content.split()),
                }
            )

            document_chunk_index += 1

    return document_chunks


def validate_source_documents():
    """Verify that every required knowledge document exists."""

    if not KNOWLEDGE_BASE_DIRECTORY.exists():
        raise FileNotFoundError(
            "Knowledge-base directory does not exist: "
            f"{KNOWLEDGE_BASE_DIRECTORY}"
        )

    available_documents = {
        path.name
        for path in KNOWLEDGE_BASE_DIRECTORY.glob("*.md")
    }

    missing_documents = (
        EXPECTED_DOCUMENTS - available_documents
    )

    if missing_documents:
        raise FileNotFoundError(
            "Missing required knowledge documents: "
            + ", ".join(sorted(missing_documents))
        )

    return sorted(
        KNOWLEDGE_BASE_DIRECTORY.glob("*.md")
    )


def validate_chunks(chunk_data):
    """Validate the generated knowledge chunks."""

    if chunk_data.empty:
        raise ValueError(
            "The knowledge-base builder generated no chunks."
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
        if column not in chunk_data.columns
    ]

    if missing_columns:
        raise ValueError(
            "Knowledge chunks are missing columns: "
            + ", ".join(missing_columns)
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

    empty_content = int(
        chunk_data["content"]
        .astype(str)
        .str.strip()
        .eq("")
        .sum()
    )

    if empty_content:
        raise ValueError(
            f"Knowledge chunks contain {empty_content} "
            "empty content values."
        )

    duplicate_ids = int(
        chunk_data["chunk_id"].duplicated().sum()
    )

    if duplicate_ids:
        raise ValueError(
            f"Knowledge chunks contain {duplicate_ids} "
            "duplicate chunk identifiers."
        )

    duplicate_content = int(
        chunk_data.duplicated(
            subset=[
                "source_file",
                "section_path",
                "content",
            ]
        ).sum()
    )

    if duplicate_content:
        raise ValueError(
            f"Knowledge chunks contain {duplicate_content} "
            "duplicate source-section-content records."
        )

    oversized_chunks = int(
        (
            chunk_data["character_count"]
            > MAX_CHUNK_CHARACTERS
        ).sum()
    )

    if oversized_chunks:
        raise ValueError(
            f"Knowledge chunks contain {oversized_chunks} "
            "oversized records."
        )


def build_knowledge_base():
    """Build and save the searchable knowledge-base chunks."""

    document_paths = validate_source_documents()

    print("RAG KNOWLEDGE-BASE BUILD")
    print("-" * 72)
    print(
        f"Knowledge directory: "
        f"{KNOWLEDGE_BASE_DIRECTORY}"
    )
    print(
        f"Markdown documents found: "
        f"{len(document_paths):,}"
    )

    all_chunks = []

    for document_path in document_paths:
        document_chunks = build_document_chunks(
            document_path
        )

        all_chunks.extend(document_chunks)

        print(
            f"{document_path.name}: "
            f"{len(document_chunks):,} chunks"
        )

    chunk_data = pd.DataFrame(all_chunks)

    chunk_data = chunk_data.sort_values(
        [
            "source_file",
            "document_chunk_index",
        ]
    ).reset_index(drop=True)

    validate_chunks(chunk_data)

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    chunk_data.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8",
    )

    print("-" * 72)
    print(
        f"Total chunks created: "
        f"{len(chunk_data):,}"
    )
    print(
        f"Total words indexed: "
        f"{chunk_data['word_count'].sum():,}"
    )
    print(
        f"Maximum chunk characters: "
        f"{chunk_data['character_count'].max():,}"
    )
    print(f"Output file: {OUTPUT_FILE}")
    print(
        "Knowledge-base build completed successfully."
    )


if __name__ == "__main__":
    build_knowledge_base()