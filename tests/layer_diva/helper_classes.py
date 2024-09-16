from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List


@dataclass
class Subsample1:
    hello: Optional[str]
    nested_madness: Dict[str, List[Dict[str, str]]]
            

class Statuz(Enum):
    FIRST = "first"
    SECOND = "second"
    THIRD = "third"

    
@dataclass
class Sample1:
    id: str
    active: bool
    count: int
    ids: List[str]
    subclazz: Subsample1
    wow: dict
    timestamp: datetime = field(metadata={"date_format": "%Y-%m-%d %H:%M:%S"})
    statuz: Statuz
    reg: str = field(metadata={"regex": r'^(\d{4}-\d{2}-\d{2})$'})