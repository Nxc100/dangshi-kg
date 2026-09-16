import request from '@/utils/request'

// GET /api/stats/overview（admin）→ {top_questions, top_entities, intent_dist, trend_30d, fallback_rate, llm:{calls, success_rate, avg_latency_ms}}
export const getStatsOverview = () => request.get('/stats/overview')
