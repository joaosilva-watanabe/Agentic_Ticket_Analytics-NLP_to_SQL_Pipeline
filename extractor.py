import os
import json
import logging
from dotenv import load_dotenv
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# Initialize API credentials
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

def extract_information_via_api(text: str, model: str = "gemini-3.6-flash") -> dict:
    """Sends the text to the API and ensures the return is in strict JSON."""
    system_prompt = """
    Você é um extrator de dados transacionais bancários. 
    Sua única função é receber o texto do cliente e retornar EXCLUSIVAMENTE um objeto JSON válido.
    NÃO inclua saudações, NÃO inclua explicações, NÃO envolva a resposta em blocos de código markdown.
    
    Esquema JSON obrigatório:
    {
      "category": "string (Pix, Cartão, Empréstimo, Atendimento, Outros)",
      "involved_value": "float (use null se nenhum valor for mencionado)",
      "sentiment": "string (Positivo, Negativo, Neutro)"
    }
    
    Exemplo 1:
    Entrada: "Fiz um pix de R$ 150,50 ontem mas não caiu na conta, estou revoltado!"
    Saída: {"category": "Pix", "involved_value": 150.50, "sentiment": "Negativo"}
    """
    
    try:
        response = client.models.generate_content(
            model=model,
            contents=f"{system_prompt}\n\nEntrada: {text}\nSaída: ",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,
            ),
        )
        
        content_str = response.text
        clean_content = content_str.strip()
        if clean_content.startswith("```json"):
            clean_content = clean_content[7:]
        if clean_content.endswith("```"):
            clean_content = clean_content[:-3]
            
        return json.loads(clean_content.strip())
        
    except Exception as e:
        logger.error(f"Failed to communicate with LLM: {e}")
        raise