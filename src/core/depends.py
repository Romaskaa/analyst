from typing import Final

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    TextSplitter,
)
from pydantic import SecretStr

from ..agents.prompts import PROMPT_CWV, PROMPT_MARKDOWN, PROMPT_RESULT
from ..settings import settings
from .schemas import (
    CWVReport,
    ExpertiseSite,
    GenerateAIOContent,
    ListGeneratedAlt,
    SemanticCore,
    SEOAnalysisReport,
    SiteAnalysisReport,
    SpecializationSite,
)

CHUNK_SIZE = 1500
CHUNK_OVERLAP = 50
TIMEOUT = 120
MININUM_COSINE_SIMILARITY = 0.45

CHUNK_SIZE = 1500
CHUNK_OVERLAP = 50


yandex_gpt: ChatOpenAI = ChatOpenAI(
    api_key=SecretStr(settings.yandexcloud.api_key),
    model=f"gpt://{settings.yandexcloud.folder_id}/yandexgpt/latest",
    base_url="https://llm.api.cloud.yandex.net/v1",
    max_retries=3,
)

gpt_oss_120b: ChatOpenAI = ChatOpenAI(
    api_key=SecretStr(settings.yandexcloud.api_key),
    model=f"gpt://{settings.yandexcloud.folder_id}/gpt-oss-120b/latest",
    base_url="https://llm.api.cloud.yandex.net/v1",
    max_retries=3,
)

gemma_3_27b_it: ChatOpenAI = ChatOpenAI(
    api_key=SecretStr(settings.yandexcloud.api_key),
    model=f"gpt://{settings.yandexcloud.folder_id}/gemma-3-27b-it/latest",
    base_url="https://llm.api.cloud.yandex.net/v1",
    max_retries=3,
)

rag_stepfun: ChatOpenAI = ChatOpenAI(
    api_key=SecretStr(settings.openrouter.api_key),
    model="stepfun/step-3.5-flash:free",
    base_url=settings.openrouter.base_url,
    max_retries=3,
)

text_splitter: Final[TextSplitter] = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    length_function=len,
    separators=["\n\n", "\n", " ", ""],
)

parser_markdown = PydanticOutputParser(pydantic_object=SEOAnalysisReport)

parser_specialization = PydanticOutputParser(pydantic_object=SpecializationSite)

parser_expertise = PydanticOutputParser(pydantic_object=ExpertiseSite)

parser_aio_content = PydanticOutputParser(pydantic_object=GenerateAIOContent)


markdown_prompt_template: PromptTemplate = PromptTemplate(
    template=PROMPT_MARKDOWN,
    input_variables=["query"],
    partial_variables={"format_instructions": parser_markdown.get_format_instructions()},
)


parser_cwv = PydanticOutputParser(pydantic_object=CWVReport)

parser_result = PydanticOutputParser(pydantic_object=SiteAnalysisReport)

parser_sc = PydanticOutputParser(pydantic_object=SemanticCore)

parser_generated_alt = PydanticOutputParser(pydantic_object=ListGeneratedAlt)

cwv_prompt_template: PromptTemplate = PromptTemplate(
    template=PROMPT_CWV,
    input_variables=["query"],
    partial_variables={"format_instructions": parser_cwv.get_format_instructions()},
)

result_prompt_template: PromptTemplate = PromptTemplate(
    template=PROMPT_RESULT,
    input_variables=["sitemap", "markdown", "seo_issue", "cwv"],
    partial_variables={"format_instructions": parser_result.get_format_instructions()},
)
