from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health():
    """
    Health check endpoint
    """
    return {"status": "ok"}