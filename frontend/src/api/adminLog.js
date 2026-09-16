import request from '@/utils/request'

// GET /api/admin/logs?fallback=&source=&from=&to=&kw=&page=&size=
export const getQaLogs = (params) => request.get('/admin/logs', { params })

// GET /api/admin/logs/export（与当前筛选一致，utf-8-sig CSV）→ Blob
export const exportQaLogs = (params) => request.get('/admin/logs/export', { params, responseType: 'blob' })
