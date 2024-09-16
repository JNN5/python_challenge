from dataclasses import dataclass, field
from typing import Optional

import util_constants
@dataclass
class BookingInput:
    company: Optional[str]
    start_of_week: Optional[str] = field(metadata={"regex": util_constants.DATE_REGEX})
    location: Optional[str]
    capsule_id: Optional[str]
