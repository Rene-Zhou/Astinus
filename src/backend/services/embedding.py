"""
Embedding functions for vector store.

Provides custom embedding functions for ChromaDB using sentence-transformers.
"""

from chromadb.api.types import EmbeddingFunction
from sentence_transformers import SentenceTransformer


class QwenEmbeddingFunction(EmbeddingFunction):
    """
    Qwen3-Embedding-0.6B for multilingual text embedding.

    Uses the Qwen3-Embedding-0.6B model which supports 100+ languages
    with excellent performance on Chinese and English text.

    The model produces normalized embeddings, which are compatible with
    cosine similarity distance metrics in ChromaDB.

    Examples:
        >>> embedding_fn = QwenEmbeddingFunction()
        >>> embeddings = embedding_fn(["Hello world", "你好世界"])
        >>> len(embeddings)
        2
        >>> len(embeddings[0])
        1024
    """

    def __init__(self, model_name: str = "Qwen/Qwen3-Embedding-0.6B", device: str = "cpu"):
        """
        Initialize the Qwen embedding function.

        Args:
            model_name: Hugging Face model name to use.
                       Default: "Qwen/Qwen3-Embedding-0.6B"
            device: Device to run the model on ("cpu" or "cuda").
                   Default: "cpu" for compatibility
        """
        self.model = SentenceTransformer(model_name, device=device)

    def __call__(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (each as a list of floats)
        """
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,  # Important: normalize for cosine similarity
            show_progress_bar=False,
        )
        return embeddings.tolist()


class DefaultEmbeddingFunction(EmbeddingFunction):
    """
    Fallback embedding function using all-MiniLM-L6-v2.

    This is a smaller model that works well for English text
    but has limited support for Chinese and other languages.

    Only use this if Qwen3-Embedding is not available.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", device: str = "cpu"):
        """
        Initialize the default embedding function.

        Args:
            model_name: Hugging Face model name to use
            device: Device to run the model on ("cpu" or "cuda")
        """
        self.model = SentenceTransformer(model_name, device=device)

    def __call__(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (each as a list of floats)
        """
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()
