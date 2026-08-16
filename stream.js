/**
 * SSE-style streaming over fetch (POST + ReadableStream).
 * The backend emits `data: {json}\n\n` events; this helper decodes them and
 * dispatches typed callbacks.
 */

export async function streamChat(url, body, { onDelta, onDone, onError, onNotice, signal } = {}) {
  const resp = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${localStorage.getItem('olmwed_token') || ''}`,
    },
    body: JSON.stringify(body),
    signal,
  })

  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`
    try {
      const err = await resp.json()
      detail = err.detail || detail
    } catch {
      /* keep default */
    }
    throw new Error(detail)
  }

  if (!resp.body) {
    throw new Error('浏览器不支持流式响应')
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let sep
    while ((sep = buffer.indexOf('\n\n')) >= 0) {
      const raw = buffer.slice(0, sep).trim()
      buffer = buffer.slice(sep + 2)
      if (!raw.startsWith('data: ')) continue
      let obj
      try {
        obj = JSON.parse(raw.slice(6))
      } catch {
        continue
      }
      if (obj.type === 'delta') onDelta?.(obj.content)
      else if (obj.type === 'done') onDone?.(obj)
      else if (obj.type === 'error') onError?.(new Error(obj.message || '未知错误'))
      else if (obj.type === 'notice') onNotice?.(obj.message)
    }
  }
}
