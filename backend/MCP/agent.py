# Standard library imports
import asyncio
import logging
import os
import sys
from .config import mcp_configs
# Third-party imports
try:
    from dotenv import load_dotenv
    from langchain.chat_models import init_chat_model
    from langchain.schema import HumanMessage
    from langgraph.prebuilt import create_react_agent
except ImportError as e:
    print(f'\nError: Required package not found: {e}')
    print('Please ensure all required packages are installed\n')
    sys.exit(1)

# Local application imports
from langchain_mcp_tools import convert_mcp_to_langchain_tools

# A very simple logger
def init_logger() -> logging.Logger: # 初始化
    
    logging.basicConfig(
        level=logging.INFO,  # logging.DEBUG,
        format='\x1b[90m[%(levelname)s]\x1b[0m %(message)s'
    )
    return logging.getLogger()

async def run(llm, messages):  # 运行接口函数
    try:
        
        tools, cleanup = await convert_mcp_to_langchain_tools(
            mcp_configs,
            init_logger()
        )  # 获得工具
        print(tools)
        agent = create_react_agent(
            llm,
            tools
        )  # 创建agent

        print('\x1b[33m')  # color to yellow
        print(messages)
        print('\x1b[0m')   # reset the color
        result = agent.invoke({'messages': messages}, stream_mode="messages")
        # return result
        async for chunk in result:
            # print(chunk[0].content, end="", flush=True)
            res = chunk[0].content
            if len(res)<=20 and 'INFO' not in res:
                yield res
    finally:
        if cleanup is not None:
            await cleanup()



if __name__ == '__main__':
    load_dotenv()
    from langchain_openai import ChatOpenAI
    _llm = ChatOpenAI(
        openai_api_base="https://chatapi.littlewheat.com/v1",
        openai_api_key="sk-DgMNurbu7w3ZtJaV1jPpTD5SGS9XugLnnfGp0Lm6dDn4Tk5O",
        model="gpt-4o",
        temperature=0
    )
    async def main():
        async for res in run(_llm, '学校周围有什么美食'):
            print(res, end="", flush=True)
    asyncio.run(main())