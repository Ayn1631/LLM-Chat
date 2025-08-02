# 合并 Graph_RAG 文件夹中的所有内容

# base.py
from langchain_community.graphs import Neo4jGraph as _Neo4jGraph
import os as _os
import dotenv as _dotenv
_dotenv.load_dotenv()

_graph = _Neo4jGraph(refresh_schema=False)  # 初始化图数据库对象

# config.py
_debug = True  # 调试模式开关
_retry = 3  # 最大重试次数

# get_entity.py
from .base import _graph
from LLM import llm as _llm
from typing import List as _List
from langchain_core.pydantic_v1 import BaseModel as _BaseModel, Field as _Field
from langchain_core.prompts import ChatPromptTemplate as _ChatPromptTemplate

__all__ = (
    'entity_chain',  # 导出的实体链对象
)

_graph.query(
    "CREATE FULLTEXT INDEX entity IF NOT EXISTS FOR (e:__Entity__) ON EACH [e.id]")  # 创建全文索引

class _Entities(_BaseModel):
    names: _List[str] = _Field(
        ...,
        description="所有在文本中出现的实体名称，包括人名和组织名",
    )

_prompt = _ChatPromptTemplate.from_messages([
    ("system", "从文本中提取 organization 和 person 实体，并返回 JSON 格式的输出。"),
    ("human", "从以下内容中提取信息 input: {question}"),
])

import json as _json

def _res2json(res):
    try:
        resdic = _json.loads(res)
    except:
        staridx = res.find('```json')
        resdic = res[staridx+len('```json'):res.find('```', staridx+1)]
        resdic = _json.loads(resdic)
    return resdic

class _OutHelper:
    def invoke(self, res) -> _Entities:
        return _res2json(res.content)

_entity_chain = _prompt | _llm | _OutHelper()  # 构建实体链

# get_retriever.py
from langchain_community.vectorstores.neo4j_vector import remove_lucene_chars as _remove_lucene_chars
from .get_entity import _entity_chain
from .base import _graph
from .config import _debug, _retry

def _generate_full_text_query(input: str) -> str:
    words = [el for el in _remove_lucene_chars(input).split() if el]
    return " AND ".join([f"{word}~2" for word in words])

def _structured_retriever(question: str) -> str:
    result = ""
    for i in range(_retry):
        try:
            entities = _entity_chain.invoke({"question": question})
            if isinstance(entities['res'], list):
                break
        except Exception as e:
            print('ERROR: 格式错误: ', str(e))
    else:
        return ''
    for entity in entities['res']:
        response = _graph.query(
            "CALL db.index.fulltext.queryNodes('entity', $query, {limit:2}) YIELD node,score MATCH (node)-[r]-(neighbor) RETURN node.id + ' - ' + type(r) + ' -> ' + neighbor.id AS output",
            {"query": _generate_full_text_query(entity)},
        )
        result += "\n".join([el['output'] for el in response])
    return result

def retriever(question: str):
    structured_data = _structured_retriever(question)
    return f"Structured data:\n{structured_data}\n"

# Graph_RAG_Search.py
from langchain_core.prompts.prompt import PromptTemplate
from typing import Tuple, List
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableBranch, RunnableLambda, RunnableParallel, RunnablePassthrough
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from .get_retriever import retriever

_template = """Given the following conversation and a follow up question, rephrase the follow up question to be a standalone question, in its original language.\nChat History:\n{chat_history}\nFollow Up Input: {question}\nStandalone question:"""
CONDENSE_QUESTION_PROMPT = PromptTemplate.from_template(_template)

def _format_chat_history(chat_history: List[Tuple[str, str]]) -> List:
    buffer = []
    for human, ai in chat_history:
        buffer.append(HumanMessage(content=human))
        buffer.append(AIMessage(content=ai))
    return buffer

_search_query = RunnableBranch(
    (RunnableLambda(lambda x: bool(x.get("chat_history"))), RunnablePassthrough.assign(chat_history=lambda x: _format_chat_history(x["chat_history"])) | CONDENSE_QUESTION_PROMPT | ChatOpenAI(temperature=0) | StrOutputParser()),
    RunnableLambda(lambda x: x["question"]),
)

template = """根据以下文档和提问, 回答问题：\n{context}\n\n问题：{question}\n使用中文回答!语言生动且简洁!。\n答案："""
prompt = ChatPromptTemplate.from_template(template)

chain = RunnableParallel({"context": _search_query | retriever, "question": RunnablePassthrough()})