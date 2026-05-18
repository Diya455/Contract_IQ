import re
import fitz
import numpy as np
import streamlit as st
from paddleocr import PaddleOCR
from pdf2image import convert_from_path, pdfinfo_from_path

POPPLER_PATH = r"C:\Users\Diya Shah\AppData\Local\Programs\poppler\Library\bin"


# LOAD OCR MODEL ONCE (CRITICAL)
@st.cache_resource(show_spinner=False)
def get_ocr():
    return PaddleOCR(
        use_angle_cls=True,
        lang="en",
    )

ocr = get_ocr()

# SAFE OCR EXTRACTION
def extract_ocr_pages(pdf_path, dpi=200):

    info = pdfinfo_from_path(
        pdf_path,
        poppler_path = POPPLER_PATH
    )

    images = convert_from_path(
        pdf_path,
        dpi = dpi,
        poppler_path = POPPLER_PATH
    )

    pages = []

    for img in images:
        img_np = np.array(img)
        result = ocr.ocr(img_np)
       
        try:
            result = ocr.ocr(img_np)
        except Exception:
            continue
        texts = []

        if result:

            # Handle ALL PaddleOCR formats safely
            for block in result:

                if isinstance(block, list):

                    for line in block:

                        try:
                            text = line[1][0]
                            texts.append(text)
                        except Exception:
                            continue

                elif isinstance(block, dict):

                    if "rec_texts" in block:
                        texts.extend(block["rec_texts"])

        page_text = " ".join(texts)

        if page_text.strip():
            pages.append(page_text)

    return pages

# SMART EXTRACTION (TEXT FIRST, OCR FALLBACK)
def extract_text_from_pdf(pdf_path):

    # Step 1 — Try fast text extraction first
    doc = fitz.open(pdf_path)

    text = ""

    for page in doc:
        page_text = page.get_text("text")
        if page_text:
            text += page_text

    doc.close()

    # Step 2 — If text exists, use it
    if text.strip():
        return text

    # Step 3 — Otherwise use OCR
    pages = extract_ocr_pages(pdf_path)

    if not pages:
        return ""

    return "\n".join(pages)

# CLEAN TEXT
def clean_text(text):

    if not text:
        return ""

    text = str(text)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# OPTIONAL CHUNK FUNCTION
def chunk_text(text, size=500, overlap=50):

    if not text:
        return []

    chunks = []

    start = 0

    while start < len(text):

        chunk = text[start:start + size]

        if chunk.strip():
            chunks.append(chunk)

        start += size - overlap

    return chunks
