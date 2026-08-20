// 统一图表配色（品牌中性色，集中管理便于一键换肤）
export const CHART = {
  primary: '#409eff',
  success: '#67c23a',
  warning: '#e6a23c',
  danger: '#f56c6c',
  info: '#909399',
  // 分类序列色（饼图 / 堆叠 / 多系列，按此顺序取色）
  series: ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#9254de', '#13c2c2', '#909399'],
  // 年龄四档语义色（蓝→绿→橙→红）
  ageBands: ['#409eff', '#67c23a', '#e6a23c', '#f56c6c'],
  // 地图顺序渐变（浅→深蓝，与 primary 同色系）
  map: ['#e6f4ff', '#91caff', '#409eff', '#0958d9'],
  // 预警三色
  alert: { red: '#f56c6c', orange: '#e6a23c', yellow: '#f7ba2a' }
}
