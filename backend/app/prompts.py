EMOTION_PROMPT_VERSION = "emotion-v2-evidence"

EMOTION_QUESTIONS = {
    "anxiety": {
        "type": "score",
        "instructions": (
            "Rate ANXIETY OR WORRY expressed by the CURRENT USER MESSAGE. Recent context only "
            "resolves references. Judge expressed emotion, not objective seriousness or diagnosis. "
            "Ignore emotion spoken only by the assistant, attributed to another person, quoted, "
            "hypothetical, or explicitly negated. Anxiety includes anticipatory worry, nervousness, "
            "uncertainty, rumination and dread about possible outcomes; distinguish it from fear "
            "of a specific perceived danger."
        ),
        "criteria": [
            "No meaningful anxiety or worry expressed",
            "Slight or weak anxiety or worry",
            "Clear moderate anxiety or worry",
            "Strong anxiety or worry central to the message",
            "Very intense or overwhelming anxiety or worry",
        ],
    },
    "sadness": {
        "type": "score",
        "instructions": (
            "Rate SADNESS expressed by the CURRENT USER MESSAGE. Recent context only resolves "
            "references. Judge expressed emotion without diagnosis. Ignore sadness spoken only by "
            "the assistant, attributed to another person, quoted, hypothetical, or explicitly negated. "
            "Sadness includes sorrow, grief, disappointment, hurt, loneliness and feeling down."
        ),
        "criteria": [
            "No meaningful sadness expressed",
            "Slight or weak sadness",
            "Clear moderate sadness",
            "Strong sadness central to the message",
            "Very intense or overwhelming sadness or grief",
        ],
    },
    "fear": {
        "type": "score",
        "instructions": (
            "Rate how SCARED OR AFRAID the user appears in the CURRENT USER MESSAGE. Recent context "
            "only resolves references. Fear includes feeling frightened, unsafe, threatened or "
            "responding to a specific perceived danger. 'I am scared' counts even about the future. "
            "Distinguish ordinary uncertain worry from fear. Ignore fear spoken only by the assistant, "
            "attributed to someone else, quoted, hypothetical, or explicitly negated."
        ),
        "criteria": [
            "No meaningful fear expressed",
            "Slight or weak fear",
            "Clear moderate fear",
            "Strong fear central to the message",
            "Very intense fear or feeling seriously threatened",
        ],
    },
}
