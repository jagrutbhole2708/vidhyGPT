import logging

from video.gemini_client import GeminiClientError, generate_text

logging.basicConfig(level=logging.INFO)


def main() -> None:
    prompt = "Explain Newton's First Law in 3 short bullet points for Class 9 students."
    try:
        output = generate_text(prompt)
        print(output)
    except GeminiClientError as exc:
        logging.error("Gemini generation failed: %s", exc)


if __name__ == "__main__":
    main()
