from langchain_neo4j.vectorstores.neo4j_vector import remove_lucene_chars
from .get_entity import entity_chain
from .base import graph
from .config import debug, retry
__all__ = (
    'retriever'
)

def generate_full_text_query(input: str) -> str:
    """为给定的输入字符串生成全文搜索查询。

    此函数构造适合全文搜索的查询字符串。
    它通过将输入字符串拆分为单词并附加一个
    相似度阈值（~2 个更改的字符）与每个单词匹配，然后组合
    他们使用 AND 运算符。用于映射用户问题中的实体
    添加到数据库值中，并允许一些拼写错误。"""
    full_text_query = ""
    words = [el for el in remove_lucene_chars(input).split() if el]
    for word in words[:-1]:
        full_text_query += f" {word}~2 AND"
    full_text_query += f" {words[-1]}~2"
    # return full_text_query.strip()
    return input

def structured_retriever(question: str) -> str:
    """
    Collects the neighborhood of entities mentioned
    in the question
    """
    result = ""
    for i in range(retry): 
        try:
            entities = entity_chain.invoke({"question": question})
        
            if isinstance(entities['res'], list):
                break
        except Exception as e:
            print('ERROR: 格式错误: ', str(e))
    else:
        print('ERROR: 多次重试仍然《提取到的实体》格式错误')
        return ''
    if debug:
        print('分割出的实体列表为: ', str(entities))
    for entity in entities['res']:
        response = graph.query(
            """
            CALL db.index.fulltext.queryNodes('entity', $query, {limit:2})
            YIELD node,score
            MATCH (node)-[r]-(neighbor) // 通过这步匹配来明确neighbor的来源，可根据实际关系调整这里的模式
            CALL (node, neighbor) {
              MATCH (node)-[r:!MENTIONS]->(neighbor)
              RETURN node.id + ' - ' + type(r) + ' -> ' + neighbor.id AS output
              UNION ALL
              MATCH (node)<-[r:!MENTIONS]-(neighbor)
              RETURN neighbor.id + ' - ' + type(r) + ' -> ' +  node.id AS output
            }
            RETURN output LIMIT 10
            """,
            {"query": generate_full_text_query(entity)},
        )
        if debug:
            print('generate_full_text_query(entity): ', generate_full_text_query(entity))
        result += "\n".join([el['output'] for el in response])
    return result
    

def retriever(question: str):
    if debug:
        print(f"Search query: {question}")
    structured_data = structured_retriever(question)
    # unstructured_data = [el.page_content for el in vector_index.similarity_search(question)]
    final_data = f"""Structured data:
{structured_data}
    """
    if debug:
        print(f'~ final_data({question}): ', final_data)
    return final_data