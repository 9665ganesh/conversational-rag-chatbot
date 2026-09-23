import os
import base64
import uuid
import pickle

import pdfplumber
import fitz

from dotenv import load_dotenv

from groq import Groq

from langchain_community.document_loaders import (
    TextLoader,
    PyMuPDFLoader
)

from langchain_core.documents import Document

from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_huggingface import HuggingFaceEmbeddings

from langchain_chroma import Chroma


load_dotenv()


# =========================================================
# GROQ CLIENT
# =========================================================

groq_client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


VISION_MODEL = "qwen/qwen3.6-27b"


# =========================================================
# EXTRACT TABLES FROM PDF
# =========================================================

def extract_tables_from_pdf(file_path):
    """
    Extract real/selectable tables from PDF.
    """

    table_documents = []

    print("\n========================================")
    print("Extracting PDF tables...")
    print("========================================")

    with pdfplumber.open(file_path) as pdf:

        for page_number, page in enumerate(pdf.pages):

            tables = page.extract_tables()

            if not tables:
                continue

            print(
                f"Found {len(tables)} table(s) "
                f"on page {page_number + 1}"
            )

            for table_number, table in enumerate(tables):

                if not table:
                    continue

                cleaned_rows = []

                for row in table:

                    if not row:
                        continue

                    cleaned_row = [
                        str(cell).strip()
                        if cell is not None
                        else ""
                        for cell in row
                    ]

                    if any(cleaned_row):
                        cleaned_rows.append(cleaned_row)

                if not cleaned_rows:
                    continue

                table_text = (
                    f"Table {table_number + 1} "
                    f"from page {page_number + 1}\n\n"
                )

                for row in cleaned_rows:

                    table_text += " | ".join(row)
                    table_text += "\n"

                table_doc = Document(
                    page_content=table_text,
                    metadata={
                        "source": file_path,
                        "page": page_number,
                        "type": "table",
                        "table_number": table_number + 1
                    }
                )

                table_documents.append(table_doc)

    print(
        f"Total real PDF tables extracted: "
        f"{len(table_documents)}"
    )

    return table_documents


# =========================================================
# SAVE PDF IMAGE
# =========================================================

def save_pdf_image(
    image_bytes,
    image_directory,
    image_number
):
    """
    Save extracted PDF image to disk.
    """

    os.makedirs(
        image_directory,
        exist_ok=True
    )

    image_path = os.path.join(
        image_directory,
        f"image_{image_number}.png"
    )

    with open(
        image_path,
        "wb"
    ) as image_file:

        image_file.write(image_bytes)

    return image_path


# =========================================================
# ANALYZE IMAGE WITH VISION MODEL
# =========================================================

def analyze_image_with_vision(image_path, page_number):
    """
    Analyze an image using Groq vision model.

    The model handles:
    - normal images
    - OCR
    - tables inside images
    - charts
    - graphs
    - diagrams

    Logos, branding, letterheads, page numbers, and watermarks
    are ignored. If an image contains ONLY such elements with no
    meaningful content, the model returns a "SKIP:" marker so the
    caller can drop it instead of indexing it.
    """

    print(
        f"\nAnalyzing image: {image_path}"
    )

    try:

        with open(
            image_path,
            "rb"
        ) as image_file:

            image_bytes = image_file.read()

        base64_image = base64.b64encode(
            image_bytes
        ).decode("utf-8")

        prompt = """
You are analyzing an image extracted from a PDF.

Your task is to create a detailed textual representation
that can be stored in a vector database for RAG.

FIRST, check if this image is ONLY a logo, brand mark, icon, letterhead,
watermark, page number, decorative border, signature, or copyright notice —
with no chart, table, diagram, meaningful text, or photograph of substance.

If YES, respond with exactly this and nothing else:
SKIP: No meaningful content in this image.

Otherwise, analyze the image carefully and ignore any logos, branding,
letterheads, page numbers, or watermarks that appear alongside the real
content — do not describe or mention them, focus only on the meaningful part.

If the image contains normal text:
- Extract the important readable text.

If the image contains a table:
- Identify the table.
- Extract the column names.
- Extract the rows and values.
- Preserve relationships between columns and rows.

If the image contains a chart or graph:
- Identify the chart type.
- Identify labels, categories and values.
- Explain the important trends.

If the image contains a diagram:
- Explain the components.
- Explain relationships and flow between components.

If the image is a normal photograph:
- Describe the important objects and information.

Do NOT simply say "this is an image".

Return a detailed but concise textual representation
that can be searched later by a RAG system.

Do not invent information that cannot be seen.
"""

        response = groq_client.chat.completions.create(

            model=VISION_MODEL,

            messages=[
                {
                    "role": "user",

                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },

                        {
                            "type": "image_url",

                            "image_url": {
                                "url":
                                f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],

            temperature=0
        )

        description = response.choices[0].message.content

        print(
            "Image analysis completed."
        )

        return description

    except Exception as e:

        print(
            f"Error analyzing image: {e}"
        )

        return (
            "Image could not be analyzed."
        )


# =========================================================
# EXTRACT AND ANALYZE PDF IMAGES
# =========================================================

def process_pdf_images(
    file_path,
    chat_id
):
    """
    Extract embedded images from PDF,
    save them, analyze them with vision,
    and convert them into LangChain Documents.

    Images that are only logos/branding/watermarks (flagged by the
    vision model as "SKIP:") are discarded and never indexed.
    """

    image_documents = []
    skipped_count = 0

    print("\n========================================")
    print("Extracting PDF images...")
    print("========================================")

    image_directory = os.path.join(
        "db",
        chat_id,
        "images"
    )

    os.makedirs(
        image_directory,
        exist_ok=True
    )

    pdf = fitz.open(
        file_path
    )

    image_counter = 0

    try:

        for page_index in range(
            len(pdf)
        ):

            page = pdf[
                page_index
            ]

            images = page.get_images(
                full=True
            )

            if not images:
                continue

            print(
                f"Page {page_index + 1}: "
                f"{len(images)} image(s) found"
            )

            for image_info in images:

                image_counter += 1

                xref = image_info[0]

                image_data = pdf.extract_image(
                    xref
                )

                image_bytes = image_data[
                    "image"
                ]

                image_extension = image_data[
                    "ext"
                ]

                image_path = os.path.join(
                    image_directory,
                    f"image_{image_counter}.{image_extension}"
                )

                with open(
                    image_path,
                    "wb"
                ) as image_file:

                    image_file.write(
                        image_bytes
                    )

                print(
                    f"Saved image: "
                    f"{image_path}"
                )

                # -----------------------------------------
                # Vision analysis
                # -----------------------------------------

                description = analyze_image_with_vision(
                    image_path,
                    page_index
                )

                # -----------------------------------------
                # Skip logos / branding / watermark-only images
                # -----------------------------------------

                if description.strip().startswith("SKIP:"):

                    print(
                        f"Skipping image_{image_counter} "
                        f"(logo/branding, no useful content)"
                    )

                    skipped_count += 1

                    continue

                # -----------------------------------------
                # Create LangChain document
                # -----------------------------------------

                image_text = f"""
Image extracted from PDF.

Page:
{page_index + 1}

Image:
{image_counter}

Image Content:
{description}
"""

                image_doc = Document(

                    page_content=image_text,

                    metadata={
                        "source": file_path,

                        "page": page_index,

                        "type": "image",

                        "image_number":
                            image_counter,

                        "image_path":
                            image_path
                    }
                )

                image_documents.append(
                    image_doc
                )

    finally:

        pdf.close()

    print(
        f"\nTotal PDF images processed: "
        f"{len(image_documents)}"
    )

    print(
        f"Total PDF images skipped (logo/branding): "
        f"{skipped_count}"
    )

    return image_documents


# =========================================================
# LOAD DOCUMENTS
# =========================================================

def load_documents(
    file_path,
    chat_id=None
):

    print(
        f"\nLoading file: {file_path}"
    )

    if not os.path.exists(
        file_path
    ):

        raise FileNotFoundError(
            f"File does not exist: "
            f"{file_path}"
        )

    extension = os.path.splitext(
        file_path
    )[1].lower()

    # =====================================================
    # PDF
    # =====================================================

    if extension == ".pdf":

        print(
            "PDF detected"
        )

        loader = PyMuPDFLoader(
            file_path
        )

    # =====================================================
    # TXT
    # =====================================================

    elif extension == ".txt":

        print(
            "TXT detected"
        )

        loader = TextLoader(
            file_path,
            encoding="utf-8"
        )

    else:

        raise ValueError(
            f"Unsupported file type: "
            f"{extension}"
        )

    # =====================================================
    # LOAD TEXT
    # =====================================================

    documents = loader.load()

    # =====================================================
    # PDF TABLES
    # =====================================================

    if extension == ".pdf":

        table_documents = (
            extract_tables_from_pdf(
                file_path
            )
        )

        documents.extend(
            table_documents
        )

    # =====================================================
    # PDF IMAGES
    # =====================================================

    if (
        extension == ".pdf"
        and chat_id is not None
    ):

        image_documents = (
            process_pdf_images(
                file_path,
                chat_id
            )
        )

        documents.extend(
            image_documents
        )

    if not documents:

        raise ValueError(
            "No content found in document"
        )

    print(
        f"\nTotal document sections: "
        f"{len(documents)}"
    )

    # =====================================================
    # DEBUG INFORMATION
    # =====================================================

    for i, doc in enumerate(
        documents[:10]
    ):

        print(
            f"\n========== Document {i + 1} =========="
        )

        print(
            "Source:",
            doc.metadata.get(
                "source"
            )
        )

        print(
            "Type:",
            doc.metadata.get(
                "type",
                "text"
            )
        )

        print(
            "Page:",
            doc.metadata.get(
                "page"
            )
        )

        print(
            "Content length:",
            len(
                doc.page_content
            )
        )

        print(
            "Preview:"
        )

        print(
            doc.page_content[:500]
        )

        print(
            "Metadata:",
            doc.metadata
        )

    return documents


# =========================================================
# SPLIT DOCUMENTS
# =========================================================

def split_documents(
    documents,
    chunk_size=500,
    chunk_overlap=20
):
    """
    Split text documents into chunks. Image and table documents
    are kept intact (not split) since the vision model / table
    extractor already produces concise, self-contained content —
    splitting them can break metadata continuity (image_path)
    across chunks and hurt retrieval quality.
    """

    print(
        "\nChunking documents...."
    )

    text_spliter = (
        RecursiveCharacterTextSplitter(

            chunk_size=chunk_size,

            chunk_overlap=chunk_overlap
        )
    )

    # Separate text docs from image/table docs
    text_documents = [
        doc for doc in documents
        if doc.metadata.get("type") not in ("image", "table")
    ]

    special_documents = [
        doc for doc in documents
        if doc.metadata.get("type") in ("image", "table")
    ]

    chunks = (
        text_spliter.split_documents(
            text_documents
        )
    )

    # Add image/table docs back without splitting
    chunks.extend(special_documents)

    print(
        f"\nTotal chunks created: "
        f"{len(chunks)}"
    )

    if chunks:

        for i, chunk in enumerate(
            chunks[:10]
        ):

            print(
                f"\n------ Chunk {i + 1} ------"
            )

            print(
                "Source:",
                chunk.metadata.get(
                    "source"
                )
            )

            print(
                "Type:",
                chunk.metadata.get(
                    "type",
                    "text"
                )
            )

            print(
                "Page:",
                chunk.metadata.get(
                    "page"
                )
            )

            print(
                "Content Length:",
                len(
                    chunk.page_content
                )
            )

            print(
                "Content:"
            )

            print(
                chunk.page_content
            )

            print(
                "-" * 50
            )

        if len(chunks) > 10:

            print(
                f"\n...and "
                f"{len(chunks) - 10} "
                f"more chunks...."
            )

    return chunks


# =========================================================
# VECTOR STORE
# =========================================================

def vector_store(
    chunks,
    chat_id=None
):

    if chat_id is None:

        chat_id = uuid.uuid4().hex[:8]

    persist_directory = os.path.join(
        "db",
        chat_id
    )

    os.makedirs(
        persist_directory,
        exist_ok=True
    )

    print(
        "\n1. Chat ID:",
        chat_id
    )

    print(
        "2. DB Path:",
        persist_directory
    )

    embedding_model = (
        HuggingFaceEmbeddings(

            model_name=
            "BAAI/bge-small-en-v1.5"
        )
    )

    print(
        "3. Embedding model loaded"
    )

    db = Chroma.from_documents(

        documents=chunks,

        embedding=embedding_model,

        persist_directory=
            persist_directory
    )

    print(
        "4. Chroma DB created"
    )

    # =====================================================
    # SAVE CHUNKS
    # =====================================================

    with open(
        os.path.join(
            persist_directory,
            "documents.pkl"
        ),
        "wb"
    ) as f:

        pickle.dump(
            chunks,
            f
        )

    print(
        "5. documents.pkl saved"
    )

    return (
        chat_id,
        persist_directory
    )


# =========================================================
# COMPLETE INGESTION PIPELINE
# =========================================================

def ingestion_pipeline(
    file_path
):

    print(
        "\n========================================"
    )

    print(
        "Starting ingestion pipeline..."
    )

    print(
        "========================================"
    )

    # -----------------------------------------------------
    # Create chat ID FIRST
    # -----------------------------------------------------

    chat_id = uuid.uuid4().hex[:8]

    print(
        f"Generated Chat ID: {chat_id}"
    )

    # -----------------------------------------------------
    # Load text + tables + images
    # -----------------------------------------------------

    documents = load_documents(
        file_path,
        chat_id
    )

    # -----------------------------------------------------
    # Split everything
    # -----------------------------------------------------

    chunks = split_documents(
        documents
    )

    # -----------------------------------------------------
    # Create vector database
    # -----------------------------------------------------

    chat_id, db_path = vector_store(
        chunks,
        chat_id
    )

    print(
        "\n========================================"
    )

    print(
        "Ingestion completed successfully!"
    )

    print(
        "========================================"
    )

    return (
        chat_id,
        db_path
    )


# =========================================================
# MAIN
# =========================================================

def main():

    print(
        "Main function"
    )

    file_path = "uploads"

    if not os.path.exists(
        file_path
    ):

        print(
            "uploads directory does not exist."
        )

        return

    # NOTE:
    # This main() is only for testing.
    # The Flask application should use
    # ingestion_pipeline(file_path).

    print(
        "Use ingestion_pipeline() "
        "from your Flask application."
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    main()