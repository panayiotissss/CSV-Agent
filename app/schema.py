from pydantic import BaseModel
from typing import Literal

class Finding(BaseModel):
    answer: str
    key_numbers: dict[str, float]
    tools_used: list[str]
    confidence: Literal["high", "medium", "low"]