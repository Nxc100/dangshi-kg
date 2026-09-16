import request from '@/utils/request'

// ---- 资料 ----
export const getProfile = () => request.get('/user/profile')
export const updateProfile = (data) => request.put('/user/profile', data) // {nickname}

// POST /api/user/avatar（multipart）→ {avatar_url}（带时间戳参数破缓存）
export const uploadAvatar = (file) => {
  const form = new FormData()
  form.append('file', file)
  return request.post('/user/avatar', form, { headers: { 'Content-Type': 'multipart/form-data' } })
}

// PUT /api/user/password {old_password, new_password, confirm_password}
export const changePassword = (data) => request.put('/user/password', data)

// ---- 提问历史 ----
export const getHistory = (params) => request.get('/user/history', { params })
export const deleteHistory = (id) => request.delete(`/user/history/${id}`)
export const clearHistory = () => request.delete('/user/history')

// ---- 收藏夹 ----
export const getFavorites = (params) => request.get('/user/favorite', { params }) // {fav_type, page, size}
export const addFavorite = (data) => request.post('/user/favorite', data) // {fav_type, ref_id}
export const removeFavorite = (data) => request.delete('/user/favorite', { data }) // {fav_type, ref_id}
