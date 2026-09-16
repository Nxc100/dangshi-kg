import request from '@/utils/request'

// GET /api/graph/search?kw= → [{name, type}]（≤10 条，别名命中回链主名）
export const searchEntities = (kw) => request.get('/graph/search', { params: { kw } })

// GET /api/graph/subgraph?name=&hops=2&limit=100 → {nodes, links, truncated}
export const getSubgraph = (name, hops = 2, limit = 100) =>
  request.get('/graph/subgraph', { params: { name, hops, limit } })

// GET /api/graph/neighbors?name= → {nodes, links}（1 跳增量）
export const getNeighbors = (name) => request.get('/graph/neighbors', { params: { name } })
