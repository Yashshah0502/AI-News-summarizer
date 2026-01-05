from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

class ArticleSummary(BaseModel):
    one_liner: str
    bullets: list[str]

_prompt = ChatPromptTemplate.from_messages([
    ("system", "Return JSON only. Be concise."),
    ("user", "Title: {title}\n\nArticle:\n{content}\n\nSummarize into 1 one-liner + 3 bullets.")
])

def summarize(title: str, content: str) -> ArticleSummary:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    chain = _prompt | llm.with_structured_output(ArticleSummary)
    return chain.invoke({"title": title, "content": content[:6000]})
