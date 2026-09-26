/** 运营概览相关请求：看板卡片与各模块统计卡片共用同一份数据，保证数字对得上。 */
import { fetchJson } from '@/api/client'

export type ModuleSummary = {
  name: string
  created: number
  pending: number
  abnormal: number
}

export type Overview = {
  cards: { label: string; value: number }[]
  modules: ModuleSummary[]
}

export function fetchOverview(): Promise<Overview> {
  return fetchJson<Overview>('/api/overview')
}

/** 取某个业务模块（按接口路径，如 /api/berth）的汇总数字；接口不可用时返回 null。 */
export async function fetchModuleStats(endpoint: string): Promise<ModuleSummary | null> {
  const module = endpoint.split('/').filter(Boolean).pop() ?? ''
  try {
    const overview = await fetchOverview()
    return overview.modules.find((item) => item.name === module) ?? null
  } catch {
    return null
  }
}
