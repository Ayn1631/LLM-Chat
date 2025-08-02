from .Graph_RAG_Search import chain
from .config import debug, retry
from .base import graph
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain.text_splitter import CharacterTextSplitter
from tqdm import tqdm, trange
import os
from langchain_core.documents import Document
import threading

__all__ = (
    'GraphRAG'
)

class GraphRAG:
    def __init__(self, chunk_size=256, chunk_overlap=64):
        self.chain = chain
        self.retry = retry
        self.graph = graph
        self.text_splitter = CharacterTextSplitter(separator="", chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def __call__(self, req):
        return self._query(req)

    def _query(self, req):
        res = ''
        for i in range(self.retry):
            try:
                res = self.chain.invoke({"question": req})
                break
            except Exception as e:
                print(f'ERROR: 知识库搜索报错_{i}!', str(e))
        else:
            return ''
        return res

    def clear(self, file_name: str = None):
        if file_name:
            file_name = os.path.basename(file_name)
            # 删除与指定 source 的 Document 节点通过 MENTIONS 关系连接的实体节点
            self.graph.query(
                """
                MATCH (doc:Document {source: $file_name})-[:MENTIONS]->(entity)
                DETACH DELETE entity
                """,
                {"file_name": file_name}
            )
            # 删除具有指定 source 的 Document 节点
            self.graph.query(
                "MATCH (doc:Document {source: $file_name}) DETACH DELETE doc",
                {"file_name": file_name}
            )
        else:
            # 删除所有节点和关系
            self.graph.query("MATCH (n) DETACH DELETE n")

    def up(self, file_path, llm):
        """
        上传并构建图谱：
        - 为每个文档节点设置 metadata type 为来源文件名
        """
        graph_docs = []

        def Run(doc__, llm_transformer):
            nonlocal graph_docs
            res = llm_transformer.process_response(doc__)
            with threading.Lock():
                graph_docs.append(res)

        if file_path is None:
            return

        llm_transformer = LLMGraphTransformer(llm=llm, ignore_tool_usage=True)
        print('---当前模型: ', llm.model_name)

        if not os.path.exists(file_path):
            print('上传为文件内容')
            text = file_path
            file_name = "custom_input"
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                print('---读取文件: ', file_path)
                text = f.read()
            file_name = os.path.basename(file_path)

        existing_docs = self.graph.query(
            "MATCH (doc:Document {source: $file_name}) RETURN doc",
            {"file_name": file_name}
        )
        if existing_docs:
            print(f"文件 {file_name} 已存在，跳过上传。")
            return
        
        doc = Document(text, metadata={"source": file_name})
        # docs = [doc]
        docs = self.text_splitter.split_documents([doc])
        graph_docs = []

        thread_num = 3
        print('---线程数: ', thread_num)
        print('---文档数: ', len(docs))
        print('---开始转换文档: ')
        for star_idx in trange(0, len(docs), thread_num, desc='Transformer', unit='Epoch'):
            threads = []
            for i in range(thread_num):
                if star_idx + i >= len(docs):
                    break
                t = threading.Thread(target=Run, args=[docs[star_idx + i], llm_transformer])
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

        print('---开始上传文档: ')
        for x in tqdm(graph_docs, desc='Up', unit='cnt'):
            try:
                # 在上传时添加文件名作为 metadata type
                graph.add_graph_documents(
                    [x],
                    baseEntityLabel=True,
                    include_source=True,
                )
            except Exception as e:
                print('ERROR: 上传文档失败:', str(e))
                print(x)
        print('---运行结束!')
        print('~' * 100)
