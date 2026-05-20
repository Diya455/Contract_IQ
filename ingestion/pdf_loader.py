"""
PDF Loader with HuggingFace Integration - COMPLETE FIX
Handles all chunk formats correctly.
"""
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv

load_dotenv()

# Use a reliable, free model for embeddings
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# HuggingFace API setup
HF_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")


def load_model():
    """Load embedding model."""
    print(f"Loading embedding model: {EMBEDDING_MODEL}")
    try:
        model = SentenceTransformer(EMBEDDING_MODEL)
        print("✓ Model loaded successfully")
        return model
    except Exception as e:
        print(f"❌ Model loading failed: {e}")
        raise


def chunk_text_clause_section_with_metadata(text, chunk_size=500, overlap=50):
    """Split text into chunks with metadata."""
    chunks = []
    words = text.split()

    for i in range(0, len(words), chunk_size - overlap):
        chunk_words = words[i:i + chunk_size]
        chunk_text = " ".join(chunk_words)

        chunks.append({
            "text": chunk_text,
            "metadata": {
                "chunk_index": len(chunks),
                "start_word": i,
                "end_word": i + len(chunk_words)
            }
        })

    print(f"✓ Created {len(chunks)} chunks")
    return chunks


def embed_chunks(chunks, model):
    """Generate embeddings for text chunks."""
    try:
        # Extract text from chunks (handle both string and dict formats)
        texts = []
        for chunk in chunks:
            if isinstance(chunk, dict):
                texts.append(chunk.get("text", ""))
            else:
                texts.append(str(chunk))

        # Generate embeddings
        embeddings = model.encode(texts, show_progress_bar=False)

        # Convert to list format
        embeddings_list = [emb.tolist() for emb in embeddings]

        print(f"✓ Generated {len(embeddings_list)} embeddings")
        return embeddings_list
    except Exception as e:
        print(f"❌ Embedding error: {e}")
        raise


def extract_text_from_chunk(chunk):
    """
    Extract text from chunk regardless of format.
    Handles: dict, string, or other formats.
    """
    if chunk is None:
        return ""

    # If it's a dictionary
    if isinstance(chunk, dict):
        return chunk.get("text", str(chunk))

    # If it's already a string
    if isinstance(chunk, str):
        return chunk

    # Otherwise convert to string
    return str(chunk)


def generate_answer(question, context_chunks):
    """
    Generate answer from context chunks.
    Uses HuggingFace Inference API with a reliable model.
    """
    try:
        # Extract text from all chunks (handle any format)
        context_texts = [extract_text_from_chunk(chunk) for chunk in context_chunks]

        # Remove empty texts
        context_texts = [text for text in context_texts if text.strip()]

        if not context_texts:
            return "I couldn't find relevant information in the contracts. Please try rephrasing your question."

        # If no API key, use fallback
        if not HF_API_KEY:
            print("⚠️ No HuggingFace API key found")
            return generate_simple_answer(question, context_texts)

        # Try API
        try:
            import requests

            # Combine context
            context = "\n\n".join(context_texts[:3])

            # Use a reliable, free model
            API_URL = "https://api-inference.huggingface.co/models/google/flan-t5-base"
            headers = {"Authorization": f"Bearer {HF_API_KEY}"}

            # Create prompt
            prompt = f"""Answer the question based on the context below.

Context:
{context}

Question: {question}

Answer:"""

            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 200,
                    "temperature": 0.7
                }
            }

            response = requests.post(API_URL, headers=headers, json=payload, timeout=30)

            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    answer = result[0].get("generated_text", "")
                    if answer:
                        print("✓ Generated answer using HuggingFace API")
                        return answer.strip()

            # Fallback if API fails
            print("⚠️ API failed, using simple answer")
            return generate_simple_answer(question, context_texts)

        except Exception as e:
            print(f"⚠️ HuggingFace API error: {e}")
            return generate_simple_answer(question, context_texts)

    except Exception as e:
        print(f"❌ Answer generation error: {e}")
        return "I encountered an error processing your question. Please try again."


def generate_simple_answer(question, context_texts):
    """
    Generate a simple answer without API (fallback).
    Extracts relevant sentences from context.

    Args:
        question: User's question (string)
        context_texts: List of text strings (not dicts!)
    """
    try:
        # Ensure context_texts is a list of strings
        if not isinstance(context_texts, list):
            context_texts = [str(context_texts)]

        # Convert any non-strings to strings
        context_texts = [str(text) for text in context_texts if text]

        if not context_texts:
            return "I couldn't find relevant information in the contracts."

        # Combine all context
        full_context = "\n".join(context_texts[:5])

        # Split into sentences
        sentences = []
        for sent in full_context.replace("!", ".").replace("?", ".").split("."):
            sent = sent.strip()
            if len(sent) > 20:  # Only keep substantial sentences
                sentences.append(sent)

        if not sentences:
            return full_context[:500] + "..."

        # Find sentences containing question keywords
        question_words = set(question.lower().split())
        question_words.discard("what")
        question_words.discard("when")
        question_words.discard("where")
        question_words.discard("who")
        question_words.discard("how")
        question_words.discard("is")
        question_words.discard("the")
        question_words.discard("a")

        relevant_sentences = []

        for sentence in sentences:
            sentence_words = set(sentence.lower().split())
            overlap = question_words & sentence_words
            if len(overlap) >= 1:  # At least 1 common word
                relevant_sentences.append(sentence.strip())

        if relevant_sentences:
            # Return top 3 relevant sentences
            answer = ". ".join(relevant_sentences[:3]) + "."
            print("✓ Generated simple answer from context")
            return answer
        else:
            # Return first few sentences if no match
            answer = ". ".join(sentences[:3]) + "."
            print("✓ Generated generic answer")
            return answer

    except Exception as e:
        print(f"❌ Simple answer error: {e}")
        # Last resort: return first 300 chars of first context
        try:
            if context_texts and len(context_texts) > 0:
                return str(context_texts[0])[:300] + "..."
        except:
            pass
        return "I found relevant information but couldn't format an answer. Please try rephrasing your question."
