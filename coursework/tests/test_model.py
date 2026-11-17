"""TinyGPT tests: shapes, causal mask, learning, overfitting, sampling stops."""
import torch

from coursework.tiny_transformer.data import Tokenizer, make_examples
from coursework.tiny_transformer.model import TinyGPT
from coursework.tiny_transformer.sample import generate_one

NAMES = ["ATTABOY", "BAR 54", "THE DEAD RABBIT", "MR. FONG'S", "LOREY'S", "PDT", "DOUBLE CHICKEN", "KGB"]


def tiny(tok, dropout=0.0):
    torch.manual_seed(0)
    return TinyGPT(tok.vocab_size, block_size=16, n_embd=32, n_head=2, n_layer=2, dropout=dropout)


def test_shapes():
    tok = Tokenizer(NAMES)
    x, y = make_examples(NAMES, tok, 16)
    logits, loss = tiny(tok)(x, y)
    assert logits.shape == (8, 16, tok.vocab_size) and loss.ndim == 0


def test_causal_mask_future_does_not_leak():
    """[N7] Changing tokens after position t must not change the logits at positions <= t."""
    tok = Tokenizer(NAMES)
    model = tiny(tok).eval()
    x = torch.randint(0, tok.vocab_size, (1, 16))
    x2 = x.clone()
    x2[0, 9:] = (x2[0, 9:] + 1) % tok.vocab_size
    with torch.no_grad():
        a, _ = model(x)
        b, _ = model(x2)
    assert torch.allclose(a[0, :9], b[0, :9], atol=1e-6)
    assert not torch.allclose(a[0, 9:], b[0, 9:])


def test_one_step_lowers_loss():
    tok = Tokenizer(NAMES)
    model = tiny(tok)
    x, y = make_examples(NAMES, tok, 16)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-3)
    _, before = model(x, y)
    opt.zero_grad()
    before.backward()
    opt.step()
    _, after = model(x, y)
    assert after.item() < before.item()


def test_overfit_eight_names():
    tok = Tokenizer(NAMES)
    model = tiny(tok)
    x, y = make_examples(NAMES, tok, 16)
    # The FIRST character is a genuine 1-in-8 guess (which name?), costing ln 8 = 2.08 nats however
    # well the model memorises, so it is excluded; every later character can be memorised.
    y[:, 0] = -100
    opt = torch.optim.AdamW(model.parameters(), lr=3e-3)
    for _ in range(300):
        _, loss = model(x, y)
        opt.zero_grad()
        loss.backward()
        opt.step()
    assert loss.item() < 0.1


def test_sampling_stops_at_end_or_max_length():
    tok = Tokenizer(NAMES)
    model = tiny(tok).eval()
    gen = torch.Generator().manual_seed(0)
    for _ in range(20):
        ids = generate_one(model, tok.start_id, tok.end_id, 1.0, None, gen)
        assert len(ids) <= model.block_size - 1 and tok.end_id not in ids and tok.start_id not in ids
