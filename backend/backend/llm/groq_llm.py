import os
import re
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except Exception:
    Groq = None
    GROQ_AVAILABLE = False

MODEL_NAME = "openai/gpt-oss-20b"

COLLEGE_FULL_NAME = "Nadimpalli Satyanarayana Raju Institute of Technology"
COLLEGE_SHORT_NAME = "NSRIT"
ASSISTANT_NAME = "Cella"

# Initialize client
_client = None
if GROQ_AVAILABLE:
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        try:
            _client = Groq(api_key=api_key)
        except Exception:
            _client = None


def normalize_text(text: str) -> str:
    text = (text or "").strip().lower().replace("’", "'")
    text = text.replace("after noon", "afternoon")
    text = text.replace("goodafternoon", "good afternoon")
    text = text.replace("goodmorning", "good morning")
    text = text.replace("goodevening", "good evening")
    text = text.replace("goodnight", "good night")
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text



def build_history_messages(history: Optional[list] = None, limit: int = 6):
    history = history or []
    messages = []

    for item in history[-limit:]:
        if not isinstance(item, dict):
            continue

        role = item.get("role")
        content = (item.get("content") or "").strip()

        if role not in {"user", "assistant"} or not content:
            continue

        messages.append({
            "role": role,
            "content": content
        })

    return messages

def get_rule_based_reply(prompt: str) -> Optional[str]:
    q = normalize_text(prompt)

    if not q:
        return "Hello! Welcome to the NSRIT Exam Cell. How can I assist you today?"

    greeting_patterns = {
        "hello", "hi", "hey", "good",
        "good morning", "good evening", "good afternoon", "good night"
    }
    if q in greeting_patterns:
        if q == "good morning":
            return "Good morning! Welcome to the NSRIT Exam Cell. How can I assist you today?"
        if q == "good evening":
            return "Good evening! Welcome to the NSRIT Exam Cell. How can I assist you today?"
        if q == "good afternoon":
            return "Good afternoon! Welcome to the NSRIT Exam Cell. How can I assist you today?"
        if q == "good night":
            return "Good night! If you need any exam cell information later, I will be here to help."
        if q == "good":
            return "Hello! How can I help you with NSRIT exam cell information today?"
        return "Hello! Welcome to the NSRIT Exam Cell. How can I assist you today?"

    if q in {
        "your name", "what is your name", "who are you", "tell me your name",
        "u r name", "ur name", "name"
    }:
        return f"My name is {ASSISTANT_NAME}. I am the {COLLEGE_SHORT_NAME} Exam Cell Assistant."

    if q in {
        "which college", "college name", "what is your college",
        "what is your college name", "which institute", "college"
    }:
        return (
            f"You are interacting with the {COLLEGE_SHORT_NAME} Exam Cell Assistant. "
            f"{COLLEGE_SHORT_NAME} stands for {COLLEGE_FULL_NAME}."
        )

    if "established" in q and ("nsrit" in q or "college" in q or "institute" in q):
        return f"{COLLEGE_FULL_NAME} ({COLLEGE_SHORT_NAME}) was established in 2008."

    if q in {"it 2008", "its 2008", "it's 2008", "yes 2008"}:
        return f"Yes. {COLLEGE_SHORT_NAME} was established in 2008."

    off_topic_patterns = {
        "had dinner",
        "have you had dinner",
        "u had dinner",
        "did you have dinner",
        "dinner",
        "had lunch",
        "u had lunch",
        "lunch",
        "how was your day",
        "what are you doing"
    }
    if q in off_topic_patterns:
        return (
            f"I am {ASSISTANT_NAME}, the {COLLEGE_SHORT_NAME} Exam Cell Assistant, so I do not have personal routines like meals. "
            "I can help you with sem timetables, mid timetables, supply fees, revaluation fees, sem fees, and exam circulars."
        )

    thanks_patterns = {"thanks", "thank you", "ok thanks", "thank you so much"}
    if q in thanks_patterns:
        return "You're welcome. If you need any exam cell information, I'm here to help."

    return None

def generate_answer(prompt: str, context: str, history: Optional[list] = None) -> str:
    history_messages = build_history_messages(history)

    # First handle identity / greeting / off-topic safely
    direct_reply = get_rule_based_reply(prompt)
    if direct_reply:
        return direct_reply

    use_context = bool(context and len(context.strip()) > 30)

    if use_context and len(context) > 5000:
        context = context[:5000]

    # ==================================================
    # RAG MODE
    # ==================================================
    if use_context:
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are the official Exam Cell Assistant of {COLLEGE_FULL_NAME} ({COLLEGE_SHORT_NAME}).\n\n"
                    "IDENTITY RULES:\n"
                    f"- Your name is {ASSISTANT_NAME}\n"
                    f"- Your college is {COLLEGE_FULL_NAME}\n"
                    f"- {COLLEGE_SHORT_NAME} stands for {COLLEGE_FULL_NAME}\n"
                    "- Never mention any other college name\n"
                    "- Never invent a different expansion for NSRIT\n"
                    "- Always answer as the NSRIT Exam Cell Assistant only\n\n"
                    "ANSWERING RULES:\n"
                    "- Use the document context as the main source of truth\n"
                    "- Do not invent dates, semesters, batches, regulations, or notices\n"
                    "- If OCR text is noisy, still extract the most likely correct official information carefully\n"
                    "- If some details are missing, clearly say 'Not clearly mentioned in the document'\n"
                    "- Keep the answer clear, official, and easy for students to understand\n"
                    "- Include batch/admitted year when it is visible in the document\n"
                    "- Include important dates if they exist\n"
                    "- Include exam type and semester if they are identifiable\n\n"
                    "RESPONSE FORMAT:\n"
                    "Always respond in this format:\n\n"
                    "Summary:\n"
                    "<2 to 4 clear lines>\n\n"
                    "Important Dates:\n"
                    "- <date or detail>\n"
                    "- <date or detail>\n\n"
                    "Exam Type / Semester:\n"
                    "- Exam Type: <value>\n"
                    "- Semester: <value>\n"
                    "- Batch / Regulation: <value>\n\n"
                    "Additional Details:\n"
                    "- <extra useful point>\n"
                    "- <extra useful point>\n\n"
                    "If a section has no clear information, write 'Not clearly mentioned in the document.'"
                )
            }
        ]

        if history_messages:
            messages.extend(history_messages)

        messages.append(
            {
                "role": "user",
                "content": f"""
DOCUMENT CONTENT:
{context}

QUESTION:
{prompt}

Read the document carefully and answer in the required format.
Do not skip the section headings.
"""
            }
        )

    # ==================================================
    # NORMAL CHAT MODE
    # ==================================================
    else:
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are {ASSISTANT_NAME}, the {COLLEGE_SHORT_NAME} Exam Cell Assistant of {COLLEGE_FULL_NAME}.\n"
                    f"{COLLEGE_SHORT_NAME} stands for {COLLEGE_FULL_NAME}.\n"
                    "Never mention any wrong college name.\n"
                    "For general conversation, reply politely but do not behave like a personal human friend.\n"
                    "Always gently steer the conversation back to exam cell help.\n"
                    "If the user asks about exam notices, timetables, supply, revaluation, hall tickets, results, or circulars, help clearly.\n"
                    "If no uploaded document context is available for official details, say that the user should check uploaded exam cell documents."
                )
            }
        ]

        if history_messages:
            messages.extend(history_messages)

        messages.append(
            {
                "role": "user",
                "content": prompt
            }
        )

    # ==================================================
    # LLM CALL
    # ==================================================
    if _client:
        try:
            completion = _client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.15,
                max_tokens=500,
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            return f"⚠️ LLM Error: {str(e)}"

    # ==================================================
    # FALLBACK
    # ==================================================
    if use_context:
        return (
            "Summary:\n"
            "LLM is not available right now, but relevant document text was found.\n\n"
            "Important Dates:\n"
            "- Not clearly processed because LLM is unavailable.\n\n"
            "Exam Type / Semester:\n"
            "- Not clearly processed because LLM is unavailable.\n\n"
            "Additional Details:\n"
            f"- Extracted document preview: {context[:700]}"
        )

    return "⚠️ LLM not configured properly. Please check API key."
