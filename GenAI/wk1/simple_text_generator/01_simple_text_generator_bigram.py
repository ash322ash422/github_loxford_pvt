"""Basic text generator for teaching purposes.

Usage:
  python 01_simple_text_generator_bigram.py [--seed WORD] [--words N] [--file PATH]
  
  Example:  
  python 01_simple_text_generator_bigram.py --seed "Artificial" --words 3 
  python 01_simple_text_generator_bigram.py --seed "Alice" --words 6 --file "alice_in_wonderland.txt"
  
  
Generates simple text using a bigram (order-1 Markov) model built from
either a provided text file or a small default corpus.
"""
import random
import argparse
import sys


DEFAULT_CORPUS = (
	"Artificial intelligence is transforming how we work and learn. "
	"Text generation models can assist with writing, brainstorming, and education. "
	"This simple generator demonstrates a basic Markov chain approach."
)


def build_bigrams(text: str):
	words = text.split()
	model = {}
	for a, b in zip(words, words[1:]):
		model.setdefault(a, []).append(b)
	return model


def generate(model, seed=None, max_words=50):
	if not model:
		return ""
	if seed is None or seed not in model:
		seed = random.choice(list(model.keys()))
	output = [seed]
	for _ in range(max_words - 1):
		choices = model.get(output[-1])
		if not choices:
			break
		next_word = random.choice(choices)
		output.append(next_word)
	return " ".join(output)


def main(argv=None):
	parser = argparse.ArgumentParser(description="Basic text generator (Markov bigrams)")
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

	model = build_bigrams(corpus)
	text = generate(model, seed=args.seed, max_words=args.words)
	print(text)


if __name__ == "__main__":
	main()

