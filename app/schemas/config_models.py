from pydantic import BaseModel


class ProviderConfig(BaseModel):
    chat: str
    embedding: str


class ConfigModelsResponse(BaseModel):
    security_mode: str  # "secure" | "not_secure"
    active_chat_model: str
    active_embedding_model: str
    openai: ProviderConfig
    ollama: ProviderConfig
