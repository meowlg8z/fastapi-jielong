import { createApp } from 'vue'
import App from './App.vue'

console.log('API地址:', import.meta.env.VITE_API_BASE_URL)
const baseURL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api'

// 封装 fetch
const request = async (url, options = {}) => {
  // 改成 let，允许后续拼接参数
  let fullUrl = url.startsWith('http') ? url : `${baseURL}${url}`

  const defaultHeaders = {
    'Content-Type': 'application/json',
    ...options.headers
  }

  const fetchOptions = {
    method: options.method || 'GET',
    headers: defaultHeaders,
    ...options
  }

  // GET 参数拼接
  if (fetchOptions.method.toUpperCase() === 'GET' && options.params) {
    const params = new URLSearchParams(options.params)
    fullUrl += `?${params.toString()}`
  } 
  // POST/PUT 处理请求体
  else if (options.data) {
    fetchOptions.body = JSON.stringify(options.data)
  }

  try {
    const response = await fetch(fullUrl, fetchOptions)
    if (!response.ok) {
      throw new Error(`请求失败: ${response.status} ${response.statusText}`)
    }
    const data = await response.json()
    return { data, status: response.status, response }
  } catch (error) {
    console.error('请求出错:', error)
    throw error
  }
}

const app = createApp(App)
app.config.globalProperties.$api = {
  get: (url, params) => request(url, { method: 'GET', params }),
  post: (url, data) => request(url, { method: 'POST', data }),
  put: (url, data) => request(url, { method: 'PUT', data }),
  delete: (url, params) => request(url, { method: 'DELETE', params })
}

app.mount('#app')