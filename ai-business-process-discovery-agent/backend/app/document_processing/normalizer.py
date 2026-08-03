import re


class TextNormalizer:
    _horizontal_whitespace = re.compile(r"[^\S\n]+")
    _repeated_blank_lines = re.compile(r"\n{3,}")

    def normalize(self, text: str) -> str:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        normalized = self._horizontal_whitespace.sub(" ", normalized)
        normalized = "\n".join(line.strip() for line in normalized.split("\n"))
        normalized = self._repeated_blank_lines.sub("\n\n", normalized)
        return normalized.strip()
