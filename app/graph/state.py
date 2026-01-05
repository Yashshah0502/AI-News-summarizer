# app/graph/state.py
from typing import TypedDict, List, Dict

class NewsState(TypedDict, total=False):
    window_hours: int
    raw_count: int
    article_ids: List[int]
    extracted_attempted: int
    extraction_stats: Dict[str, int]
    selected_ids: List[int]
