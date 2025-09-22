from pydantic import BaseModel
class Log(BaseModel):
    id: int
    mensaje: str
    class Config:
        orm_mode = True
