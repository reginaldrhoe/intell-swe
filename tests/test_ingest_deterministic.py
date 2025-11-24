from mcp.mcp import deterministic_embedding


def test_deterministic_embedding_shape_and_repeatability():
    text = "This is a deterministic test"
    v1 = deterministic_embedding(text, dim=64)
    v2 = deterministic_embedding(text, dim=64)
    assert isinstance(v1, list)
    assert len(v1) == 64
    assert v1 == v2
    # ensure vector is normalized (within numerical tolerance)
    import math
    norm = math.sqrt(sum(x * x for x in v1))
    assert abs(norm - 1.0) < 1e-6
