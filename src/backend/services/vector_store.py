"""
Vector store service using ChromaDB for semantic search.

Provides embedding-based search for lore entries, NPC memories, and conversation history.
Uses singleton pattern to ensure single ChromaDB client instance.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.types import EmbeddingFunction

from src.backend.services.embedding import QwenEmbeddingFunction


class VectorStoreService:
    """
    Service for managing vector embeddings and semantic search.

    Uses ChromaDB with persistent storage for:
    - Lore entries (world pack knowledge)
    - NPC memories (character event history)
    - Conversation history (dialogue context)

    Examples:
        >>> store = VectorStoreService()
        >>> collection = store.get_or_create_collection("test_collection")
        >>> store.add_documents(
        ...     collection_name="test_collection",
        ...     documents=["Doc 1", "Doc 2"],
        ...     metadatas=[{"key": "value1"}, {"key": "value2"}],
        ...     ids=["1", "2"]
        ... )
        >>> results = store.search(
        ...     collection_name="test_collection",
        ...     query_text="Doc",
        ...     n_results=2
        ... )
    """

    _instance: VectorStoreService | None = None
    _client: chromadb.PersistentClient | None = None

    def __new__(cls, db_path: str | Path | None = None) -> VectorStoreService:
        """
        Implement singleton pattern.

        Args:
            db_path: Optional custom database path (only used on first instantiation)

        Returns:
            Singleton instance of VectorStoreService
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: str | Path | None = None):
        """
        Initialize vector store service.

        Args:
            db_path: Path to ChromaDB persistent storage (default: ./data/chroma_db)
        """
        # Only initialize once (singleton pattern)
        if self._initialized:
            return

        if db_path is None:
            # Default to data/chroma_db relative to project root
            project_root = Path(__file__).parent.parent.parent.parent
            db_path = project_root / "data" / "chroma_db"

        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)

        # Lazy initialization - client created on first use
        self._client = None
        self._cached_embedding_function: EmbeddingFunction | None = None
        self._initialized = True

    def _get_client(self) -> chromadb.PersistentClient:
        """
        Get or create ChromaDB client (lazy initialization).

        Returns:
            ChromaDB persistent client
        """
        if self._client is None:
            self._client = chromadb.PersistentClient(path=str(self.db_path))
        return self._client

    def get_or_create_collection(
        self,
        name: str,
        metadata: dict[str, Any] | None = None,
        embedding_function: EmbeddingFunction | None = None,
    ) -> chromadb.Collection:
        """
        Get existing collection or create new one.

        Uses Qwen3-Embedding-0.6B by default for multilingual support with
        cosine distance metric for semantic similarity.

        The embedding function is cached to prevent repeatedly loading the model.

        Args:
            name: Collection name
            metadata: Optional collection metadata (will add hnsw:space="cosine")
            embedding_function: Optional custom embedding function
                                (default: Qwen3-Embedding-0.6B, cached)

        Returns:
            ChromaDB collection
        """
        # Use cached QwenEmbeddingFunction by default to avoid reloading the model
        if embedding_function is None:
            if self._cached_embedding_function is None:
                self._cached_embedding_function = QwenEmbeddingFunction()
            embedding_function = self._cached_embedding_function

        # Configure cosine distance for normalized embeddings
        if metadata is None:
            metadata = {}
        metadata["hnsw:space"] = "cosine"

        client = self._get_client()
        return client.get_or_create_collection(
            name=name,
            metadata=metadata,
            embedding_function=embedding_function,
        )

    def add_documents(
        self,
        collection_name: str,
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        ids: list[str] | None = None,
    ) -> None:
        """
        Add documents to a collection with automatic embedding.

        Args:
            collection_name: Name of the collection
            documents: List of document texts
            metadatas: Optional list of metadata dicts (one per document)
            ids: Optional list of unique IDs (auto-generated if not provided)

        Raises:
            ValueError: If documents, metadatas, and ids have mismatched lengths
        """
        if metadatas and len(metadatas) != len(documents):
            raise ValueError("metadatas must have same length as documents")

        if ids and len(ids) != len(documents):
            raise ValueError("ids must have same length as documents")

        # Auto-generate IDs if not provided
        if ids is None:
            ids = [f"doc_{i}" for i in range(len(documents))]

        collection = self.get_or_create_collection(collection_name)
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )

    def search(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 5,
        where: dict[str, Any] | None = None,
        include: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Search for similar documents using semantic similarity.

        Args:
            collection_name: Name of the collection to search
            query_text: Query text for semantic search
            n_results: Number of results to return (default: 5)
            where: Optional metadata filter (e.g., {"lang": "cn"})
            include: Optional list of fields to include in results
                    (default: ["documents", "metadatas", "distances"])

        Returns:
            Search results dictionary with keys:
            - documents: List of matching document texts
            - metadatas: List of metadata dicts
            - distances: List of similarity distances (lower = more similar)
            - ids: List of document IDs

        Raises:
            ValueError: If collection doesn't exist
        """
        if include is None:
            include = ["documents", "metadatas", "distances"]

        try:
            collection = self.get_or_create_collection(collection_name)
        except Exception as e:
            raise ValueError(f"Collection '{collection_name}' not found: {e}") from e

        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where,
            include=include,  # type: ignore
        )

        return results

    def delete_collection(self, collection_name: str) -> None:
        """
        Delete a collection and all its documents.

        Args:
            collection_name: Name of the collection to delete
        """
        client = self._get_client()
        with contextlib.suppress(ValueError):
            client.delete_collection(name=collection_name)

    def get_collection_metadata(self, collection_name: str) -> dict[str, Any] | None:
        """
        Get metadata for an existing collection.

        Args:
            collection_name: Name of the collection

        Returns:
            Collection metadata dict, or None if collection doesn't exist
        """
        client = self._get_client()
        try:
            collection = client.get_collection(name=collection_name)
            return collection.metadata
        except Exception:
            return None

    def list_collections(self) -> list[str]:
        """
        List all collection names.

        Returns:
            List of collection names
        """
        client = self._get_client()
        collections = client.list_collections()
        return [col.name for col in collections]

    def get_collection_count(self, collection_name: str) -> int:
        """
        Get document count in a collection.

        Args:
            collection_name: Name of the collection

        Returns:
            Number of documents in the collection

        Raises:
            ValueError: If collection doesn't exist
        """
        try:
            collection = self.get_or_create_collection(collection_name)
            return collection.count()
        except Exception as e:
            raise ValueError(f"Collection '{collection_name}' not found: {e}") from e

    @classmethod
    def reset_instance(cls) -> None:
        """
        Reset singleton instance (useful for testing).

        Warning: This will close the current client and reset the singleton.
        Explicitly deletes the ML model to free memory (important for testing).
        """
        if cls._instance is not None:
            if cls._instance._client is not None:
                # ChromaDB client doesn't need explicit close
                cls._instance._client = None
            # Explicitly delete embedding function to free ML model memory
            if cls._instance._cached_embedding_function is not None:
                del cls._instance._cached_embedding_function
                cls._instance._cached_embedding_function = None
            cls._instance = None
        # Force garbage collection to release large model memory
        import gc

        gc.collect()


# Global singleton accessor
_global_store: VectorStoreService | None = None


def get_vector_store(db_path: str | Path | None = None) -> VectorStoreService:
    """
    Get the global vector store instance.

    Args:
        db_path: Optional custom database path (only used on first call)

    Returns:
        Global VectorStoreService instance
    """
    global _global_store
    if _global_store is None:
        _global_store = VectorStoreService(db_path)
    return _global_store
