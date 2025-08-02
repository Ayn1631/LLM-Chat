from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Any
import os
import json
import asyncio
from LLM import llm  # 导入LLM模型接口
from MCP import agent  # 导入多智能体协作模块

# 导入RAG(检索增强生成)模块并初始化知识库
# from RAG import knowledgeBase, query
# kb = knowledgeBase.KnowledgeBase(debug=True)

from bge_RAG import RAG
# 从环境变量获取文本分块参数并初始化RAG
kb = RAG(max_len=os.environ['max_len'], overlap_len=os.environ['overlap_len'])

# 加载已保存的知识库索引
kb.load()
# kb.add()
# 取消注释以下代码可在启动时自动加载指定目录下的所有文本文件
# root = 'uploaded_files'
# for file in os.listdir(root):
#     path = os.path.join(root, file)
#     if os.path.isfile(path) and path.endswith('.txt'):
#         kb.add(path)
#         # graph_rag.up(path, llm)

# 初始化FastAPI应用
app = FastAPI()

# 配置CORS跨域资源共享，允许来自Vue开发服务器的请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vue开发服务器的默认地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 定义API请求模型
class TextRequest(BaseModel):
    messages: Any  # 对话历史消息
    useRAG: bool = False  # 是否使用RAG增强
    useMCP: bool = False  # 是否使用多智能体协作处理

# 定义实体分析模型
class Entity(BaseModel):
    type: str  # 实体类型
    text: str  # 实体文本

# 定义文本分析结果模型
class Analysis(BaseModel):
    sentiment: str  # 情感分析结果
    keywords: List[str]  # 关键词列表
    entities: List[Entity]  # 实体列表

# 定义API响应模型
class TextResponse(BaseModel):
    originalText: str  # 原始文本
    processedText: str  # 处理后的文本
    analysis: Analysis  # 文本分析结果


# 生成带RAG增强的流式响应
async def generate_stream_RAG(request):
    try:
        # 提取对话历史和最新用户输入
        message = request.messages[:-1]
        info = request.messages[-1]
        print('INFO: ', info)
        
        # 构建用于查询改写的消息格式
        messages = []
        for m in message[:-1]:
            messages.append({'role':m['type'], 'content':m['text']})
        user_input = message[-1]['text']
        print('用户输入: ', user_input)
        
        # 调用LLM进行查询改写，提高检索准确性
        change_input = llm.invoke([{'role':'user', 'content':f'''你需要根据历史信息和用户输入, 为我进行查询改写.\n---例如: 用户在历史信息中提问:厨房有什么东西?你回答有菜刀, 冰箱等. 然后用户提问:第一个的作用. 你应该改写查询为:厨房里菜刀的作用? 如果用户提问一个新的话题, 改写后的内容应该保持不变!如:历史提问:今天吃什么? 提问:明天去哪玩? 你应该保持不变, 输出:明天去哪玩?\n---重要的: 你应该除了改写后的输入, 其他什么都不要输出! \n---历史信息:{message}; \n---用户输入: {user_input} ---输出:'''}]).content
        print(f'查询改写: {user_input} -> {change_input}')
        
        # 使用改写后的查询进行RAG检索，获取相关文档
        Unstructured = kb.req(change_input, top_k=3)
        
        # 保留结构化知识检索的接口(当前未启用)
        # Structured = graph_rag(user_input)['context']
        Structured = ''
        print('-'*100)
        # print('graph_RAG结果: ', Structured)
        print('~ RAG结果: \n', Unstructured)
        print('-'*100)
        
        # 构建提示词，将检索结果和用户问题一起提供给LLM
        prompt = f'''
你是一个智能问答系统, 你会完全按照用户的要求进行返回.
---需求
你会根据知识库的查询内容(Unstructured documents) 和对话历史信息进行智能回答.
- Unstructured documents:
{Unstructured}
--- 输入:
{user_input}
--- 输出:
'''
        
        messages.append({'role':'user', 'content':prompt})
        print('messages: ', messages)
        
        # 流式调用LLM并返回结果
        for chunk in llm.stream(messages):
            if chunk.content:
                content = chunk.content
                # 将数据包装成事件流格式
                yield content
                await asyncio.sleep(0.01)  # 控制流速度

    except Exception as e:
        # 发生异常时返回错误信息
        error_response = {'error': str(e), 'done': True}
        print(f"发生错误: {error_response}")
        yield f"{json.dumps(error_response)}"


# 生成普通流式响应(不使用RAG)
async def generate_stream(request):
    try:
        # 提取对话历史和最新用户输入
        message = request.messages[:-1]
        info = request.messages[-1]
        
        # 构建消息格式
        messages = [{'role': 'system', 'content':message[0]['text']}]
        for m in message[1:]:
            messages.append({'role':m['type'], 'content':m['text']})
        print('INFO: ', info)

        # 流式调用LLM并返回结果
        for chunk in llm.stream(messages):
            if chunk.content:
                content = chunk.content
                # 将数据包装成事件流格式
                yield content
                await asyncio.sleep(0.01)  # 控制流速度

    except Exception as e:
        # 发生异常时返回错误信息
        error_response = {'error': str(e), 'done': True}
        print(f"发生错误: {error_response}")
        yield f"{json.dumps(error_response)}"

# 生成多智能体协作处理的流式响应
async def generate_stream_mcp(request):
    try:
        # 提取对话历史和最新用户输入
        message = request.messages[:-1]
        info = request.messages[-1]
        
        # 构建消息格式
        messages = [{'role': 'system', 'content':message[0]['text']}]
        for m in message[1:]:
            messages.append({'role':m['type'], 'content':m['text']})
        print('INFO: ', info)

        # 调用多智能体协作处理并流式返回结果
        async for chunk in agent.run(llm, messages):
            yield chunk
            await asyncio.sleep(0.01)  # 控制流速度

    except Exception as e:
        # 发生异常时返回错误信息
        error_response = {'error': str(e), 'done': True}
        print(f"发生错误: {error_response}")
        yield f"{json.dumps(error_response)}"

# 处理文本请求的API端点
@app.post("/api/process")
async def generate_text(request: TextRequest):
    print('收到请求!')
    print(f'请求文本: \n{request}')
    
    # 根据请求参数选择处理函数
    useRAG = request.useRAG
    useMCP = request.useMCP
    if useRAG:
        func = generate_stream_RAG
    elif useMCP:
        func = generate_stream_mcp
    else:
        func = generate_stream
        
    # 返回流式响应
    return StreamingResponse(
        content=func(request),
        media_type="text/event-stream"
    )


# 文件类型检查辅助函数
ALLOWED_EXTENSIONS = {'txt'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 文件上传相关导入
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os, shutil


# 创建上传文件存储目录
UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 文件上传API端点
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    print('~ 上传文件: ', file.filename)
    
    # 校验文件扩展名
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in {"txt", "docx"}:
        raise HTTPException(status_code=400, detail="不支持的文件类型")
    
    # 构造本地存储路径
    save_path = os.path.join(UPLOAD_DIR, file.filename)
    
    try:
        # 保存上传的文件
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存文件失败：{e}")
    finally:
        await file.close()
    
    # 处理docx文件，转换为txt格式
    if 'docx' in file.filename:
        file_base_name = ''.join(file.filename.split('.')[:-1])+'.txt'
        print(file_base_name)
        file_path = os.path.join(UPLOAD_DIR, file_base_name)
        
        from read_docs import read_docx
        res = read_docx(save_path)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(res)
        os.remove(save_path)  # 删除原始docx文件
        save_path = file_path  # 更新路径为转换后的txt文件

    # 将文件内容添加到RAG知识库
    kb.add(save_path, spiltNum=128, chunk_overlap=16)
    # graph_rag.up(save_path, llm)
    
    # 返回上传成功信息
    return {"filename": file.filename, "size": os.path.getsize(save_path)}


# 获取知识库文件列表API
@app.get("/api/knowledge-base")
async def get_knowledge_base():
    """
    返回 UPLOAD_DIR 目录中所有 .txt 文件的名称与大小列表
    """
    print('~ 打印知识库列表')
    try:
        files = []
        for fn in os.listdir(UPLOAD_DIR):
            if fn.lower().endswith(".txt"):
                path = os.path.join(UPLOAD_DIR, fn)
                size_kb = os.path.getsize(path) / 1024
                files.append({
                    "name": fn,
                    "size": f"{size_kb:.2f} KB"
                })
        return {"files": files}
    except Exception as e:
        # 遇到异常时返回 500，并带上错误信息
        raise HTTPException(status_code=500, detail=f"读取知识库失败：{e}")

# 删除知识库文件API
@app.delete("/api/knowledge-base/{filename}", status_code=status.HTTP_200_OK)
async def delete_knowledge_file(filename: str):
    """
    删除指定知识库文件：
      - 如果文件存在，则删除并返回成功消息
      - 如果文件不存在，则抛出 404
      - 遇到其他异常，抛出 500
    """
    print('~ 删除文件: ', filename)
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # 校验文件是否存在
    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="文件不存在")
    try:
        os.remove(file_path)  # 删除文件
        kb.delete(file_path)  # 从RAG知识库中删除
        # graph_rag.clear(file_path)  # 从图数据库中清除
        # 如果有重新加载知识库的逻辑，可以在这里调用
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"删除文件失败：{e}")
    return {"message": "文件删除成功"}


# 应用启动和关闭处理
if __name__ == "__main__":
    import atexit
    # 注册应用退出时的回调函数，保存RAG知识库
    # atexit.register(lambda: kb.save('RAG/save.pkl'))
    
    import uvicorn
    print(generate_stream('你好'))  # 测试流式响应函数
    
    # 启动FastAPI应用
    uvicorn.run(app, host="0.0.0.0", port=8000) 