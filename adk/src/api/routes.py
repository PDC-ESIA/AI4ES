from fastapi import APIRouter, HTTPException
from src.schemas.request_response import TextRequest, VowelCountResponse
from src.services.vowel_counter import VowelCounterService

router = APIRouter()

@router.post("/count-vowels", response_model=VowelCountResponse)
def count_vowels(request: TextRequest):
    count = VowelCounterService.count_vowels(request.text)
    return VowelCountResponse(vowel_count=count)
