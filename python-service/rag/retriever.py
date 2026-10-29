import os
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from dotenv import load_dotenv

load_dotenv()

QDRANT_URL = os.getenv("QUADRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QUADRANT_API_KEY", None)
COLLECTION_NAME = "ncert"
EMBED_MODEL = "all-MiniLM-L6-v2"

# Load once at module level (expensive to reload every request)
model = SentenceTransformer(EMBED_MODEL)
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


# ═══════════════════════════════════════════════════════════════════
# SUBJECT DETECTION — keyword-based scoring
# ═══════════════════════════════════════════════════════════════════

SUBJECT_KEYWORDS = {
    "physics": [
        "motion", "force", "velocity", "acceleration", "momentum", "energy",
        "work", "power", "gravity", "gravitation", "newton", "kepler",
        "wave", "sound", "light", "optics", "reflection", "refraction",
        "electricity", "current", "resistance", "magnetic", "magnetism",
        "circuit", "voltage", "ohm", "thermodynamics", "heat", "temperature",
        "pressure", "fluid", "buoyancy", "nuclear", "radiation", "quantum",
        "inertia", "friction", "tension", "projectile", "orbit", "satellite",
    ],
    "chemistry": [
        "atom", "molecule", "element", "compound", "reaction", "bond",
        "ionic", "covalent", "organic", "inorganic", "acid", "base", "salt",
        "oxidation", "reduction", "redox", "mole", "concentration", "solution",
        "periodic", "valence", "electron", "proton", "neutron", "isotope",
        "polymer", "hydrocarbon", "alkane", "alkene", "alcohol", "aldehyde",
        "ketone", "ester", "amine", "benzene", "aromatic", "catalyst",
        "equilibrium", "kinetics", "thermochemistry", "electrochemistry",
        "sandmeyer", "diazotization", "esterification", "saponification",
        "ph", "buffer", "titration", "indicator", "precipitate",
    ],
    "mathematics": [
        "equation", "algebra", "geometry", "trigonometry", "calculus",
        "derivative", "integral", "function", "graph", "coordinate",
        "matrix", "vector", "probability", "statistics", "set", "sequence",
        "series", "progression", "arithmetic", "geometric", "logarithm",
        "polynomial", "quadratic", "linear", "circle", "triangle", "angle",
        "theorem", "pythagoras", "proof", "permutation", "combination",
        "binomial", "complex", "differential", "integration", "limit",
        "continuity", "determinant", "inverse", "ratio", "proportion",
    ],
}


def detect_subject(question: str) -> str:
    """
    Detect subject from question text.
    Returns: "physics" | "chemistry" | "mathematics" | "general"
    """
    question_lower = question.lower()

    scores = {"physics": 0, "chemistry": 0, "mathematics": 0}

    for subject, keywords in SUBJECT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in question_lower:
                scores[subject] += 1

    best_subject = max(scores, key=scores.get)

    # Only return detected subject if score > 0
    if scores[best_subject] > 0:
        return best_subject

    return "general"


def _normalize_subject(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    return normalized or None


def _normalize_class_level(value: str | None) -> str | None:
    if value is None:
        return None

    text = str(value).strip().lower()
    if not text:
        return None

    for prefix in ("class", "grade", "std"):
        text = text.replace(prefix, "")
    text = text.strip()

    digits = "".join(ch for ch in text if ch.isdigit())
    if digits:
        return str(int(digits))

    roman_to_int = {
        "i": "1",
        "ii": "2",
        "iii": "3",
        "iv": "4",
        "v": "5",
        "vi": "6",
        "vii": "7",
        "viii": "8",
        "ix": "9",
        "x": "10",
        "xi": "11",
        "xii": "12",
    }
    return roman_to_int.get(text, text)


def _build_filters(subject: str | None, class_level: str | None):
    conditions = []
    if subject:
        conditions.append(
            FieldCondition(key="subject", match=MatchValue(value=subject))
        )
    if class_level:
        conditions.append(
            FieldCondition(key="class", match=MatchValue(value=class_level))
        )

    if not conditions:
        return None
    return Filter(must=conditions)


def _query_with_filters(query_vector, filters, top_k):
    """Query Qdrant with filters. Falls back to unfiltered if indexes are missing."""
    try:
        return client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=filters,
            limit=top_k,
            with_payload=True,
        )
    except Exception as e:
        error_msg = str(e)
        # If the error is about missing indexes, retry without filters
        if "Index required" in error_msg or "400" in error_msg:
            import logging
            logging.getLogger(__name__).warning(
                "Qdrant filter failed (missing index?): %s. Retrying without filters.", error_msg[:120]
            )
            # Try to create indexes for next time
            _ensure_payload_indexes()
            # Fall back to unfiltered search
            return client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vector,
                query_filter=None,
                limit=top_k,
                with_payload=True,
            )
        raise


def _ensure_payload_indexes():
    """Try to create payload indexes on Qdrant collection (idempotent, safe to call multiple times)."""
    try:
        from qdrant_client.models import PayloadSchemaType
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="subject",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="class",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        import logging
        logging.getLogger(__name__).info("Created payload indexes for 'subject' and 'class'")
    except Exception:
        pass  # Indexes might already exist or we lack permissions — both are fine


def search_chunks(
    query: str, subject: str = None, class_level: str = None, top_k: int = 3
):
    """
    Given a student's question, find the top_k most relevant NCERT chunks.
    Optionally filter by subject and class.
    If subject is None or "auto", auto-detect from query text.
    """

    # Auto-detect subject if not specified or set to "auto"
    if not subject or subject.strip().lower() == "auto":
        subject = detect_subject(query)

    raw_subject = str(subject).strip() if subject else None
    subject = _normalize_subject(subject)
    class_level = _normalize_class_level(class_level)

    query_vector = model.encode(query).tolist()

    subject_candidates = []
    for candidate in (
        subject,
        raw_subject,
        raw_subject.title() if raw_subject else None,
    ):
        if candidate and candidate not in subject_candidates:
            subject_candidates.append(candidate)

    if subject_candidates:
        results = None
        for candidate in subject_candidates:
            filters = _build_filters(candidate, class_level)
            results = _query_with_filters(query_vector, filters, top_k)
            if results.points:
                break
    else:
        filters = _build_filters(None, class_level)
        results = _query_with_filters(query_vector, filters, top_k)

    # If class metadata is missing/sparse, still return relevant subject matches.
    if not results.points and subject_candidates and class_level:
        for candidate in subject_candidates:
            relaxed_filters = _build_filters(subject=candidate, class_level=None)
            results = _query_with_filters(query_vector, relaxed_filters, top_k)
            if results.points:
                break

    # Format for LLM injection
    chunks = []
    for r in results.points:
        chunks.append(
            {
                "text": r.payload.get("answer", ""),
                "question": r.payload.get("question", ""),
                "subject": r.payload.get("subject", ""),
                "class": r.payload.get("class", ""),
                "chapter": r.payload.get("chapter", ""),
                "score": round(r.score, 3),  # cosine similarity score
            }
        )

    return chunks
