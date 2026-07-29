// admin/src/utils/mask.js —— 敏感信息前端脱敏（展示最小化，符合个保法）
export function maskPhone(phone) {
  if (!phone) return ''
  const s = String(phone).trim()
  if (s.length < 7) return s
  return s.slice(0, 3) + '****' + s.slice(-4)
}
