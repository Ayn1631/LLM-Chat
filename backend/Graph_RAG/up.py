import os
from langchain_community.graphs import Neo4jGraph
from langchain.text_splitter import TokenTextSplitter
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_core.documents import Document
from Graph_RAG.base import *
import threading
from tqdm.notebook import tqdm, trange
import dotenv
dotenv.load_dotenv()

graph = Neo4jGraph(refresh_schema=False)

from langchain_text_splitters import TokenTextSplitter

# 定义分块策略
text_splitter = TokenTextSplitter(chunk_size=1024, chunk_overlap=24)

from langchain_experimental.graph_transformers import LLMGraphTransformer

graph_docs = []

def Run(doc__, llm_transformer):
    global graph_docs
    # print(doc__)
    res = llm_transformer.process_response(doc__)
    with threading.Lock():
        graph_docs.append(res)

def clear():
    print('---清除图谱数据: ')
    graph.query("MATCH (n) DETACH DELETE n")

def up(file_path, llm):
    if file_path is None:
        return
    llm_transformer = LLMGraphTransformer(llm=llm, ignore_tool_usage=True)
    print('---当前模型: ', llm.model_name)
    global graph_docs
    if not os.path.exists(file_path):
        # raise ValueError(f"File {file_path} does not exist.")
        text = file_path
    else:
        with open(file_path, 'r', encoding='utf-8') as f:
            print('---读取文件: ', file_path)
            text = f.read()
            
    doc = Document(text)
    print('---分块文档: ')
    # docs = text_splitter.split_documents([doc])
    docs = [doc]
    graph_docs = []
    

            
    thread_num = 4
    print('---线程数: ', thread_num)
    print('---文档数: ', len(docs))
    print('---开始转换文档: ')
    for star_idx in trange(0, len(docs), thread_num, desc='Transformer', unit='Epoch'):
        threads = []
        for i in range(thread_num):
            if star_idx + i >= len(docs):
                break
            # print(type(docs[star_idx + i]))
            t = threading.Thread(target=Run, args=[docs[star_idx + i], llm_transformer])
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
    
    print('---开始上传文档: ')
    for x in tqdm(graph_docs, desc='Up', unit='cnt'):
        try:
            graph.add_graph_documents(
            [x], 
            baseEntityLabel=True, 
            include_source=True
            )
        except Exception as e:
            print('ERROR: ', str(e))
            print(x)
    print('---运行结束!')
    print('~'*100)

if __name__ == '__main__':
    import os
    root = 'Graph_RAG/books'
    for file in os.listdir(root):
        file_path = os.path.join(root, file)
        up(file_path)