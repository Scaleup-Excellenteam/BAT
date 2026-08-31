import re
import string

# ביטוי רגולרי שמזהה את כל סימני הפיסוק התקניים
PUNCTUATION_PATTERN = re.compile(f"[{re.escape(string.punctuation)}]")

# ביטוי רגולרי שמזהה רצף של רווחים או תווים לבנים (טאבים, ירידות שורה)
EXTRA_SPACES_PATTERN = re.compile(r"\s+")

def normalize_text(text: str) -> str:
    """
    מנרמל מחרוזת טקסט:
    1. הופך לאותיות קטנות.
    2. מחליף סימני פיסוק ברווח (מונע הדבקת מילים סמוכות).
    3. מכווץ רווחים כפולים לרווח בודד ומנקה רווחי שוליים.
    """
    if not text:
        return ""
    
    # 1. Lowercase
    text = text.lower()
    
    # 2. הסרת סימני פיסוק (החלפה ברווח)
    text = PUNCTUATION_PATTERN.sub(" ", text)
    
    # 3. כיווץ רווחים וניקוי שוליים
    text = EXTRA_SPACES_PATTERN.sub(" ", text).strip()
    
    return text