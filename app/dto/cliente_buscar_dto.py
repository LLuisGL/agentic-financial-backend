from pydantic import BaseModel

class ClienteBuscarRequest(BaseModel):
    ruc_cedula: str | None = None
    razon_social: str | None = None
    numero_titulo: str | None = None
