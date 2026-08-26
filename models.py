from pydantic import BaseModel, Field
from typing import Optional, Literal

class ProcessedTicket(BaseModel):
    """Pydantic model for strict runtime validation of AI outputs."""
    
    # The Literal type forces the AI to output the exact spelling, otherwise the code rejects it!
    category: Literal["Pix", "Cartão", "Empréstimo", "Atendimento", "Outros", "Desconhecida"] = "Desconhecida"
    
    involved_value: Optional[float] = Field(default=None)
    
    sentiment: Literal["Positivo", "Negativo", "Neutro"] = "Neutro"