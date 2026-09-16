import request from '@/utils/request'

// GET /api/daily → {recommend:{name,type,intro}|null, today_events:[{name,type,time_text,brief}]}
export const getDaily = () => request.get('/daily')
