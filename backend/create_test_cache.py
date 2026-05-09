"""
Populates backend/cache/ and backend/test_data/ with a minimal fake transcript
for Karpathy's "Let's build GPT" video (kCc8FmEb1nY).
Run once to unblock development when YouTube IP-blocks transcript fetching.
"""

import json
from pathlib import Path

VIDEO_ID = "kCc8FmEb1nY"

SEGMENTS = [
    {
        "segment_index": 0,
        "start_time": 0.0,
        "end_time": 120.0,
        "text": (
            "Hi everyone, so by now you've probably heard of ChatGPT. It's taken the world by storm "
            "and it's a language model — you feed it text and it produces more text. What I want to do "
            "in this video is build one from scratch. We're going to implement a transformer neural network, "
            "the architecture behind GPT, and train it on Shakespeare text. By the end you'll understand "
            "how these models actually work under the hood."
        ),
    },
    {
        "segment_index": 1,
        "start_time": 120.0,
        "end_time": 240.0,
        "text": (
            "Before we touch any neural networks, we need to talk about tokenization. Tokenization is the "
            "process of converting raw text into sequences of integers that a model can process. The simplest "
            "approach is character-level tokenization where each character maps to a unique integer. "
            "More advanced systems like Byte Pair Encoding, used in real GPT models, merge common character "
            "sequences into single tokens. For our purposes we'll keep it simple and tokenize at the character level."
        ),
    },
    {
        "segment_index": 2,
        "start_time": 240.0,
        "end_time": 360.0,
        "text": (
            "Now let's talk about the training objective. Given a sequence of tokens, the model must predict "
            "the next token at every position. This is called the language modeling objective. We feed in "
            "a context window — say 256 tokens — and at every position the model outputs a probability "
            "distribution over the vocabulary. We then compute cross-entropy loss and backpropagate. "
            "This self-supervised approach means we can train on any raw text with no labels required."
        ),
    },
    {
        "segment_index": 3,
        "start_time": 360.0,
        "end_time": 480.0,
        "text": (
            "The core idea of the transformer is the self-attention mechanism. For every token in the sequence, "
            "self-attention lets it look at all other tokens and decide which ones are relevant. Each token "
            "produces three vectors: a query, a key, and a value. The query of one token is dot-producted "
            "against the keys of all tokens to get attention weights. These weights, after a softmax, are "
            "used to take a weighted sum of the value vectors. This gives each token a rich contextual representation."
        ),
    },
    {
        "segment_index": 4,
        "start_time": 480.0,
        "end_time": 600.0,
        "text": (
            "Multi-head attention runs several attention heads in parallel. Each head learns to attend to "
            "different aspects of the sequence. One head might learn syntactic relationships, another "
            "semantic ones. The outputs of all heads are concatenated and projected back down. "
            "In our GPT we'll use causal or masked self-attention — each token can only attend to tokens "
            "that came before it, not future ones, since during generation we only have past context."
        ),
    },
    {
        "segment_index": 5,
        "start_time": 600.0,
        "end_time": 720.0,
        "text": (
            "A transformer block combines self-attention with a feed-forward network. After the attention "
            "sub-layer, we pass the output through two linear layers with a ReLU nonlinearity in between. "
            "Both sub-layers use residual connections — we add the input back to the output — and layer "
            "normalization. Residual connections are crucial: they allow gradients to flow cleanly through "
            "the network during backpropagation and make training deep models much more stable."
        ),
    },
    {
        "segment_index": 6,
        "start_time": 720.0,
        "end_time": 840.0,
        "text": (
            "Positional encoding gives the model information about token order. Self-attention itself is "
            "permutation invariant — it doesn't know which token came first. We solve this by adding a "
            "positional embedding to each token embedding. We learn a separate embedding vector for each "
            "position in the context window. This way the model can distinguish token at position 5 from "
            "the same token at position 50."
        ),
    },
    {
        "segment_index": 7,
        "start_time": 840.0,
        "end_time": 960.0,
        "text": (
            "Let's talk about scaling. GPT-2 small has 117 million parameters, GPT-3 has 175 billion. "
            "The main levers are the number of layers, the embedding dimension, and the number of attention heads. "
            "Deeper models with wider embeddings are more capable but slower to train. "
            "We also need to think about the batch size and learning rate schedule. "
            "A warmup period followed by cosine decay is standard practice for transformer training."
        ),
    },
    {
        "segment_index": 8,
        "start_time": 960.0,
        "end_time": 1080.0,
        "text": (
            "Regularization is important to prevent overfitting. Dropout randomly zeroes out activations "
            "during training with some probability, forcing the network to learn redundant representations. "
            "We apply dropout after attention weights and after the feed-forward layers. "
            "Weight decay is another regularizer applied via the optimizer. Together these keep the model "
            "from memorizing the training data."
        ),
    },
    {
        "segment_index": 9,
        "start_time": 1080.0,
        "end_time": 1200.0,
        "text": (
            "To generate text we autoregressively sample from the model. We start with a prompt, "
            "run a forward pass to get the next-token distribution, sample from it using temperature "
            "to control randomness, append the sampled token, and repeat. Temperature above 1 makes "
            "the distribution more uniform and output more creative. Temperature below 1 sharpens the "
            "distribution toward the most likely token. This is how ChatGPT generates its responses."
        ),
    },
]

full_text = " ".join(s["text"] for s in SEGMENTS)
duration = SEGMENTS[-1]["end_time"]

result = {
    "video_id": VIDEO_ID,
    "segments": SEGMENTS,
    "full_text": full_text,
    "duration_seconds": duration,
}

cache_dir = Path(__file__).parent / "cache"
test_data_dir = Path(__file__).parent / "test_data"

cache_dir.mkdir(parents=True, exist_ok=True)
test_data_dir.mkdir(parents=True, exist_ok=True)

cache_path = cache_dir / f"{VIDEO_ID}.json"
test_data_path = test_data_dir / "karpathy_transcript.json"

cache_path.write_text(json.dumps(result, indent=2))
test_data_path.write_text(json.dumps(result, indent=2))

print(f"Written: {cache_path}")
print(f"Written: {test_data_path}")
print(f"Segments: {len(SEGMENTS)}")
print(f"Duration: {duration}s")
print(f"Full text chars: {len(full_text)}")
