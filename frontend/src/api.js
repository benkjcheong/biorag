import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:5001/api'
})

export const searchAPI = async (query, topK = 10) => {
  const response = await api.post('/search', {
    query,
    top_k: topK
  })
  return response.data
}