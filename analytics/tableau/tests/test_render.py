import struct


def test_render_png_size(exported, tmp_path):
    import render_standin
    out = render_standin.render(exported, exported / "synthetic", tmp_path / "d.png")
    with open(out, "rb") as f:
        head = f.read(24)
    assert head[:8] == b"\x89PNG\r\n\x1a\n"
    w, h = struct.unpack(">II", head[16:24])
    assert w >= 2400 and h >= 1600
    assert out.with_suffix(".pdf").exists()


def test_synthetic_marking_in_code():
    """Every script that touches synthetic data carries a SYNTHETIC: marker."""
    from conftest import TABLEAU
    for name in ("export_extracts.py", "render_standin.py", "queries.py"):
        assert "# SYNTHETIC:" in (TABLEAU / name).read_text(), name
