from enum import StrEnum

from langchain.agents import AgentState
from pydantic import BaseModel, Field


class State(AgentState):
    request: str
    importer_result: dict | None
    analyst_result: dict | None
    aio_result: dict | None
    seo_result: dict | None
    total_tokens: int
    total_money: float


class HeaderAnalysis(BaseModel):
    tag: str  # H1, H2, H3...
    text: str
    contains_keywords: bool
    issues: list[str] | None = []


class KeywordAnalysis(BaseModel):
    keyword: str
    count: int
    density: float  # в процентах


class LinkAnalysis(BaseModel):
    url: str
    anchor_text: str
    is_internal: bool
    is_broken: bool | None = None


class ImageAnalysis(BaseModel):
    src: str
    alt_text: str | None
    has_keywords: bool
    issues: list[str] | None = []


class ReadabilityAnalysis(BaseModel):
    word_count: int
    sentence_count: int
    paragraphs_count: int
    readability_score: float | None = None  # например, Flesch score
    issues: list[str] | None = []


class MetadataAnalysis(BaseModel):
    title: str | None
    description: str | None
    issues: list[str] | None = []


class SEOAnalysisReport(BaseModel):
    headers: list[HeaderAnalysis]
    keywords: list[KeywordAnalysis]
    links: list[LinkAnalysis]
    images: list[ImageAnalysis]
    readability: ReadabilityAnalysis
    metadata: MetadataAnalysis
    overall_score: float | None = None
    recommendations: list[str]


class CWVMetricSummary(BaseModel):
    category: str | None
    percentile: float | None
    fast_percent: float | None
    average_percent: float | None
    slow_percent: float | None


class CWVReport(BaseModel):
    overall_category: str | None
    performance_score: float | None
    seo_score: float | None

    fcp: CWVMetricSummary | None
    lcp: CWVMetricSummary | None
    cls: CWVMetricSummary | None
    ttfb: CWVMetricSummary | None
    inp: CWVMetricSummary | None

    critical_seo_issues: list[dict] | None
    conclusion: str
    recommendations: list[str]


class GenerateAIOContent(BaseModel):
    transformed_content: str = Field(description="Преобразованный контент")
    placement_recommendation: str = Field(
        description="Рекомендация по размещению текста на странице"
    )


class Problem(BaseModel):
    title: str = Field(..., description="Краткое название проблемы")
    description: str = Field(..., description="Понятное объяснение проблемы")
    severity: str = Field(..., description="Уровень критичности: low | medium | high | critical")
    recommendation: str = Field(..., description="Рекомендация по исправлению")


class SEOScore(BaseModel):
    score: int = Field(..., ge=0, le=100, description="Оценка SEO от 0 до 100")
    summary: str = Field(..., description="Краткое пояснение оценки")


class PerformanceScore(BaseModel):
    score: int = Field(..., ge=0, le=100, description="Оценка производительности от 0 до 100")
    lcp: float | None = Field(None, description="Largest Contentful Paint (сек)")
    fid: float | None = Field(None, description="First Input Delay (мс)")
    cls: float | None = Field(None, description="Cumulative Layout Shift")
    summary: str = Field(..., description="Краткое пояснение оценки производительности")


class SiteAnalysisReport(BaseModel):
    overall_summary: str = Field(..., description="Общее резюме состояния сайта")
    sitemap_analysis: str = Field(..., description="Выводы по sitemap")
    content_analysis: str = Field(..., description="Анализ markdown и HTML структуры")
    core_web_vitals_analysis: str = Field(..., description="Анализ Core Web Vitals простым языком")
    issues: list[Problem] = Field(default_factory=list, description="Список найденных проблем")
    recommendations: list[str] = Field(default_factory=list, description="Общие рекомендации")
    seo: SEOScore
    performance: PerformanceScore

    @property
    def to_dict(self) -> dict:
        return {
            "overall_summary": self.overall_summary,
            "sitemap_analysis": self.sitemap_analysis,
            "content_analysis": self.content_analysis,
            "core_web_vitals_analysis": self.core_web_vitals_analysis,
            "issues": [i.model_dump() for i in self.issues],
            "recommendations": self.recommendations,
            "seo": self.seo.model_dump(),
            "performance": self.performance.model_dump(),
        }


class SpecializationSite(BaseModel):
    specialization: str


class ExpertiseSite(BaseModel):
    main_area: str
    key_user_problem: str
    benefit_to_the_user: str


class SemanticCore(BaseModel):
    high_frequency: list[str] = Field(description="Высокочастотные запросы")
    medium_frequency: list[str] = Field(description="Среднечастотные запросы")
    low_frequency: list[str] = Field(description="Низкочастотные запросы")


class Role(StrEnum):
    AI = "assistant"
    USER = "user"


class Chat(BaseModel):
    role: Role
    content: str


class QueueData(BaseModel):
    urls: list
    start_url: str
    base_url: str
    passed_urls: set
    found: bool
    result: list[dict]


class GeneratedAlt(BaseModel):
    alt: str = Field(description="Сгенерированный альт тег")
    url: str = Field(description="Ссылка для которой был сегенерирован альт тег")


class ListGeneratedAlt(BaseModel):
    result: list[GeneratedAlt]

class RAGGenerateRequest(BaseModel):
    topic: str
    knowledge_text: str
    top_k: int = Field(default=5, ge=1, le=20)
    chunk_size: int = Field(default=500, ge=100, le=4000)

class RAGGenerateResponse(BaseModel):
    content: str

class GenerateContentRequest(BaseModel):
    topic: str


class UrlRequest(BaseModel):
    url: str


class TechnicalAuditRequest(BaseModel):
    url: str
    depth: int = Field(default=3, ge=1, le=10)


class MetrikaOAuthRequest(BaseModel):
    oauth_token: str
    counter_id: str

class UploadResponse(BaseModel):
    path: str