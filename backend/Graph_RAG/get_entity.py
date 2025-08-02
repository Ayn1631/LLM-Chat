from .base import graph
from LLM import llm
from typing import List
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate

__all__ = (
    'entity_chain'
)

graph.query(
    "CREATE FULLTEXT INDEX entity IF NOT EXISTS FOR (e:__Entity__) ON EACH [e.id]")

# Extract entities from text
class Entities(BaseModel):
    """Identifying information about entities.""" 

    names: List[str] = Field(
        ...,
        description="All the person, organization, or business entities that "
        "appear in the text",
    )

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "您正在从文本中提取 organization 和 person 实体。并且只返回json格式的输出！json中，只需要有res键，值为一个列表，内容你找到的所有organization和person实体名。",
        ),
        (
            "human",
            "使用给定的格式从以下内容中提取信息"
            "input: {question}",
        ),
    ]
)

import json
def res2json(res):
    try:
        resdic = json.loads(res)
    except:
        # pattern = r'```json(.*?)```'
        staridx = res.find('```json')
        resdic = res[staridx+len('```json'):res.find('```', staridx+1)]
        resdic = json.loads(resdic)
        # print(resdic)
        # print(type(resdic))
    return resdic
class outHelper:
    def __init__(self):
        pass
    def invoke(self, res) -> Entities:
        return res2json(res.content)
    
    def __call__(self, res) -> Entities:
        return res2json(res.content)

entity_chain = prompt | llm | outHelper()