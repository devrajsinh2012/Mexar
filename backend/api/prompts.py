from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from modules.prompt_analyzer import create_prompt_analyzer, get_prompt_templates

router = APIRouter(prefix="/api", tags=["prompts"])

class AnalyzeRequest(BaseModel):
    prompt: str

@router.get("/prompt-templates")
async def get_templates():
    """Get available system prompt templates."""
    try:
        templates = get_prompt_templates()
        return {"templates": templates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze-prompt")
async def analyze_prompt_endpoint(request: AnalyzeRequest):
    """Analyze a system prompt to extract domain and metadata."""
    try:
        analyzer = create_prompt_analyzer()
        analysis = analyzer.analyze_prompt(request.prompt)
        return {"analysis": analysis}
    except Exception as e:
        # Fallback is handled inside analyze_prompt, but just in case
        raise HTTPException(status_code=500, detail=str(e))
