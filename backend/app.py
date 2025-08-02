from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
from werkzeug.utils import secure_filename
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
CORS(app)

# 配置知识库目录
UPLOAD_FOLDER = 'knowledge_base'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制上传文件大小为16MB

ALLOWED_EXTENSIONS = {'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 加载句子嵌入模型
try:
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    print("模型加载成功")
except Exception as e:
    print(f"模型加载失败: {e}")
    model = None

# 存储知识库的向量和文本
knowledge_vectors = []
knowledge_texts = []

def load_knowledge_base():
    global knowledge_vectors, knowledge_texts
    knowledge_vectors = []
    knowledge_texts = []
    
    if not model:
        print("模型未加载，无法处理知识库")
        return
    
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        if filename.endswith('.txt'):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                    # 将文本分割成句子
                    sentences = text.split('\n')
                    for sentence in sentences:
                        if sentence.strip():
                            # 生成句子向量
                            vector = model.encode(sentence)
                            knowledge_vectors.append(vector)
                            knowledge_texts.append(sentence)
            except Exception as e:
                print(f"处理文件 {filename} 时出错: {e}")

def search_knowledge(query, top_k=3):
    if not knowledge_vectors or not model:
        return []
    
    try:
        # 生成查询向量
        query_vector = model.encode(query)
        
        # 计算相似度
        similarities = cosine_similarity([query_vector], knowledge_vectors)[0]
        
        # 获取最相似的top_k个结果
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            results.append({
                'text': knowledge_texts[idx],
                'similarity': float(similarities[idx])
            })
        
        return results
    except Exception as e:
        print(f"搜索知识库时出错: {e}")
        return []

# 在应用启动时加载知识库
load_knowledge_base()

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': '没有文件被上传'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            # 重新加载知识库
            load_knowledge_base()
            return jsonify({
                'message': '文件上传成功',
                'filename': filename,
                'size': os.path.getsize(file_path)
            })
        except Exception as e:
            return jsonify({'error': f'文件上传失败: {str(e)}'}), 500
    
    return jsonify({'error': '不支持的文件类型'}), 400

@app.route('/api/knowledge-base', methods=['GET'])
def get_knowledge_base():
    try:
        files = []
        for filename in os.listdir(app.config['UPLOAD_FOLDER']):
            if filename.endswith('.txt'):
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                size = os.path.getsize(file_path)
                files.append({
                    'name': filename,
                    'size': f"{size / 1024:.2f} KB"
                })
        return jsonify({'files': files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/knowledge-base/<filename>', methods=['DELETE'])
def delete_knowledge_file(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            # 重新加载知识库
            load_knowledge_base()
            return jsonify({'message': '文件删除成功'})
        return jsonify({'error': '文件不存在'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/process', methods=['POST'])
def process_text():
    try:
        data = request.get_json()
        messages = data.get('messages', [])
        use_rag = data.get('useRAG', False)
        use_search = data.get('useSearch', False)
        
        # 获取最后一条用户消息
        last_user_message = None
        for msg in reversed(messages):
            if msg.get('type') == 'user':
                last_user_message = msg.get('text')
                break
        
        if use_rag and last_user_message and model:
            # 从知识库中检索相关内容
            relevant_knowledge = search_knowledge(last_user_message)
            # 构建提示词
            context = "\n".join([f"知识片段 {i+1}: {item['text']}" for i, item in enumerate(relevant_knowledge)])
            prompt = f"""基于以下知识库内容回答问题：

{context}

问题：{last_user_message}

请根据上述知识库内容回答用户的问题。如果知识库中没有相关信息，请说明无法回答。"""
        else:
            prompt = last_user_message
        
        def generate_response():
            # 这里应该调用实际的LLM模型
            # 现在只是模拟响应
            if use_rag:
                response = "这是基于知识库的响应..."
            else:
                response = "这是普通对话响应..."
            
            for char in response:
                yield json.dumps({'data': char, 'done': False}) + '\n'
            yield json.dumps({'data': '', 'done': True}) + '\n'
        
        return app.response_class(generate_response(), mimetype='text/plain')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=8000) 