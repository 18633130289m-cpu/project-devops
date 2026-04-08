export async function request(url, options = {}) {
  const resp = await fetch(url, options)
  const data = await resp.json()
  if (!resp.ok) {
    throw new Error(data?.msg || `HTTP ${resp.status}`)
  }
  return data
}
