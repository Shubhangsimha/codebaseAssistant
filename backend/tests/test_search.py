"""Unit tests for FAISSStore and search mechanics (no DB, no network)."""
import numpy as np
import pytest

from app.ingestion.embedder import Embedder, FAISSStore


TEXTS = [
    "def authenticate_user(username, password): ...",
    "def get_database_connection(): ...",
    "class UserRepository: ...",
    "SELECT * FROM users WHERE id = ?",
    "def hash_password(plain): ...",
    "router.get('/health', handler)",
    "import jwt from 'jsonwebtoken'",
    "CREATE TABLE sessions (id, token, user_id)",
    "def logout_user(session_id): ...",
    "module.exports = { router }",
]


@pytest.fixture(scope="module")
def embedder():
    return Embedder()


@pytest.fixture()
def store_with_data(embedder, tmp_path):
    embeddings = embedder.embed_batch(TEXTS)
    chunk_ids = list(range(10, 10 + len(TEXTS)))  # fake DB ids 10..19
    store = FAISSStore(project_id=1, data_dir=tmp_path)
    store.create_index(embeddings, chunk_ids)
    return store, chunk_ids


def test_index_size(store_with_data):
    store, chunk_ids = store_with_data
    assert store.size == len(TEXTS)


def test_files_created(store_with_data, tmp_path):
    assert (tmp_path / "faiss" / "1.faiss").exists()
    assert (tmp_path / "faiss" / "1.meta.json").exists()


def test_load_roundtrip(store_with_data, tmp_path, embedder):
    original_store, chunk_ids = store_with_data
    loaded = FAISSStore.load_for_project(project_id=1, data_dir=tmp_path)
    assert loaded.size == len(TEXTS)


def test_search_returns_correct_count(store_with_data, embedder):
    store, _ = store_with_data
    query_vec = embedder.embed_batch(["authentication"])[0]
    distances, ids = store.search(query_vec, top_k=3)
    assert len(ids) == 3
    assert len(distances) == 3


def test_search_auth_query_top_result(store_with_data, embedder):
    store, chunk_ids = store_with_data
    query_vec = embedder.embed_batch(["user authentication login"])[0]
    distances, ids = store.search(query_vec, top_k=5)
    # chunk_id 10 = TEXTS[0] = authenticate_user, should be in top 5
    assert chunk_ids[0] in ids  # authenticate_user is chunk_id 10


def test_search_scores_ordered(store_with_data, embedder):
    store, _ = store_with_data
    query_vec = embedder.embed_batch(["database connection"])[0]
    distances, ids = store.search(query_vec, top_k=5)
    for i in range(len(distances) - 1):
        assert distances[i] >= distances[i + 1]


def test_all_result_fields_present(store_with_data, embedder):
    store, chunk_ids = store_with_data
    query_vec = embedder.embed_batch(["jwt token session"])[0]
    distances, ids = store.search(query_vec, top_k=3)
    assert len(ids) > 0
    for cid in ids:
        assert cid in chunk_ids
