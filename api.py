from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agents import research_code_error
import uvicorn

app = FastAPI(
    title="Code Error Research Assistant",
    description="Multi-Agent LangGraph system for researching code errors",
    version="1.0.0"
)

# Enable CORS for frontend
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ErrorRequest(BaseModel):
    code_snippet: str
    error_message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "code_snippet": "def divide(a, b):\n    return a / b\n\nresult = divide(10, 0)",
                "error_message": "ZeroDivisionError: division by zero"
            }
        }


class ErrorResponse(BaseModel):
    solution: str
    quality_score: int
    iterations: int
    search_queries: list
    source_urls: list


@app.get("/")
def root():
    """Serve the frontend"""
    frontend_path = Path(__file__).parent / "frontend.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    return {
        "status": "active",
        "service": "Code Error Research Assistant",
        "message": "Visit /docs for API documentation"
    }


@app.post("/research", response_model=ErrorResponse)
async def research_error(request: ErrorRequest):
    """
    Research a code error using multi-agent workflow
    
    - **code_snippet**: The problematic code
    - **error_message**: The error message you're seeing
    
    Returns a solution with quality score and iteration count
    """
    try:
        result = research_code_error(
            code_snippet=request.code_snippet,
            error_message=request.error_message
        )
        
        return ErrorResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Research failed: {str(e)}")


@app.get("/health")
def health_check():
    """System health check"""
    return {"status": "healthy", "agents": "operational"}


if __name__ == "__main__":
    import os
    
    # Get port from environment (GCP Cloud Run sets PORT env variable)
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print("\n🚀 Starting Code Error Research Assistant API...")
    print(f"📝 API Docs: http://localhost:{port}/docs")
    print("🔍 Interactive testing available at /docs\n")
    
    uvicorn.run(app, host=host, port=port)