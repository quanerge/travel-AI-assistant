// utils/markdown.js
// 轻量 Markdown 解析器：把 AI 回复的 markdown 文本拆成结构化 blocks，
// 供小程序 wx:for 渲染为标题/列表/引用/加粗等清晰样式。
// 纯 JS，不依赖任何小程序 API，可在 node 下直接测试。

// 行内解析：**加粗** 与 `行内代码`
function parseInline(text) {
  const parts = []
  const re = /(\*\*([^*]+)\*\*|`([^`]+)`)/g
  let last = 0
  let m
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push({ text: text.slice(last, m.index) })
    if (m[2] !== undefined) parts.push({ text: m[2], bold: true })
    else if (m[3] !== undefined) parts.push({ text: m[3], code: true })
    last = re.lastIndex
  }
  if (last < text.length) parts.push({ text: text.slice(last) })
  return parts.length ? parts : [{ text: text }]
}

function parseBlocks(md) {
  if (!md) return []
  const lines = String(md).replace(/\r\n/g, '\n').split('\n')
  const blocks = []
  let listType = null // 'ul' | 'ol'
  let listItems = []

  function flushList() {
    if (listType) {
      blocks.push({ type: listType, items: listItems })
      listType = null
      listItems = []
    }
  }

  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    const trimmed = line.trim()

    if (trimmed === '') { flushList(); i++; continue }

    // 标题 # / ## / ###
    const h = trimmed.match(/^(#{1,3})\s+(.*)$/)
    if (h) {
      flushList()
      blocks.push({ type: 'h' + h[1].length, text: h[2].trim() })
      i++; continue
    }

    // 引用 >
    if (/^>\s?/.test(trimmed)) {
      flushList()
      blocks.push({ type: 'quote', text: trimmed.replace(/^>\s?/, '') })
      i++; continue
    }

    // 分隔线 ---
    if (/^---+$/.test(trimmed)) {
      flushList()
      blocks.push({ type: 'hr' })
      i++; continue
    }

    // 无序列表 - 或 *
    const ul = trimmed.match(/^[-*]\s+(.*)$/)
    if (ul) {
      if (listType && listType !== 'ul') flushList()
      listType = 'ul'
      listItems.push(ul[1])
      i++; continue
    }

    // 有序列表 1.
    const ol = trimmed.match(/^\d+\.\s+(.*)$/)
    if (ol) {
      if (listType && listType !== 'ol') flushList()
      listType = 'ol'
      listItems.push(ol[1])
      i++; continue
    }

    // 普通段落：合并后续连续普通行（含换行也视为同段）
    flushList()
    const para = [trimmed]
    while (i + 1 < lines.length) {
      const nx = lines[i + 1].trim()
      if (
        nx === '' || /^#{1,3}\s/.test(nx) || /^>\s?/.test(nx) ||
        /^[-*]\s/.test(nx) || /^\d+\.\s/.test(nx) || /^---+$/.test(nx)
      ) break
      para.push(nx)
      i++
    }
    blocks.push({ type: 'p', parts: parseInline(para.join(' ')) })
    i++
  }
  flushList()
  return blocks
}

module.exports = { parseBlocks, parseInline }
