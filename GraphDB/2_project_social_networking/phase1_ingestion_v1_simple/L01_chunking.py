from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter


def semantic_chunking(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50
) -> List[Dict[str, Any]]:
    """
    Performs production-ready semantic chunking.

    Strategy
    --------
    1. Split document into paragraphs.
    2. Split oversized paragraphs using RecursiveCharacterTextSplitter.
    3. Return structured chunks suitable for LLM extraction.

    Parameters
    ----------
    text : str
        Raw input document.

    chunk_size : int
        Maximum chunk size.

    chunk_overlap : int
        Overlap between adjacent chunks.

    Returns
    -------
    List[Dict]

    Example
    -------
    [
        {
            "chunk_id": 1,
            "text": "...",
            "metadata": {
                "paragraph": 1,
                "chunk_index": 1,
                "length": 423
            }
        }
    ]
    """

    # Remove empty lines
    paragraphs = [
        p.strip()
        for p in text.split("\n\n")
        if p.strip()
    ]

    splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ". ", " "],
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    chunks = []

    chunk_counter = 1

    for paragraph_number, paragraph in enumerate(paragraphs, start=1):

        paragraph_chunks = splitter.split_text(paragraph)

        for chunk_index, chunk in enumerate(paragraph_chunks, start=1):

            chunks.append(
                {
                    "chunk_id": chunk_counter,
                    "text": chunk,
                    "metadata": {
                        "paragraph": paragraph_number,
                        "chunk_index": chunk_index,
                        "length": len(chunk),
                    },
                }
            )

            chunk_counter += 1

    return chunks

if __name__ == "__main__":
    # Example 
    with open("data.txt", "r") as f:
        sample_text = f.read()
    
    result = semantic_chunking(sample_text, chunk_size=600, chunk_overlap=20)
    for i,chunk in enumerate(result):
        print(f"Chunk {i + 1}: {chunk}")
        print()
        
"""
# Chunk 1: {'chunk_id': 1, 'text': 'TechHub is a major software company managed by its CEO, Alice. The company developed a popular messaging application called ChatApp. Alice closely manages Bob, who works as the Lead Developer for ChatApp. Bob is married to Charlie, a Product Designer who also works at TechHub. Charlie shares an office with Diana, a Data Scientist at the company.', 'metadata': {'paragraph': 1, 'chunk_index': 1, 'length': 347}}

# Chunk 2: {'chunk_id': 2, 'text': 'Beyond work, this group forms a tight social circle. Alice, Bob, and Charlie are all members of a professional organization called TechAssociation. Diana recently joined this same organization. Socially, Bob and Diana are co-organizers of a local community group called DataClub. Charlie is also a member of DataClub, where she frequently interacts with Diana.', 'metadata': {'paragraph': 2, 'chunk_index': 1, 'length': 360}}

# Chunk 3: {'chunk_id': 3, 'text': 'The team heavily utilizes online platforms. Bob regularly follows Diana on GitHub to review her open-source code. Meanwhile, Diana follows Charlie on Behance to look at her design portfolios. Both Bob and Charlie are active users of LinkedIn for professional networking. Alice also uses LinkedIn, where she frequently views posts by Bob and Charlie. Additionally, TechHub maintains an official corporate profile on LinkedIn to post company updates.', 'metadata': {'paragraph': 3, 'chunk_index': 1, 'length': 448}}
"""