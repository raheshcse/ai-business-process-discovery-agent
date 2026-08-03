from abc import ABC, abstractmethod

from app.rag.retrieval.models import RetrievalRequest, RetrievalResponse


class Retriever(ABC):
    @abstractmethod
    def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        """Retrieve ranked chunks relevant to a natural-language query."""
