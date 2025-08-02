import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000'

export const processTextAPI = async (messages, onData, useRAG = false, useMCP = false) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/process`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        messages,
        useRAG,
        useMCP
      }),
    })

    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const chunk = decoder.decode(value)
      onData(chunk)
    }
  } catch (error) {
    console.error('API调用失败:', error)
    throw error
  }
}


import { useToast } from 'vue-toast-notification';

const toast = useToast();

export const uploadFileAPI = async (formData) => {
  const upInfo = toast.info('文件上传中...', { duration: 0 });

  try {
    const response = await axios.post(`${API_BASE_URL}/api/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    upInfo.dismiss()
    toast.success('文件上传完成!', { duration: 1500 });
    return response.data;
  } catch (error) {
    console.log('upError: ', error)
    upInfo.dismiss()
    toast.error('文件上传失败', { duration: 1500 });
    throw error;
  }
};

export const getKnowledgeBaseAPI = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/knowledge-base`)
    return response.data
  } catch (error) {
    console.error('获取知识库失败:', error)
    toast.error('获取知识库失败', { duration: 1500 });
    throw error
  }
}

export const deleteKnowledgeFileAPI = async (filename) => {
  const delInfo = toast.info('文件删除中...', { duration: 0 });
  try {
    const response = await axios.delete(`${API_BASE_URL}/api/knowledge-base/${filename}`)
    // return response.data
    delInfo.dismiss()
    toast.success('文件删除完成!', { duration: 1500 });
  } catch (error) {
    console.error('删除文件失败:', error)
    delInfo.dismiss()
    toast.error('删除文件失败', { duration: 1500 });
    throw error
  }
}