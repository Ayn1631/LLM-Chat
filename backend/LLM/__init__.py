from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 构建LLM
llm = ChatOpenAI(model=os.environ["Model"], temperature=int(os.environ['temperature']))