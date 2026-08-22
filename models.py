from dataclasses import dataclass
from typing import Optional

@dataclass
class ProcessedTicket:
    """Structure that defines the data contract returned by the AI."""
    category: str        
    involved_value: Optional[float] 
    sentiment: str