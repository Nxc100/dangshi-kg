import request from '@/utils/request'

// GET /api/timeline?period= → {periods:[{name,order,start_year,end_year}], period, events:[...]}
// 无参时后端返回时期列表 + 第一个时期的事件（一次请求完成冷启动）
export const getTimeline = (period) => request.get('/timeline', { params: period ? { period } : {} })
