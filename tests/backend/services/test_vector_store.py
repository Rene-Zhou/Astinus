"""Tests for VectorStoreService."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.backend.services.embedding import QwenEmbeddingFunction
from src.backend.services.vector_store import VectorStoreService, get_vector_store


class TestVectorStoreServiceUnit:
    """Unit tests for VectorStoreService (with mocked ChromaDB)."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        VectorStoreService.reset_instance()
        yield
        VectorStoreService.reset_instance()

    def test_singleton_pattern(self):
        """Test that VectorStoreService implements singleton pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store1 = VectorStoreService(tmpdir)
            store2 = VectorStoreService(tmpdir)

            assert store1 is store2

    def test_custom_db_path(self):
        """Test initialization with custom database path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStoreService(tmpdir)

            assert store.db_path == Path(tmpdir)
            assert store.db_path.exists()

    def test_default_db_path(self):
        """Test initialization with default database path."""
        store = VectorStoreService()

        # Should create data/chroma_db relative to project root
        assert "data" in str(store.db_path)
        assert "chroma_db" in str(store.db_path)

    @patch("src.backend.services.vector_store.chromadb.PersistentClient")
    def test_lazy_client_initialization(self, mock_client_class):
        """Test that ChromaDB client is created lazily."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStoreService(tmpdir)

            # Client should not be created yet
            mock_client_class.assert_not_called()

            # Access client
            store._get_client()

            # Now client should be created
            mock_client_class.assert_called_once_with(path=tmpdir)

    @patch("src.backend.services.vector_store.chromadb.PersistentClient")
    def test_get_or_create_collection(self, mock_client_class):
        """Test get_or_create_collection creates collection."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStoreService(tmpdir)
            collection = store.get_or_create_collection("test_collection")

            assert collection is mock_collection
            # Verify the call was made with correct parameters
            call_args = mock_client.get_or_create_collection.call_args
            assert call_args[1]["name"] == "test_collection"
            # Metadata should include hnsw:space=cosine configuration
            assert call_args[1]["metadata"] == {"hnsw:space": "cosine"}
            # embedding_function should be a QwenEmbeddingFunction instance (cached)
            assert isinstance(call_args[1]["embedding_function"], QwenEmbeddingFunction)

    @patch("src.backend.services.vector_store.chromadb.PersistentClient")
    def test_add_documents_with_ids(self, mock_client_class):
        """Test adding documents with explicit IDs."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStoreService(tmpdir)
            store.add_documents(
                collection_name="test",
                documents=["doc1", "doc2"],
                metadatas=[{"key": "val1"}, {"key": "val2"}],
                ids=["id1", "id2"],
            )

            mock_collection.add.assert_called_once_with(
                documents=["doc1", "doc2"],
                metadatas=[{"key": "val1"}, {"key": "val2"}],
                ids=["id1", "id2"],
            )

    @patch("src.backend.services.vector_store.chromadb.PersistentClient")
    def test_add_documents_auto_generates_ids(self, mock_client_class):
        """Test that IDs are auto-generated when not provided."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStoreService(tmpdir)
            store.add_documents(
                collection_name="test",
                documents=["doc1", "doc2"],
            )

            # Check that auto-generated IDs were used
            call_args = mock_collection.add.call_args
            assert call_args[1]["documents"] == ["doc1", "doc2"]
            assert call_args[1]["ids"] == ["doc_0", "doc_1"]

    @patch("src.backend.services.vector_store.chromadb.PersistentClient")
    def test_add_documents_mismatched_lengths(self, mock_client_class):
        """Test that mismatched lengths raise ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStoreService(tmpdir)

            with pytest.raises(ValueError, match="metadatas must have same length"):
                store.add_documents(
                    collection_name="test",
                    documents=["doc1", "doc2"],
                    metadatas=[{"key": "val1"}],  # Only one metadata
                )

            with pytest.raises(ValueError, match="ids must have same length"):
                store.add_documents(
                    collection_name="test",
                    documents=["doc1", "doc2"],
                    ids=["id1"],  # Only one ID
                )

    @patch("src.backend.services.vector_store.chromadb.PersistentClient")
    def test_search(self, mock_client_class):
        """Test search functionality."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection

        # Mock search results
        mock_results = {
            "documents": [["doc1", "doc2"]],
            "metadatas": [[{"key": "val1"}, {"key": "val2"}]],
            "distances": [[0.1, 0.2]],
        }
        mock_collection.query.return_value = mock_results

        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStoreService(tmpdir)
            results = store.search(
                collection_name="test",
                query_text="search query",
                n_results=2,
            )

            assert results == mock_results
            mock_collection.query.assert_called_once_with(
                query_texts=["search query"],
                n_results=2,
                where=None,
                include=["documents", "metadatas", "distances"],
            )

    @patch("src.backend.services.vector_store.chromadb.PersistentClient")
    def test_search_with_metadata_filter(self, mock_client_class):
        """Test search with metadata filtering."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_collection = Mock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_collection.query.return_value = {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStoreService(tmpdir)
            store.search(
                collection_name="test",
                query_text="query",
                where={"lang": "cn"},
            )

            call_args = mock_collection.query.call_args
            assert call_args[1]["where"] == {"lang": "cn"}

    @patch("src.backend.services.vector_store.chromadb.PersistentClient")
    def test_delete_collection(self, mock_client_class):
        """Test deleting a collection."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStoreService(tmpdir)
            store.delete_collection("test_collection")

            mock_client.delete_collection.assert_called_once_with(name="test_collection")

    @patch("src.backend.services.vector_store.chromadb.PersistentClient")
    def test_delete_nonexistent_collection(self, mock_client_class):
        """Test deleting non-existent collection doesn't raise error."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.delete_collection.side_effect = ValueError("Collection not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStoreService(tmpdir)
            # Should not raise
            store.delete_collection("nonexistent")

    @patch("src.backend.services.vector_store.chromadb.PersistentClient")
    def test_list_collections(self, mock_client_class):
        """Test listing all collections."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock collections
        mock_col1 = Mock()
        mock_col1.name = "collection1"
        mock_col2 = Mock()
        mock_col2.name = "collection2"
        mock_client.list_collections.return_value = [mock_col1, mock_col2]

        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStoreService(tmpdir)
            collections = store.list_collections()

            assert collections == ["collection1", "collection2"]

    @patch("src.backend.services.vector_store.chromadb.PersistentClient")
    def test_get_collection_count(self, mock_client_class):
        """Test getting document count in collection."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_collection = Mock()
        mock_collection.count.return_value = 42
        mock_client.get_or_create_collection.return_value = mock_collection

        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStoreService(tmpdir)
            count = store.get_collection_count("test")

            assert count == 42

    def test_reset_instance(self):
        """Test resetting singleton instance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store1 = VectorStoreService(tmpdir)
            VectorStoreService.reset_instance()
            store2 = VectorStoreService(tmpdir)

            # After reset, should be different instance
            assert store1 is not store2

    def test_get_vector_store_global(self):
        """Test global accessor function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store1 = get_vector_store(tmpdir)
            store2 = get_vector_store()

            # Should return same instance
            assert store1 is store2


class TestVectorStoreServiceIntegration:
    """Integration tests with real ChromaDB."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        VectorStoreService.reset_instance()
        yield
        VectorStoreService.reset_instance()

    def test_real_add_and_search(self):
        """Test adding and searching documents with real ChromaDB."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStoreService(tmpdir)

            # Add documents
            store.add_documents(
                collection_name="test_real",
                documents=[
                    "The cat sat on the mat",
                    "The dog played in the park",
                    "A bird flew over the tree",
                ],
                metadatas=[
                    {"animal": "cat"},
                    {"animal": "dog"},
                    {"animal": "bird"},
                ],
                ids=["doc1", "doc2", "doc3"],
            )

            # Search
            results = store.search(
                collection_name="test_real",
                query_text="feline on carpet",
                n_results=2,
            )

            # Should find cat document first (most similar)
            assert len(results["documents"][0]) == 2
            assert "cat" in results["documents"][0][0].lower()

    def test_real_metadata_filtering(self):
        """Test metadata filtering with real ChromaDB."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = VectorStoreService(tmpdir)

            store.add_documents(
                collection_name="test_filter",
                documents=["Doc in Chinese", "Doc in English", "Another Chinese doc"],
                metadatas=[{"lang": "cn"}, {"lang": "en"}, {"lang": "cn"}],
                ids=["1", "2", "3"],
            )

            # Search only Chinese documents
            results = store.search(
                collection_name="test_filter",
                query_text="document",
                where={"lang": "cn"},
                n_results=5,
            )

            # Should only return Chinese documents
            assert len(results["documents"][0]) == 2
            for metadata in results["metadatas"][0]:
                assert metadata["lang"] == "cn"

    def test_real_persistence(self):
        """Test that data persists across service instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # First instance - add data
            store1 = VectorStoreService(tmpdir)
            store1.add_documents(
                collection_name="persistent",
                documents=["Test document"],
                ids=["doc1"],
            )

            # Reset singleton
            VectorStoreService.reset_instance()

            # Second instance - should find existing data
            store2 = VectorStoreService(tmpdir)
            count = store2.get_collection_count("persistent")

            assert count == 1
