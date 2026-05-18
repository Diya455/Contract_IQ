import re
import os
from huggingface_hub import InferenceClient
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer
from dotenv import load_dotenv

load_dotenv()

# ─── Tokenizer (for chunk sizing) ────────────────────────────────────────────
tokenizer = AutoTokenizer.from_pretrained(
    "sentence-transformers/all-MiniLM-L6-v2"
)

# ─── Weaviate schema (called from main.py via weaviate_client.py) ─────────────
# NOTE: Schema creation is handled in vectordb/weaviate_client.py.
# This file only handles: chunking, embedding, and LLM answer generation.

# ─── Text utilities ───────────────────────────────────────────────────────────
def clean_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()

def count_tokens(text: str) -> int:
    return len(tokenizer.encode(text, add_special_tokens=False))

# ─── Section & clause splitting ───────────────────────────────────────────────
section_regex = re.compile(
    r"(?m)^(?:Chapter\s+\d+|Section\s+\d+|\d+(\.\d+){0,3})[\s:\-]+.*$"
)
clause_regex = re.compile(
    r"(?:(?:\([a-z]\))|(?:\([ivx]+\))|(?:\d+\.\d+)|(?:;))",
    re.IGNORECASE
)

def split_by_sections(text: str):
    matches = list(section_regex.finditer(text))
    if not matches:
        return [{"title": "Document", "content": text}]

    sections = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append({
            "title": match.group().strip(),
            "content": text[start:end].strip()
        })
    return sections

def split_by_clauses(text: str, max_tokens=400):
    clauses = []
    last_end = 0
    for match in clause_regex.finditer(text):
        clauses.append(text[last_end:match.start()])
        last_end = match.start()
    clauses.append(text[last_end:])
    clauses = [clean_text(c) for c in clauses if clean_text(c)]

    chunks = []
    current = ""
    for clause in clauses:
        test = (current + " " + clause).strip()
        if count_tokens(test) <= max_tokens:
            current = test
        else:
            if current:
                chunks.append(current)
            current = clause
    if current:
        chunks.append(current)
    return chunks

# ─── Main chunking function ───────────────────────────────────────────────────
def chunk_text_clause_section_with_metadata(pages_data, max_chunk_tokens=400, overlap_tokens=80):
    chunks = []

    for page_obj in pages_data:
        page_num = page_obj["page_number"]
        raw = page_obj["text"]
        raw = clean_text(raw)

        sections = split_by_sections(raw)

        for section in sections:
            title = section["title"]
            content = section["content"]

            if count_tokens(content) <= max_chunk_tokens:
                chunks.append({
                    "content": content,
                    "page_number": page_num,
                    "section_title": title
                })
            else:
                sub_chunks = split_by_clauses(content, max_tokens=max_chunk_tokens)
                for sc in sub_chunks:
                    chunks.append({
                        "content": sc,
                        "page_number": page_num,
                        "section_title": title
                    })

    if overlap_tokens > 0:
        overlapped = []
        for i, chunk in enumerate(chunks):
            overlapped.append(chunk)
            if i + 1 < len(chunks):
                cur_tokens = tokenizer.encode(chunk["content"], add_special_tokens=False)
                nxt_tokens = tokenizer.encode(chunks[i+1]["content"], add_special_tokens=False)

                if len(cur_tokens) + len(nxt_tokens) > max_chunk_tokens:
                    tail = cur_tokens[-overlap_tokens:]
                    head = nxt_tokens[:overlap_tokens]
                    bridge_tokens = tail + head
                    bridge_text = tokenizer.decode(bridge_tokens)
                    overlapped.append({
                        "content": bridge_text,
                        "page_number": chunk["page_number"],
                        "section_title": chunk["section_title"]
                    })
        chunks = overlapped

    return chunks

# ─── Embedding model ───────────────────────────────────────────────────────────
_embedding_model_cache = None

def load_model():
    global _embedding_model_cache
    if _embedding_model_cache is None:
        _embedding_model_cache = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model_cache

def embed_chunks(texts, model):
    return model.encode(texts, convert_to_numpy=True, show_progress_bar=False).tolist()

def load_and_chunk_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    pages_data = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        pages_data.append({"page_number": i+1, "text": text})

    model = load_model()
    chunks = chunk_text_clause_section_with_metadata(pages_data)
    documents = [c["content"] for c in chunks]
    embeddings = embed_chunks(documents, model)
    return pages_data, chunks, embeddings

# ─── LLM — HuggingFace Serverless Inference with Better Error Handling ─────────
HF_TOKEN = os.getenv("HF_TOKEN")

# Initialize client only if token is provided
hf_client = None
if HF_TOKEN:
    try:
        hf_client = InferenceClient(
            provider="hf-inference",
            api_key=HF_TOKEN
        )
    except Exception as e:
        print(f"Warning: Failed to initialize HuggingFace client: {e}")
        hf_client = None

def generate_answer(context: str, question: str) -> str:
    """
    Generate an answer using HuggingFace Inference API.
    Returns an error message if the API is not available.
    """
    if not HF_TOKEN:
        return (
            "⚠️ **HuggingFace Token Not Configured**\n\n"
            "The chatbot requires a valid HuggingFace API token to work.\n\n"
            "**To fix this:**\n"
            "1. Go to https://huggingface.co/settings/tokens\n"
            "2. Create a new token (or copy existing one)\n"
            "3. Update your `.env` file with: `HF_TOKEN=your_token_here`\n"
            "4. Restart the application\n\n"
            "For now, you can search contracts using the Dashboard page."
        )
    
    if not hf_client:
        return (
            "⚠️ **HuggingFace API Connection Failed**\n\n"
            "Could not connect to HuggingFace Inference API.\n\n"
            "Please check:\n"
            "- Your internet connection\n"
            "- Your HF_TOKEN is valid and not expired\n"
            "- HuggingFace services are operational\n\n"
            "You can still browse contracts in the Dashboard page."
        )
    
    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a smart contract assistant. "
                    "Answer the user's question directly and concisely — like a knowledgeable colleague, not a lawyer. "
                    "Use plain English. No bullet walls, no lengthy explanations. "
                    "If the answer is a date, party name, or number — just state it. "
                    "If the answer isn't in the context, say 'Not found in the uploaded contracts.' "
                    "Never make up information. Keep answers under 3 sentences unless a list is clearly needed."
                )
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}"
            }
        ]
        
        response = hf_client.chat_completion(
            model="Qwen/Qwen2.5-72B-Instruct",
            messages=messages,
            max_tokens=180,
            temperature=0.1
        )
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        error_msg = str(e)
        
        # Check for specific error types
        if "401" in error_msg or "Unauthorized" in error_msg:
            return (
                "⚠️ **Invalid HuggingFace Token**\n\n"
                "Your HuggingFace token is invalid or expired.\n\n"
                "**To fix this:**\n"
                "1. Go to https://huggingface.co/settings/tokens\n"
                "2. Create a new token with 'Read' permissions\n"
                "3. Copy the token (starts with 'hf_')\n"
                "4. Update `.env` file: `HF_TOKEN=hf_your_new_token`\n"
                "5. Restart the application\n\n"
                "**Note:** Tokens can expire or be revoked if shared publicly."
            )
        elif "403" in error_msg or "Forbidden" in error_msg:
            return (
                "⚠️ **Access Denied**\n\n"
                "Your HuggingFace token doesn't have permission to access this model.\n\n"
                "This usually means:\n"
                "- The token is for a different account\n"
                "- The model requires PRO subscription\n"
                "- The token permissions are insufficient\n\n"
                "Try creating a new token with 'Read' permissions."
            )
        elif "429" in error_msg or "rate limit" in error_msg.lower():
            return (
                "⚠️ **Rate Limit Exceeded**\n\n"
                "You've made too many requests to HuggingFace API.\n\n"
                "Please wait a few minutes and try again.\n\n"
                "The free tier has limits on API calls per hour."
            )
        else:
            return (
                f"⚠️ **Chatbot Error**\n\n"
                f"An error occurred while processing your question:\n\n"
                f"{error_msg}\n\n"
                f"You can still browse contracts in the Dashboard page."
            )