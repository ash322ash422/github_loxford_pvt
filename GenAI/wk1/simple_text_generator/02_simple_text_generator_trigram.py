"""
Advanced text generator for teaching purposes.
Usage: python 02_simple_text_generator_trigram.py [--seed WORD] [--words N] [--file PATH]

Example:  
  python 02_simple_text_generator_trigram.py --seed "Artificial" --words 3 
  python 02_simple_text_generator_trigram.py --seed "Alice" --words 6 --file "alice_in_wonderland.txt"


Generates realistic text using a trigram (order-2 Markov) model.
"""
import random
import argparse
import sys
import re

DEFAULT_CORPUS = (
    "Artificial intelligence is transforming how we work and learn. "
    "Text generation models can assist with writing, brainstorming, and education. "
    "This simple generator demonstrates a basic Markov chain approach."
)

def tokenize(text: str):
    """Splits text into words and punctuation so they are processed cleanly."""
    # This regular expression keeps words and punctuation marks as separate tokens
    return re.findall(r"[\w']+|[.,!?;]", text)

def build_trigrams(text: str):
    """Builds an order-2 Markov model (Trigram model)."""
    tokens = tokenize(text)
    model = {}
    
    # Loop through the text three tokens at a time
    for a, b, c in zip(tokens, tokens[1:], tokens[2:]):
        state = (a, b)
        model.setdefault(state, []).append(c)
    return model

def generate(model, seed=None, max_words=50):
    if not model:
        return ""
        
    # If no valid seed pair is provided, pick a random starting state
    if seed is None or seed not in model:
        # Filter for states starting with a capital letter for a clean sentence start
        capital_states = [k for k in model.keys() if k[0][0].isupper()]
        state = random.choice(capital_states) if capital_states else random.choice(list(model.keys()))
    else:
        state = seed

    output = [state[0], state[1]]
    
    for _ in range(max_words - 2):
        choices = model.get(state)
        if not choices:
            break
        next_word = random.choice(choices)
        output.append(next_word)
        state = (state[1], next_word) # Shift the state window forward
        
    # Detokenize: join words with spaces, but attach punctuation cleanly
    text = " ".join(output)
    text = re.sub(r'\s+([.,!?;])', r'\1', text)
    return text

def main(argv=None):
    parser = argparse.ArgumentParser(description="Realistic text generator (Markov trigrams)")
    parser.add_argument("--seed", help="Starting word for generation", default=None)
    parser.add_argument("--words", help="Number of words to generate", type=int, default=50)
    parser.add_argument("--file", help="Path to text file to build the model from", default=None)
    args = parser.parse_args(argv)

    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                corpus = f.read()
        except Exception as e:
            print(f"Could not read file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        corpus = DEFAULT_CORPUS

    model = build_trigrams(corpus)
    
    # Process the seed if provided (expecting a single word, we find a matching pair)
    seed_state = None
    if args.seed:
        matching_states = [k for k in model.keys() if k[0] == args.seed]
        if matching_states:
            seed_state = random.choice(matching_states)

    text = generate(model, seed=seed_state, max_words=args.words)
    print(text)

if __name__ == "__main__":
    main()
