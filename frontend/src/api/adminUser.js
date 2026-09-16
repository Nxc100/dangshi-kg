import request from '@/utils/request'

// GET /api/admin/users?kw=&page=&size=
export const listUsers = (params) => request.get('/admin/users', { params })

// POST /api/admin/users/<id>/status {status: 0|1}（传目标状态而非切换）
export const setUserStatus = (id, status) => request.post(`/admin/users/${id}/status`, { status })

// POST /api/admin/users/<id>/reset-password → {password}（随机密码只返回一次）
export const resetUserPassword = (id) => request.post(`/admin/users/${id}/reset-password`)

// POST /api/admin/users/<id>/role {role: 'user'|'admin'}
export const setUserRole = (id, role) => request.post(`/admin/users/${id}/role`, { role })
