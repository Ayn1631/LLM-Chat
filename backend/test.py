import os
import pandas as pd
from langchain_neo4j import Neo4jGraph
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate

# 设置环境变量（请根据你的实际情况修改）
from dotenv import load_dotenv
load_dotenv()
# 简单提示词（可根据需求调整）
SYSTEM_PROMPT = """
你是一个康养领域的知识图谱构建专家。  
请从下面的问答内容中提取实体和它们之间的关系，构建知识图谱。  
实体示例包括：问题中的关键词、回答中的关键动作、物品、护理方法等。  
关系示例包括：问题与回答之间的“解答”关系，关键词与回答中的动作或物品之间的“关联”等。  
输出JSON格式，包含nodes和relationships数组。
"""

def read_excel_to_documents(file_path: str) -> list[Document]:
    df = pd.read_excel(file_path, header=None)  # 不用第一行做列名
    documents = []
    for idx, row in df.iterrows():
        text = f"问题：{row[0]}\n关键词：{row[1]}\n回答：{row[2]}"
        documents.append(Document(page_content=text))
    return documents


def build_knowledge_graph_from_documents(documents: list[Document]) -> Neo4jGraph:
    graph = Neo4jGraph(
        url=os.environ["NEO4J_URI"],
        username=os.environ["NEO4J_USERNAME"],
        password=os.environ["NEO4J_PASSWORD"]
    )
    llm = ChatOpenAI(model="deepseek-v3", temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT),
        HumanMessagePromptTemplate.from_template("{input}")  # 这里变量名必须是input
    ])
    transformer = LLMGraphTransformer(llm=llm, prompt=prompt, ignore_tool_usage=True)

    graph_documents = transformer.convert_to_graph_documents(documents)
    graph.add_graph_documents(graph_documents, baseEntityLabel=True, include_source=True)

    print("知识图谱构建完成！")
    return graph

if __name__ == "__main__":
    excel_path = r"C:\Users\20753\Desktop\医疗问答.xlsx"
    docs = read_excel_to_documents(excel_path)
    graph = build_knowledge_graph_from_documents(docs)

    # 这里你可以写查询函数，或者直接用 Neo4j 浏览器查看结果
