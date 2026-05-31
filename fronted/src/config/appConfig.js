/**
 * 应用全局配置
 */
export const appConfig = {
  // API配置
  api: {
    // 优先使用环境变量；默认根据访问主机自动选择
    // - 本机访问(localhost/127): 直连后端
    // - 非本机访问(如局域网IP): 走 /api 代理，避免 127.0.0.1 指向客户端自身
    baseURL: import.meta.env.VITE_API_BASE_URL || (
      ['localhost', '127.0.0.1'].includes(window.location.hostname)
        ? 'http://127.0.0.1:5001/api'
        : '/api'
    ),
    timeout: 50000  // 增加超时时间，因为读取Excel和Q1散点图可能需要较长时间
  },
  
  // 主题配置
  theme: {
    primaryColor: '#1b8cff',
    secondaryColor: '#00d7ff',
    backgroundColor: 'linear-gradient(135deg, #070d1f 0%, #071425 100%)'
  },
  
  // 图表配置
  chart: {
    defaultHeight: 600,
    defaultWidth: '100%',
    animationDuration: 750
  },
  
  // 分页配置
  pagination: {
    defaultPageSize: 10,
    pageSizeOptions: [10, 20, 50, 100]
  }
}
