from pydantic import BaseModel, Field
from typing import List, Optional

class TestCase(BaseModel):
    id: str
    query: str
    category: str
    expected_refusal: bool
    keywords: List[str] = Field(default_factory=list)

class ContextSnippet(BaseModel):
    document_id: str
    score: float
    content: str

class TestResult(BaseModel):
    test_case: TestCase
    passed: bool
    refused_by_guardrail: bool
    error_message: Optional[str] = None
    details: Optional[str] = None
    context: List[ContextSnippet] = Field(default_factory=list)

class TestReport(BaseModel):
    total_cases: int = 0
    successful_cases: int = 0
    failed_cases: int = 0
    guardrail_coverage: float = 0.0
    retrieval_accuracy: float = 0.0
    failed_details: List[TestResult] = Field(default_factory=list)
