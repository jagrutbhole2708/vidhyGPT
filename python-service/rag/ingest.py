from datasets import load_dataset
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from tqdm import tqdm
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

# CONFIG
QUADRANT_URL=os.getenv("QUADRANT_URL")
QUADRANT_API_KEY=os.getenv("QUADRANT_API_KEY")
COLLECTION_NAME = "ncert"
EMBED_MODEL = "all-MiniLM-L6-v2"
BATCH_SIZE = 64
RECREATE_COLLECTION = os.getenv("RECREATE_COLLECTION", "false").lower() == "true"

client = QdrantClient(
    url=QUADRANT_URL,
    api_key=QUADRANT_API_KEY
    )
model = SentenceTransformer(EMBED_MODEL)


def _create_collection():
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=384,  # MiniLm gives 384 dims output, so setting this size
            distance=Distance.COSINE,
        ),
    )


def _pick_value(row, *keys):
    """Return the first non-empty value found in the provided keys."""
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _normalize_subject(value):
    text = str(value).strip().lower()
    return text


def _normalize_class(value):
    text = str(value).strip().lower()
    if not text:
        return ""

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


# create collection { only for the first time } if not there
if client.collection_exists(COLLECTION_NAME):
    if RECREATE_COLLECTION:
        client.delete_collection(COLLECTION_NAME)
        _create_collection()
        print(f"Collection Recreated: {COLLECTION_NAME}")
else:
    _create_collection()
    print(f"Collection Created: {COLLECTION_NAME}")

# Load the dataset
print("Loading dataset... NCERT dataset from Hugging Face")
dataset = load_dataset("KadamParth/Ncert_dataset", split="train")
print(dataset.column_names)
print(dataset[0])  # print first row to see actual data

# --- Ingest in batches ---
points = []

for i, row in enumerate(tqdm(dataset)):
    # Each row has: question, answer, subject, class, chapter, difficulty
    # We embed the answer (textbook content) and store question as metadata too
    question = _pick_value(row, "Question", "question")
    answer = _pick_value(row, "Answer", "answer")
    subject = _normalize_subject(_pick_value(row, "subject", "Subject"))
    class_level = _normalize_class(_pick_value(row, "class", "Class"))
    chapter = _pick_value(row, "chapter", "Chapter")
    difficulty = _pick_value(row, "difficulty", "Difficulty")

    text_to_embed = f"{question} {answer}".strip()  # combine for richer context

    payload = {
        "question": question,
        "answer": answer,
        "subject": subject,
        "class": class_level,
        "chapter": chapter,
        "difficulty": difficulty,
    }

    points.append((text_to_embed, payload))

    # uploading in batches
    if len(points) == BATCH_SIZE or i == len(dataset) - 1:
        texts = [p[0] for p in points]
        payloads = [p[1] for p in points]

        # embedding the texts
        embeddings = model.encode(texts, show_progress_bar=False)

        qdrant_points = [
            PointStruct(
                id=uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"{payloads[j]['question']}|{payloads[j]['answer']}|{payloads[j]['subject']}|{payloads[j]['class']}|{payloads[j]['chapter']}",
                ),
                vector=embeddings[j].tolist(),
                payload=payloads[j],
            )
            for j in range(len(points))
        ]

        client.upsert(collection_name=COLLECTION_NAME, points=qdrant_points)

        points = []  # reset for next batch

print("Ingestion completed!")
print(f"Total vectors in collection: {client.count(COLLECTION_NAME).count}")


# https://chatgpt.com/s/t_69c41c317f508191ba40c5be242d0ee8
# read this later for understanding what does this code do?


# running the qdrant docker locally
# docker run -p 6333:6333 -v ${PWD}\qdrant_data:/qdrant/storage qdrant/qdrant
