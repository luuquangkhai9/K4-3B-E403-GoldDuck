"""BM25 with Unicode tokenization and a dependency-free emergency fallback."""

from collections import Counter
import math
import re
import unicodedata

STOP_WORDS = set(
    "là gì như thế nào và hay hoặc của cho có các những một được trong với "
    "để về này đó khi thì bằng từ sẽ ra sao dùng the a an is are what how "
    "does do of to in and or for with".split()
)


def tokenize(text: str) -> list[str]:
    return [
        token for token in re.findall(r"[^\W_]+", unicodedata.normalize("NFC", text).casefold())
        if token not in STOP_WORDS
    ]


class BM25Index:
    def __init__(self, texts: list[str]):
        self.tokens = [tokenize(text) for text in texts]
        self.backend = None
        if any(self.tokens):
            try:
                from rank_bm25 import BM25Okapi

                self.backend = BM25Okapi(self.tokens)
                # Positive IDF keeps frequent query terms from reversing the
                # relevance order, and matches the emergency fallback formula.
                size = len(self.tokens)
                self.backend.idf = {
                    token: math.log(1 + (size - df + 0.5) / (df + 0.5))
                    for token, df in Counter(
                        token for tokens in self.tokens for token in set(tokens)
                    ).items()
                }
            except ImportError:
                pass
        self.counts = [Counter(tokens) for tokens in self.tokens]
        self.average_length = sum(map(len, self.tokens)) / max(1, len(texts))
        self.document_frequency = Counter(
            token for tokens in self.tokens for token in set(tokens)
        )

    def search(self, question: str, limit: int = 20) -> list[tuple[int, float]]:
        query = tokenize(question)
        if not query or not self.tokens or limit <= 0:
            return []
        if self.backend is not None:
            scores = self.backend.get_scores(query)
        else:
            scores = []
            size = len(self.tokens)
            for tokens, counts in zip(self.tokens, self.counts):
                score = 0.0
                for token in query:
                    frequency = counts[token]
                    if not frequency:
                        continue
                    df = self.document_frequency[token]
                    idf = math.log(1 + (size - df + 0.5) / (df + 0.5))
                    denominator = frequency + 1.5 * (
                        0.25 + 0.75 * len(tokens) / max(1, self.average_length)
                    )
                    score += idf * frequency * 2.5 / denominator
                scores.append(score)
        # Never return slides with no matching token.
        query_tokens = set(query)
        candidates = [
            (index, float(score))
            for index, score in enumerate(scores)
            if query_tokens.intersection(self.counts[index])
        ]
        return sorted(candidates, key=lambda item: (-item[1], item[0]))[:limit]
