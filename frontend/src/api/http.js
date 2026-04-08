export async function request(url, options = {}) {
  // 统一 HTTP 请求入口：处理 JSON 解析与错误抛出。
  const resp = await fetch(url, options)
  const data = await resp.json()
  if (!resp.ok) {
    throw new Error(data?.msg || `HTTP ${resp.status}`)
  }
  return data
}
