import sys
from pathlib import Path

import pytest

_svc = str(Path(__file__).parent.parent)
if _svc not in sys.path:
    sys.path.insert(0, _svc)


class _FakeEncoding:
    """Character-level tokenizer: one char = one token ID (unicode codepoint).

    Satisfies tiktoken's Encoding interface for unit tests without requiring
    the cl100k_base BPE file to be downloaded from the internet.
    """

    def encode(self, text: str) -> list[int]:
        return [ord(c) for c in text]

    def decode(self, ids: list[int]) -> str:
        return "".join(chr(i) for i in ids)


@pytest.fixture(autouse=True, scope="session")
def _mock_tiktoken(session_mocker=None):
    """Patch tiktoken.get_encoding for the entire test session."""
    import unittest.mock as mock

    fake = _FakeEncoding()
    with mock.patch("tiktoken.get_encoding", return_value=fake):
        yield fake
