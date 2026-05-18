import re


def clean_text(text):
    return re.sub(r"\s+", " ", text).strip()

def clean_text(text):
    if not text:
        return ""
    text = str(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

