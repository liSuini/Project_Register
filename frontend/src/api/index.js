import axios from 'axios'
import { ElMessage } from 'element-plus'

const http = axios.create({ baseURL: '/api' })
http.interceptors.response.use(
  (res) => res,
  (err) => {
    // 4xx 业务错误（如非空节点禁删409）统一弹提示
    ElMessage.error(err.response?.data?.message || err.message || '请求失败')
    return Promise.reject(err)
  }
)

export const wan = (v) => ((Number(v) || 0) / 10000).toFixed(2)      // 元 → 万元（显示）
export const toYuan = (w) => Math.round((Number(w) || 0) * 10000)    // 万元 → 元（提交）

export const projectsApi = {
  list: (params) => http.get('/projects', { params }),
  create: (data) => http.post('/projects', data),
  update: (id, data) => http.put(`/projects/${id}`, data),
  changeStage: (id, stage) => http.patch(`/projects/${id}/stage`, { stage }),
  ledger: (id) => http.get(`/projects/${id}/ledger`)
}

export const nodesApi = {
  add: (parentId, name) => http.post('/nodes', { parent_id: parentId, name }),
  rename: (id, name) => http.patch(`/nodes/${id}`, { name }),
  remove: (id) => http.delete(`/nodes/${id}`),
  attachments: (id) => http.get(`/nodes/${id}/attachments`),
  upload: (id, file) => {
    const fd = new FormData()
    fd.append('file', file)
    return http.post(`/nodes/${id}/attachments`, fd)
  },
  deleteAttachment: (id) => http.delete(`/attachments/${id}`),
  downloadUrl: (id) => `/api/attachments/${id}/download`
}

export const detailsApi = {
  purchases: (pid) => http.get(`/projects/${pid}/purchases`),
  addPurchase: (pid, data) => http.post(`/projects/${pid}/purchases`, data),
  delPurchase: (id) => http.delete(`/purchases/${id}`),
  acceptances: (pid) => http.get(`/projects/${pid}/acceptances`),
  addAcceptance: (pid, data) => http.post(`/projects/${pid}/acceptances`, data),
  delAcceptance: (id) => http.delete(`/acceptances/${id}`)
}

export const statsApi = { get: () => http.get('/stats') }
