# Tiny transformer: explanation notes

What this is: a character-level language model, a very small GPT. It learns what Manhattan
bar and restaurant names look like and then writes new ones. Everything is written from scratch in
PyTorch and trains on a laptop CPU in under a minute.

How to run (from the repo root):

```bash
python -I coursework/tiny_transformer/baselines.py          # the bars to beat
python -I coursework/tiny_transformer/train.py --ablation   # train (about 40 s) + 3 ablation runs
python -I coursework/tiny_transformer/sample.py --n 20 --temperature 0.8 --summary
python -m pytest coursework/tests -q                        # all tests
```

Each section below matches a `[N#]` tag in the code. Sections are in the order the code runs.
Numbers come from the committed `outputs/metrics.json` (seed 0).

---

## [N1] The task and the corpus

**What it does.** We train a model to predict the next character of a venue name, given the
characters so far. If the model predicts well, it has learned the "shape" of names: common words
(THE, BAR, CAFE, RESTAURANT), which letters follow which, and how long names usually are. The data
is real public data: the distinct `name` column of the `venues` table in `data/manhattan_bars.db`
(NY State Liquor Authority licences), 5,428 distinct raw names. We only read it (`mode=ro`).

**Code.** `data.py:load_names`

**Example.** One row gives the string `PIACERE ENTERPRISES LLC`.

**Common mistake.** Opening the database read-write and changing it by accident. `common.py:connect_read_only`
makes that impossible.

**Check yourself.** Why is "predict the next character" enough to make a model that can write new names?

## [N2] Cleaning and the train/validation split

**What it does.** Licence names are messy, so `clean_name` upper-cases them, keeps only the part
before a `;`, removes legal noise (`LLC`, `INC`, `CORP`, `CO.`, `LTD`, `#123`, everything after
`D/B/A`), keeps only `A-Z 0-9 space & ' - .`, collapses spaces, and drops names shorter than 3 or
longer than 30 characters. After de-duplication this leaves 4,986 names, mean length 13.7. Then
`split_names` shuffles them with a fixed seed and keeps 10% (499 names) as **validation** data the
model never trains on. Training uses the other 4,487.

We split by **whole name**. If we split the long string of all characters instead, the first half of a
name could be in training and the second half in validation. The model would then partly be tested
on things it had already seen.

**Code.** `data.py:clean_name`, `data.py:clean_all`, `data.py:split_names`

**Example.** `LUMA HOTEL - TIMES SQUARE; APERIBAR` becomes `LUMA HOTEL - TIMES SQUARE`.
`Joe's Pub #2` becomes `JOE'S PUB`.

**Common mistake.** Choosing settings by looking at the validation loss many times. That slowly
leaks validation information into the choices. Here we only use it for early stopping and a
3-run ablation, and we say so.

**Check yourself.** What would go wrong if the same name appeared in both train and validation?

## [N3] Baselines and "nats per character"

**What it does.** Before training anything we compute two simple models on the same split, so we
know what "good" means:

- **Unigram:** P(next char) = how often that character appears in training. It ignores context.
- **Bigram:** P(next char | previous char) from a 43 × 43 count table. Add-1 smoothing: every cell
  starts at 1, so no probability is ever 0.

The loss is **cross-entropy in nats per character**: the average of −ln P(true next char). "Nats"
means natural log (bits would use log base 2). Lower is better. Guessing uniformly over all 43
tokens gives ln 43 = 3.761. **Perplexity** = e^loss: roughly "how many characters the model is
choosing between" at each step.

| model | val loss (nats/char) | perplexity |
|---|---|---|
| uniform guess | 3.761 | 43.0 |
| unigram | 3.083 | 21.8 |
| bigram | 2.643 | 14.0 |
| **TinyGPT** | **2.113** | **8.27** |

All three are scored on the same targets: every character of each validation name plus the final `<e>`.

**Code.** `baselines.py:unigram_loss`, `baselines.py:bigram_loss`

**Example.** If the model gives the true next letter probability 0.5, that step costs −ln 0.5 = 0.69 nats.
If it gives 0.05, the step costs 3.0 nats.

**Common mistake.** Reporting the transformer's loss with no baseline. "2.1" means nothing until you
know that a bigram gets 2.64.

**Check yourself.** Why does the bigram baseline matter more than the uniform one? What does a
loss of ln 43 mean?

## [N4] Tokens and embeddings

**What it does.** The model works with integers, not letters. `Tokenizer` gives every character an
id, plus two special tokens: `<s>` (id 0, "a name starts here") and `<e>` (id 1, "the name ends
here", also used as padding). The vocabulary has 43 tokens. Each training example is
`<s> NAME <e> <e> …`, padded to 33 tokens. The input `x` is tokens 0..31 and the target `y` is
tokens 1..32, so **at every position the target is the next token**. Targets after the first `<e>`
are set to −100, which the loss ignores. The model should learn to end a name, but predicting
padding would only be wasted effort.

An **embedding** is a learned lookup table: token id → a vector of 64 numbers (`n_embd = 64`). At the
start the vectors are random. Training moves them so that characters that behave alike end up with
similar vectors.

**Code.** `data.py:Tokenizer`, `data.py:make_examples`, `model.py:TinyGPT.__init__` (`token_emb`)

**Example.** `BAR 54` → x = `<s> B A R ␣ 5 4 <e> <e> …`, y = `B A R ␣ 5 4 <e> -100 -100 …`.

**Common mistake.** Forgetting to shift x and y by one. The model would then learn to copy its
input, and the loss would drop to about 0 while it learned nothing useful.

**Check yourself.** Why do we keep exactly one `<e>` target and ignore the rest?

## [N5] Position embeddings

**What it does.** Attention (N6) by itself does not know the order of tokens: it treats its input as
a set. So we add a second learned table, one vector per position 0..31 (`pos_emb`), to each token
vector: `x = token_emb + pos_emb`. The model then knows both *what* the token is and *where* it is.
That matters here: names often start with `THE` and end with `BAR`, `CAFE` or `RESTAURANT`.

**Code.** `model.py:TinyGPT.forward` (`pos = self.pos_emb(torch.arange(T))`, `x = tok + pos`)

**Example.** The `A` in `ATTABOY` (position 1) and the `A` in `BAR` (position 2) start from the
same token vector but get different position vectors added.

**Common mistake.** Sampling longer than `block_size`. There is no position vector for position 32,
so `sample.py` stops at `block_size`.

**Check yourself.** What could the model not learn if we removed the position embedding?

## [N6] Self-attention, worked by hand

**What it does.** Self-attention lets each position collect information from earlier positions.
Every token vector x is turned into three vectors by three learned matrices:
**query** q = x·W_Q ("what am I looking for?"), **key** k = x·W_K ("what do I contain?"), and
**value** v = x·W_V ("what do I pass on?"). The score between position i and position j is
q_i · k_j / √d. A softmax turns each row of scores into weights that sum to 1. The output at i is
the weighted average of the values.

**Code.** `model.py:Head.forward`, the numpy version `attention_by_hand.py:attention_by_hand`, and the
test `tests/test_attention_by_hand.py`. The test loads these exact weights into `Head` and checks that
the outputs match to 1e-6.

**Worked example (3 tokens, d = 2).**
Tokens: x0 = (1,0), x1 = (0,1), x2 = (1,1). W_Q = identity, W_K = diag(1, 2), W_V swaps the coordinates.

- q = x → q0 = (1,0), q1 = (0,1), q2 = (1,1)
- k → k0 = (1,0), k1 = (0,2), k2 = (1,2)
- v → v0 = (0,1), v1 = (1,0), v2 = (1,1)
- Scores for token 2: q2·k0 = 1, q2·k1 = 2, q2·k2 = 3. Divided by √2 → 0.707, 1.414, 2.121.
- Softmax: e^0.707 = 2.03, e^1.414 = 4.11, e^2.121 = 8.34, total 14.48 → weights **0.140, 0.284, 0.576**.
- Output for token 2 = 0.140·(0,1) + 0.284·(1,0) + 0.576·(1,1) = **(0.860, 0.716)**.
- Token 1 can only see tokens 0 and 1: scores (0, 1.414) → weights (0.196, 0.804) → output (0.804, 0.196).
- Token 0 can only see itself: weight 1 → output = v0 = (0, 1).

Why divide by √d: without it, the dot products grow with the vector size. Softmax then puts almost
all of the weight on one position, and the gradients become tiny.

**Common mistake.** Forgetting that `nn.Linear` computes x·Wᵀ. The test has to load the transposed
matrices.

**Check yourself.** Redo token 1's weights by hand. Why do the weights in each row add up to 1?

## [N7] The causal mask

**What it does.** When the model predicts character t+1, it must not see characters t+1, t+2, …
Otherwise it would just read off the answer. The mask is a lower-triangular matrix of ones
(`torch.tril`). Scores where the mask is 0 (the future) are set to −∞ before the softmax, and
e^−∞ = 0, so future positions get exactly zero weight. In the example above, that is why token 0's
row is (1, 0, 0).

**Code.** `model.py:Head.__init__` (`register_buffer("mask", …)`), `Head.forward` (`masked_fill`),
and `attention_by_hand.py`. The test `tests/test_model.py:test_causal_mask_future_does_not_leak`
changes every token after position 8 and checks that the outputs at positions 0–8 do not change.

**Common mistake.** Removing the mask. Training loss then drops close to 0, because the model reads
the next character from its input. At sampling time there is no future to read, so the output is garbage.

**Check yourself.** What would break if the causal mask were removed? Why −∞ and not 0?

## [N8] Multi-head attention and the MLP

**What it does.** One head learns one kind of "look back" pattern. We run 4 heads in parallel
(`n_head = 4`), each with 16 dimensions (64 / 4), so one head can, for example, track "am I inside
the word THE" while another tracks "how long is this name so far". Their outputs are concatenated
back to 64 numbers and mixed by a linear layer (`proj`).

After attention, each position goes through a small **MLP** (feed-forward network) on its own:
64 → 256 → 64 with a GELU non-linearity in between. Attention moves information *between*
positions. The MLP processes it *at* each position.

**Code.** `model.py:MultiHeadAttention`, `model.py:FeedForward`

**Example.** Parameter count of the default model: 107,307 (see `metrics.json`). About 62% of it
(66,176) is in the two MLPs.

**Common mistake.** Thinking more heads add capacity for free. With `n_embd` fixed, more heads means
smaller heads.

**Check yourself.** What is the difference between what attention does and what the MLP does?

## [N9] Residual connections and layer norm

**What it does.** Each block computes `x = x + attention(LayerNorm(x))` and then
`x = x + MLP(LayerNorm(x))`. The `x +` part is a **residual connection**. Each sub-layer only adds
a correction to x and does not replace it, so information and gradients can flow straight through
the stack. **LayerNorm** rescales each token vector to mean 0 and variance 1 (and then applies a
learned scale and shift), which keeps the numbers in a stable range. We use "pre-norm": the norm
comes before each sub-layer, as in GPT-2. We stack 2 blocks (`n_layer = 2`), then apply a final
LayerNorm and a linear layer that outputs one score (logit) per token in the vocabulary.

**Code.** `model.py:Block.forward`, `model.py:TinyGPT.forward` (`ln_f`, `lm_head`)

**Example.** At initialisation the sub-layers output small values, so each block starts out close
to "do nothing", and the model learns the corrections it needs.

**Common mistake.** Writing `x = attn(ln(x))` without the residual. Deeper models then train much
worse.

**Check yourself.** Why does adding x back make deep networks easier to train?

## [N10] Loss, optimizer, learning-rate schedule, early stopping

**What it does.**
- **Loss:** cross-entropy (`F.cross_entropy`) between the logits and the true next token, averaged over all
  targets that are not −100. This is the same quantity as the baselines in N3.
- **Optimizer:** AdamW, a version of gradient descent that keeps a running average of each weight's
  gradient and of its size, plus a small weight decay (0.01) that pulls weights toward 0.
- **Learning rate:** cosine schedule from 3e-3 down to 3e-4 over 3,000 steps (`lr_at`). Big steps
  early, small careful steps late.
- **Batches:** 64 random training names per step, drawn with a seeded generator so runs repeat.
- **Evaluation:** every 100 steps, loss on a fixed set of 1,000 training names and on **all** 499
  validation names, with dropout off (`model.eval()`).
- **Early stopping:** if validation loss has not improved for 5 evaluations, stop, and keep the
  weights from the best evaluation.

Result: the best validation loss was 2.113 at step 1,200. Training stopped at step 1,700. At that
point training loss was 1.64 and still falling while validation loss had flattened. That gap is
**overfitting** (the model starts memorising training names), and early stopping is what protects us
from it. Dropout 0.1 also helps (see N12).

**Code.** `train.py:train_model`, `train.py:lr_at`, `train.py:evaluate`, `model.py:TinyGPT.forward`

**Example.** `outputs/loss_curve.png` shows train and val loss against the dashed bigram line.

**Common mistake.** Reporting the *last* checkpoint or the *training* loss. We report the best
validation loss and say how it was chosen.

**Check yourself.** Why is the train loss lower than the val loss? What would happen without early stopping?

## [N11] Sampling and temperature

**What it does.** To write a new name we start from `[<s>]`, run the model, take the logits at the
**last** position, divide them by the **temperature** T, apply softmax and draw one token. The token
is appended and we repeat until `<e>` is drawn or the name reaches 31 characters. `<s>` is never
allowed in the middle of a name. With top-k (optional), only the k most likely tokens are kept before
the draw.

Temperature changes how peaked the distribution is. Dividing logits by T < 1 makes big logits
relatively bigger, so the model picks safe, common characters (more repetition). T > 1 flattens the
distribution, which gives more variety but more nonsense. **Novelty rate** = share of samples that are
not an exact copy of a training name.

| T | novelty | distinct samples | examples |
|---|---|---|---|
| 0.3 | 99% | 86% | THE STORE TAVERN, THE THAI, SUSHI HOTEL THE RESTAURANT |
| 0.8 | 100% | 100% | SUSHAY MUSHI, JONOY AND CAFE, THE STRIDA |
| 1.2 | 99% | 100% | ART AAQUUARINA, AVEVE HOUSE, SUSHAY MUNGUTO |

(200 samples each, `outputs/sampling.json`.) The 20 saved samples at T = 0.8 are in
`outputs/synthetic/generated_names.csv`. They are **synthetic** (`is_synthetic = 1`): never show
them as real venues.

**Code.** `sample.py:generate_one`, `sample.py:novelty_rate`, `sample.py:temperature_summary`

**Example.** Logits (2, 1, 0) at T = 1 give probabilities (0.67, 0.24, 0.09). At T = 0.5 the
logits become (4, 2, 0) and the probabilities (0.87, 0.12, 0.02).

**Common mistake.** Treating high novelty as proof of quality. Random letters are 100% novel too. Novelty
has to be read together with the loss and with actually reading the samples.

**Check yourself.** Why is a temperature below 1 more conservative? Why use only the last position's logits?

## [N12] Results, ablation, limitations

**Results (seed 0, CPU, 4 threads):** 107,307 parameters, 39 s of training, best val loss
**2.113 nats/char** (perplexity 8.27). That is **20.0% lower than the bigram baseline** (2.643; the PRD
target was 10%), and the sample novelty rate at T = 0.8 is 100% (target 70%). A rerun with the
same seed reproduced 2.1131 exactly (AC1.4).

**Ablation** (one change at a time, val loss only, `metrics.json → ablation`):

| variant | params | best val loss |
|---|---|---|
| default (2 layers, block 32, dropout 0.1) | 107,307 | 2.113 |
| n_layer = 1 | 57,515 | 2.143 |
| block_size = 16 | 106,283 | 2.212 |
| dropout = 0 | 107,307 | 2.205 |

Reading it: the second layer helps a little. Without dropout the model overfits sooner, and the val
loss is worse. The block_size = 16 run truncates names longer than 15 characters, so its loss is
measured on slightly different targets. Read it as "shorter context hurts", not as an exact comparison.
These are single runs with one seed, so differences of about 0.01 may be noise.

**What I would say in a 2-minute presentation**
1. I trained a 107k-parameter GPT-style model from scratch on 4,986 real Manhattan liquor-licence names, CPU only, in under a minute.
2. The bar to beat was a bigram model at 2.64 nats/char. The transformer got 2.11, 20% lower, on names it never saw.
3. Attention is a weighted average of earlier characters (I can show the 3-token example by hand), and the causal mask stops it from seeing the answer.
4. Early stopping at the best validation loss stopped the model from memorising. Train loss kept falling while val loss levelled off.
5. The generated names (THE STORE TAVERN, JONOY AND CAFE) are new and look like real names. Temperature trades safety for variety.

**Limitations**
- Small corpus (about 5k names, about 70k characters), so the model only learns surface patterns. Many samples are near-misses ("CLUBLE").
- One seed and no confidence intervals on the loss. The ablation differences are small.
- Licence names include company and personal names, not only "nice" bar names.
- Character-level only. A word-level tokenizer would need far more data.
- Plausibility was not formally rated (the PRD's "90% plausible by manual read" is left for Ryan to do on the 20 saved samples).

---

## Answers to the self-check questions (cover these up first)

- **Why predict the next character?** If you can predict each next character well, you can generate by sampling one character at a time.
- **Same name in train and val?** The model would be tested on memorised data, and the val loss would look too good.
- **Why the bigram baseline?** It is the simplest model that uses context. Beating it shows that attention over longer context adds something. ln 43 = the loss of guessing uniformly.
- **One `<e>` target?** The model must learn where names end. The padding after that carries no information.
- **No position embedding?** Order-dependent patterns would be lost: "starts with THE", "ends with BAR", name length.
- **Rows sum to 1?** Softmax output. The result is a weighted *average* of the values.
- **No causal mask?** The model cheats in training by reading the next character, and it fails at generation. −∞ gives weight exactly 0. A score of 0 would still get weight e^0 = 1.
- **Attention vs MLP?** Attention mixes information across positions. The MLP transforms each position on its own.
- **Residual?** Gradients reach early layers directly, and each layer only learns a correction.
- **Train < val?** The model fits names it has seen. Without early stopping, val loss would start rising as it memorises.
- **T < 1 conservative?** It sharpens the distribution toward the most likely characters. Only the last position predicts the *next* character. The other positions predict characters we already have.
