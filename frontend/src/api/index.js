import axios from 'axios'

const request = axios.create({ baseURL: import.meta.env.VITE_API_BASE || '/api', timeout: 20000 })

request.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) config.headers['Authorization'] = `Bearer ${token}`
  return config
})

request.interceptors.response.use(
  res => res.data,
  err => {
    if (err.response && err.response.status === 401) {
      localStorage.clear()
      location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default request
