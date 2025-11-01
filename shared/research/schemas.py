"""Research data schemas using Pydantic."""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator


class ProblemStatement(BaseModel):
    """Schema for research problem statement."""

    query: str = Field(..., description="Original research query")
    research_question: str = Field(..., description="Formal research question")
    hypothesis: str = Field(..., description="Primary hypothesis to test")
    scope: Dict[str, Any] = Field(..., description="Research scope and boundaries")
    keywords: List[str] = Field(..., description="Key research keywords")
    domain: str = Field(..., description="Research domain/field")
    feasibility_score: Optional[float] = Field(None, ge=0, le=1, description="Feasibility score (0-1)")
    novelty_score: Optional[float] = Field(None, ge=0, le=1, description="Novelty score (0-1)")

    @validator('keywords')
    def validate_keywords(cls, v):
        if len(v) < 3:
            raise ValueError("At least 3 keywords required")
        return v


class Paper(BaseModel):
    """Schema for academic paper metadata."""

    title: str
    authors: List[str]
    abstract: str
    published_date: Optional[str] = None
    journal: Optional[str] = None
    arxiv_id: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    relevance_score: Optional[float] = Field(None, ge=0, le=1)
    citations_count: Optional[int] = Field(None, ge=0)

    @validator('authors')
    def validate_authors(cls, v):
        if not v:
            raise ValueError("At least one author required")
        return v


class LiteratureCorpus(BaseModel):
    """Schema for literature search results."""

    query: str = Field(..., description="Search query used")
    total_found: int = Field(..., description="Total papers found")
    papers: List[Paper] = Field(..., description="List of papers")
    sources: List[str] = Field(..., description="Sources searched (ArXiv, Semantic Scholar, etc.)")
    search_date: datetime = Field(default_factory=datetime.utcnow)
    filtering_criteria: Optional[Dict[str, Any]] = None

    @validator('papers')
    def validate_papers(cls, v):
        if not v:
            raise ValueError("At least one paper required in corpus")
        return v


class ExtractedKnowledge(BaseModel):
    """Schema for knowledge extracted from papers."""

    paper_id: str = Field(..., description="Source paper identifier")
    claims: List[str] = Field(..., description="Key claims extracted")
    methods: List[str] = Field(..., description="Methods/approaches used")
    datasets: List[str] = Field(..., description="Datasets mentioned")
    findings: List[str] = Field(..., description="Key findings")
    limitations: List[str] = Field(..., description="Limitations mentioned")
    future_work: List[str] = Field(..., description="Future work suggestions")


class HypothesisDesign(BaseModel):
    """Schema for hypothesis and experiment design."""

    hypothesis: str = Field(..., description="Testable hypothesis")
    null_hypothesis: str = Field(..., description="Null hypothesis")
    variables: Dict[str, str] = Field(..., description="Independent and dependent variables")
    metrics: List[str] = Field(..., description="Success metrics")
    test_type: str = Field(..., description="Type of test (statistical, simulation, etc.)")
    sample_size: Optional[int] = None
    confidence_level: float = Field(default=0.95, ge=0, le=1)
    methodology: str = Field(..., description="Detailed methodology")


class ExperimentResult(BaseModel):
    """Schema for experiment results."""

    experiment_id: str = Field(..., description="Unique experiment identifier")
    hypothesis_id: str = Field(..., description="Associated hypothesis ID")
    code: Optional[str] = Field(None, description="Experiment code (Python)")
    raw_results: Dict[str, Any] = Field(..., description="Raw experimental results")
    statistical_results: Optional[Dict[str, float]] = None
    visualizations: Optional[List[str]] = Field(None, description="Paths/URLs to visualizations")
    result_hash: str = Field(..., description="Hash of results for verification")
    execution_time: float = Field(..., description="Execution time in seconds")
    reproducible: Optional[bool] = None
    verification_score: Optional[float] = Field(None, ge=0, le=1)

    @validator('result_hash')
    def validate_hash(cls, v):
        if len(v) < 32:
            raise ValueError("Result hash must be at least 32 characters")
        return v


class Interpretation(BaseModel):
    """Schema for result interpretation."""

    experiment_id: str
    insights: List[str] = Field(..., min_items=1, description="Key insights")
    conclusions: List[str] = Field(..., min_items=1, description="Main conclusions")
    limitations: List[str] = Field(..., description="Study limitations")
    future_directions: List[str] = Field(..., description="Future research directions")
    confidence: float = Field(..., ge=0, le=1, description="Confidence in conclusions")
    supports_hypothesis: bool = Field(..., description="Whether results support hypothesis")


class BiasReport(BaseModel):
    """Schema for bias audit report."""

    methodology_biases: List[str] = Field(..., description="Detected methodology biases")
    data_biases: List[str] = Field(..., description="Detected data biases")
    selection_bias_score: float = Field(..., ge=0, le=1)
    confirmation_bias_score: float = Field(..., ge=0, le=1)
    overall_bias_score: float = Field(..., ge=0, le=1)
    recommendations: List[str] = Field(..., description="Recommendations to reduce bias")
    risk_level: str = Field(..., description="Risk level: low, medium, high")


class ComplianceReport(BaseModel):
    """Schema for ethics and compliance report."""

    plagiarism_score: float = Field(..., ge=0, le=1, description="Plagiarism detection score")
    citation_integrity: bool = Field(..., description="Citation integrity check passed")
    ethics_violations: List[str] = Field(default_factory=list, description="Ethics violations found")
    missing_citations: List[str] = Field(default_factory=list, description="Missing citations")
    compliance_score: float = Field(..., ge=0, le=1, description="Overall compliance score")
    approved: bool = Field(..., description="Whether paper is approved for publication")


class ResearchPaperSection(BaseModel):
    """Schema for a research paper section."""

    section_type: str = Field(..., description="Type: introduction, methods, results, discussion, conclusion")
    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section content (markdown/LaTeX)")
    citations: List[str] = Field(default_factory=list, description="Citations used in section")
    word_count: int = Field(..., ge=0)
    quality_score: Optional[float] = Field(None, ge=0, le=1)


class ResearchPaper(BaseModel):
    """Schema for complete research paper."""

    title: str = Field(..., description="Paper title")
    abstract: str = Field(..., description="Paper abstract", max_length=500)
    authors: List[str] = Field(..., description="Paper authors")
    sections: List[ResearchPaperSection] = Field(..., description="Paper sections")
    references: List[str] = Field(..., description="Bibliography")
    keywords: List[str] = Field(..., min_items=3, max_items=10)
    total_word_count: int = Field(..., ge=0)
    format: str = Field(default="markdown", description="Format: markdown, latex, pdf")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator('sections')
    def validate_sections(cls, v):
        required = {'introduction', 'methods', 'results', 'discussion', 'conclusion'}
        present = {s.section_type for s in v}
        missing = required - present
        if missing:
            raise ValueError(f"Missing required sections: {missing}")
        return v


class PeerReview(BaseModel):
    """Schema for peer review."""

    paper_id: str = Field(..., description="ID of paper being reviewed")
    reviewer_agent_id: str = Field(..., description="ID of reviewer agent")
    overall_score: float = Field(..., ge=0, le=10, description="Overall score (0-10)")
    scores: Dict[str, float] = Field(..., description="Detailed scores by category")
    strengths: List[str] = Field(..., min_items=1, description="Paper strengths")
    weaknesses: List[str] = Field(..., min_items=1, description="Paper weaknesses")
    suggestions: List[str] = Field(..., description="Improvement suggestions")
    recommendation: str = Field(..., description="accept, minor_revision, major_revision, reject")
    confidence: float = Field(..., ge=0, le=1, description="Reviewer confidence")

    @validator('recommendation')
    def validate_recommendation(cls, v):
        valid = {'accept', 'minor_revision', 'major_revision', 'reject'}
        if v not in valid:
            raise ValueError(f"Recommendation must be one of {valid}")
        return v


class ReputationUpdate(BaseModel):
    """Schema for reputation update."""

    agent_id: str = Field(..., description="Agent ID")
    task_id: str = Field(..., description="Task ID")
    success: bool = Field(..., description="Task success")
    quality_score: float = Field(..., ge=0, le=1, description="Quality score")
    feedback: Optional[str] = None
    new_reputation_score: float = Field(..., ge=0, le=1)
    new_payment_multiplier: float = Field(..., ge=0.5, le=2.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)