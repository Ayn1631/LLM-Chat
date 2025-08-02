# GraphRAG基础指导

## 该库使用方法

1. 构建***.env***文件

```.env
PYTHONIOENCODING = utf-8
# LLM
OPENAI_API_KEY = xxx
OPENAI_API_BASE = xxx
Model = xxx
# Model = qwen2.5-32b-instruct
temperature = 0

# Neo4j
NEO4J_URI = neo4j+s://4ddf9113.databases.neo4j.io
NEO4J_USERNAME = neo4j
NEO4J_PASSWORD = plkPPNzpT9mJY2vTywLlm0EdTjrkpyFrsaaZWvqA1uE
```

2. 运行代码

```python
from Graph_RAG import GraphRAG, graph
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
# 加载环境变量
load_dotenv()

# 构建LLM
llm = ChatOpenAI(model=os.environ["Model"], temperature=int(os.environ['temperature']))

graphRAG = GraphRAG()
graphRAG.clear()
file_path = r'D:/xxx/xxx.txt'

graphRAG.up(file_path, llm=llm)
graphRAG._query('孙太白')
```



## 其他介绍

1. 如果使用*不能使用* ***function_call***的模型:

	则设置 ignore_tool_usage=True, 否则为False(或不设)

	位置于GraphRAG/\_\_init\_\_.py  **73行**

	![image-20250619165948629](https://raw.githubusercontent.com/Ayn1631/image_datas/main/notebook_images/image-20250619165948629.png)

2. 对于LLMGraphTransformer的介绍

	```markdown
	它允许指定要包含在输出图中的节点和关系类型的约束。
	该类支持提取节点和关系的属性。
	
	参数：
	    llm (BaseLanguageModel): 支持结构化输出的语言模型实例。
	    allowed_nodes (List[str], optional): 指定图中允许的节点类型。
	      默认为空列表，允许所有节点类型。
	    allowed_relationships (List[str], optional): 指定图中允许的关系类型。
	      默认为空列表，允许所有关系类型。
	    prompt (Optional[ChatPromptTemplate], optional): 传递给LLM的提示，包含附加说明。
	    strict_mode (bool, optional): 确定转换器是否应应用过滤器以严格遵守
	      `allowed_nodes` 和 `allowed_relationships`。默认为True。
	    node_properties (Union[bool, List[str]]): 如果为True，LLM可以从文本中提取任何
	      节点属性。或者，可以提供有效属性的列表，限制提取为指定的属性。
	    relationship_properties (Union[bool, List[str]]): 如果为True，LLM可以提取
	      任何关系属性。或者，可以提供有效属性的列表，限制提取为指定的属性。
	    ignore_tool_usage (bool): 指示转换器是否应绕过语言模型的结构化输出功能。
	      如果设置为True，转换器将不会使用语言模型的本地函数调用功能来处理结构化输出。
	      默认为False。
	    additional_instructions (str): 允许您向提示中添加附加说明，而无需更改整个提示。
	
	示例：
	    .. code-block:: python
	        from langchain_experimental.graph_transformers import LLMGraphTransformer
	        from langchain_core.documents import Document
	        from langchain_openai import ChatOpenAI
	
	        llm=ChatOpenAI(temperature=0)
	        transformer = LLMGraphTransformer(
	            llm=llm,
	            allowed_nodes=["Person", "Organization"])
	
	        doc = Document(page_content="Elon Musk is suing OpenAI")
	        graph_documents = transformer.convert_to_graph_documents([doc])
	```

3. 如果生成的效果不好, 可以自行构建节点和关系列表

	```python
	from langchain_community.graphs.graph_document import GraphDocument, Node, Relationship
	from langchain_core.documents import Document
	
	# 自定义添加实体与关系
	a = Node(id='李白', type='人物')  # 实体a
	b = Node(id='诗人', type='职业')  # 实体b
	re = Relationship(source=a, target=b, type='职业')  # 关系
	g = GraphDocument(nodes=[a, b], relationships=[re], source=Document(page_content='李白是诗人'))
	
	
	from Graph_RAG import graph
	from tqdm import tqdm
	for x in tqdm([g], desc='Up', unit='cnt'):
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
	```

	