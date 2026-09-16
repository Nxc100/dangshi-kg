import request from '@/utils/request'

// POST /api/auth/register {username, password, confirm_password} → {token, user}（注册后自动登录）
export const register = (data) => request.post('/auth/register', data)

// POST /api/auth/login {username, password} → {token, user:{user_id, username, role, nickname, avatar_url, must_change_pwd}}
export const login = (data) => request.post('/auth/login', data)

// GET /api/auth/check?username= → {available: boolean}
export const checkUsername = (username) => request.get('/auth/check', { params: { username } })
