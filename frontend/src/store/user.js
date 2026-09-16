import { defineStore } from 'pinia'

// 登录态（token / user_id / role / nickname / avatar / must_change_pwd），localStorage 持久化
const STORAGE_KEY = 'dangshi_user'

const EMPTY = {
  token: '',
  user_id: null,
  username: '',
  role: '',
  nickname: '',
  avatar_url: '',
  must_change_pwd: 0,
}

function load() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? { ...EMPTY, ...JSON.parse(raw) } : { ...EMPTY }
  } catch {
    return { ...EMPTY }
  }
}

function save(state) {
  try {
    const data = {}
    Object.keys(EMPTY).forEach((k) => (data[k] = state[k]))
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  } catch {
    // localStorage 不可用时仅保留内存状态
  }
}

export const useUserStore = defineStore('user', {
  state: () => load(),
  getters: {
    isLogin: (state) => !!state.token,
    isAdmin: (state) => state.role === 'admin',
  },
  actions: {
    // 登录 / 注册成功：{token, user:{user_id, username, role, nickname, avatar_url, must_change_pwd}}
    login({ token, user }) {
      this.token = token || ''
      this.setUser(user || {})
    },
    // 资料更新后以接口返回值为准（不以 token 载荷为准）
    setUser(user = {}) {
      Object.keys(EMPTY).forEach((k) => {
        if (k !== 'token' && user[k] !== undefined) this[k] = user[k]
      })
      save(this.$state)
    },
    logout() {
      Object.assign(this, { ...EMPTY })
      try {
        localStorage.removeItem(STORAGE_KEY)
      } catch {
        // ignore
      }
    },
  },
})
