from pydantic import BaseModel, Field
from typing import Optional, Literal

class ProcessedTicket(BaseModel):
    """Pydantic model for strict runtime validation of AI outputs."""
    
    # O Literal obriga a IA a acertar a grafia exata, senão o código rejeita!
    category: Literal["Pix", "Cartão", "Empréstimo", "Atendimento", "Outros", "Desconhecida"] = "Desconhecida"
    
    involved_value: Optional[float] = Field(default=None)
    
    sentiment: Literal["Positivo", "Negativo", "Neutro"] = "Neutro"