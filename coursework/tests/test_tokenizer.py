"""Tokenizer and data-prep tests for the tiny transformer."""
from coursework.tiny_transformer.data import Tokenizer, clean_name, make_examples, split_names

NAMES = ["THE DEAD RABBIT", "ATTABOY", "MR. FONG'S", "BAR 54"]


def test_round_trip():
    tok = Tokenizer(NAMES)
    for name in NAMES:
        assert tok.decode(tok.encode(name)) == name


def test_special_tokens_first():
    tok = Tokenizer(NAMES)
    assert tok.itos[:2] == ["<s>", "<e>"] and tok.start_id == 0 and tok.end_id == 1


def test_clean_name():
    assert clean_name("PIACERE ENTERPRISES LLC") == "PIACERE ENTERPRISES"
    assert clean_name("LUMA HOTEL - TIMES SQUARE; APERIBAR") == "LUMA HOTEL - TIMES SQUARE"
    assert clean_name("Joe's Pub #2") == "JOE'S PUB"


def test_split_is_by_name_and_seeded():
    names = [f"N{i}" for i in range(100)]
    tr, va = split_names(names, 0.1, seed=0)
    assert len(va) == 10 and not set(tr) & set(va)
    assert split_names(names, 0.1, seed=0) == (tr, va)


def test_examples_shift_and_ignore_padding():
    tok = Tokenizer(NAMES)
    x, y = make_examples(["BAR 54"], tok, block_size=10)
    assert x.shape == (1, 10)
    assert x[0, 0] == tok.start_id and y[0, 0] == tok.encode("B")[0]   # target = next char
    assert y[0, 6] == tok.end_id and (y[0, 7:] == -100).all()         # one <e>, then ignored
