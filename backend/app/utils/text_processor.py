import re
import unicodedata
from typing import FrozenSet, List, Dict

ENGLISH_STOPWORDS: FrozenSet[str] = frozenset(
    {
        "a",
        "about",
        "above",
        "after",
        "again",
        "against",
        "ain",
        "all",
        "am",
        "an",
        "and",
        "any",
        "are",
        "aren",
        "aren't",
        "as",
        "at",
        "be",
        "because",
        "been",
        "before",
        "being",
        "below",
        "between",
        "both",
        "but",
        "by",
        "can",
        "couldn",
        "couldn't",
        "d",
        "did",
        "didn",
        "didn't",
        "do",
        "does",
        "doesn",
        "doesn't",
        "doing",
        "don",
        "don't",
        "down",
        "during",
        "each",
        "few",
        "for",
        "from",
        "further",
        "had",
        "hadn",
        "hadn't",
        "has",
        "hasn",
        "hasn't",
        "have",
        "haven",
        "haven't",
        "having",
        "he",
        "her",
        "here",
        "hers",
        "herself",
        "him",
        "himself",
        "his",
        "how",
        "i",
        "if",
        "in",
        "into",
        "is",
        "isn",
        "isn't",
        "it",
        "it's",
        "its",
        "itself",
        "just",
        "ll",
        "m",
        "ma",
        "me",
        "mightn",
        "mightn't",
        "more",
        "most",
        "mustn",
        "mustn't",
        "my",
        "myself",
        "needn",
        "needn't",
        "no",
        "nor",
        "not",
        "now",
        "o",
        "of",
        "off",
        "on",
        "once",
        "only",
        "or",
        "other",
        "our",
        "ours",
        "ourselves",
        "out",
        "over",
        "own",
        "re",
        "s",
        "same",
        "shan",
        "shan't",
        "she",
        "she's",
        "should",
        "should've",
        "shouldn",
        "shouldn't",
        "so",
        "some",
        "such",
        "t",
        "than",
        "that",
        "that'll",
        "the",
        "their",
        "theirs",
        "them",
        "themselves",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "to",
        "too",
        "under",
        "until",
        "up",
        "ve",
        "very",
        "was",
        "wasn",
        "wasn't",
        "we",
        "were",
        "weren",
        "weren't",
        "what",
        "when",
        "where",
        "which",
        "while",
        "who",
        "whom",
        "why",
        "will",
        "with",
        "won",
        "won't",
        "wouldn",
        "wouldn't",
        "y",
        "you",
        "you'd",
        "you'll",
        "you're",
        "you've",
        "your",
        "yours",
        "yourself",
        "yourselves",
    }
)

_ABBREVIATION_PATTERNS: List[str] = [
    r"\bDr\.",
    r"\bMr\.",
    r"\bMrs\.",
    r"\bMs\.",
    r"\bProf\.",
    r"\bSr\.",
    r"\bJr\.",
    r"\bRev\.",
    r"\bHon\.",
    r"\be\.g\.",
    r"\bi\.e\.",
    r"\betc\.",
    r"\bvs\.",
    r"\bal\.",
    r"\bInc\.",
    r"\bLtd\.",
    r"\bCorp\.",
    r"\bCo\.",
    r"\bDept\.",
    r"\bEst\.",
    r"\bApprox\.",
    r"\bApt\.",
    r"\bPh\.D\.",
    r"\bM\.D\.",
    r"\bB\.Tech\.",
    r"\bM\.Tech\.",
    r"\bB\.Sc\.",
    r"\bM\.Sc\.",
    r"\bB\.A\.",
    r"\bM\.A\.",
    r"\bB\.E\.",
    r"\bM\.E\.",
    r"\bB\.S\.",
    r"\bM\.S\.",
    r"\b[A-Z]\.",
]


def normalize_text(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""

    normalized = unicodedata.normalize("NFKD", text)
    return re.sub(r"\s+", " ", normalized).strip()


def clean_text(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""

    cleaned = re.sub(r"[^a-zA-Z0-9\s.,@+\-]", " ", text)
    return re.sub(r"\s+", " ", cleaned).strip()


def segment_sentences(text: str) -> List[str]:
    if not text or not isinstance(text, str):
        return []

    stripped = text.strip()
    if not stripped:
        return []

    placeholder = "@@DOT@@"
    processed = stripped

    for pattern in _ABBREVIATION_PATTERNS:

        def _mask_dot(match: re.Match) -> str:
            return match.group(0).replace(".", placeholder)

        processed = re.sub(pattern, _mask_dot, processed, flags=re.IGNORECASE)

    raw_segments = re.split(r"(?<=[.!?])\s+|\r?\n+", processed)

    sentences: List[str] = []
    for segment in raw_segments:
        restored = segment.replace(placeholder, ".").strip()
        if restored:
            sentences.append(restored)

    return sentences


def tokenize(text: str) -> List[str]:
    if not text or not isinstance(text, str):
        return []

    return re.findall(r"\b\w+\b", text)


def remove_stopwords(
    tokens: List[str], extra_stopwords: List[str] = None
) -> List[str]:
    if not tokens:
        return []

    stopwords = set(ENGLISH_STOPWORDS)
    if extra_stopwords:
        stopwords.update(word.lower() for word in extra_stopwords if word)

    return [token for token in tokens if token.lower() not in stopwords]


def preprocess_for_tfidf(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""

    normalized = normalize_text(text)
    cleaned = clean_text(normalized)
    tokens = tokenize(cleaned)
    filtered = remove_stopwords(tokens)

    return " ".join(t.lower() for t in filtered)


def preprocess_for_embedding(text: str) -> str:
    if not text or not isinstance(text, str):
        return ""

    normalized = normalize_text(text)
    return clean_text(normalized)


# Skill alias mappings for normalization
_SKILL_ALIASES: Dict[str, str] = {
    "js": "javascript",
    "node": "node.js",
    "nodejs": "node.js",
    "postgre": "postgresql",
    "postgres": "postgresql",
    "mongo": "mongodb",
    "mysql": "mysql",
    "redis": "redis",
    "oop": "object-oriented programming",
    "rest": "rest api",
    "restful": "rest api",
    "graphql": "graphql",
    "ts": "typescript",
    "py": "python",
    "golang": "go",
    "cs": "c#",
    "cpp": "c++",
    ".net": ".net",
    "asp": "asp.net",
    "ml": "machine learning",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "ai": "artificial intelligence",
    "ci/cd": "cicd",
    "devops": "devops",
    "aws": "aws",
    "azure": "azure",
    "gcp": "gcp",
    "k8s": "kubernetes",
    "k8": "kubernetes",
    "tf": "tensorflow",
    "torch": "pytorch",
    "sklearn": "scikit-learn",
    "pandas": "pandas",
    "numpy": "numpy",
    "reactjs": "react",
    "angularjs": "angular",
    "vuejs": "vue.js",
    "express": "express.js",
    "nest": "nestjs",
    "next": "next.js",
    "nuxt": "nuxt.js",
    "docker": "docker",
    "k8": "kubernetes",
    "tf": "terraform",
    "tdd": "test-driven development",
    "bdd": "behavior-driven development",
    "agile": "agile",
    "scrum": "scrum",
    "kanban": "kanban",
    "git": "git",
    "github": "github",
    "gitlab": "gitlab",
    "jira": "jira",
    "linux": "linux",
    "unix": "unix",
    "sql": "sql",
    "nosql": "nosql",
    "html": "html",
    "css": "css",
    "sass": "sass",
    "scss": "sass",
    "less": "less",
    "webpack": "webpack",
    "vite": "vite",
    "npm": "npm",
    "yarn": "yarn",
    "pnpm": "pnpm",
    
    # REST API variations
    "rest apis": "rest api",
    "restful api": "rest api",
    "restful services": "rest api",
    "rest api development": "rest api",
    
    # Object-Oriented Programming variations
    "object oriented programming": "object-oriented programming",
    "object-oriented design": "object-oriented programming",
    "object-oriented principles": "object-oriented programming",
    
    # SQL variations
    "structured query language": "sql",
    "sql querying": "sql",
    "sql queries": "sql",
    
    # PostgreSQL variations
    "postgresql database": "postgresql",
    "postgresql databases": "postgresql",
}

def normalize_skill_name(skill: str) -> str:
    if not skill or not isinstance(skill, str):
        return ""

    normalized = re.sub(r"\s+", " ", skill.strip().lower())
    
    # Apply alias mapping
    return _SKILL_ALIASES.get(normalized, normalized)
