/**
 * 行业分析API
 */
import apiClient from './apiClient.js'

/**
 * 获取行业分析数据
 * @param {number} limit - 返回行业数量限制
 * @param {number} minJobs - 最小职位数量过滤
 * @returns {Promise<Object>} 行业分析数据
 */
export async function getIndustryAnalysis(limit = 10, minJobs = 0) {
  return await apiClient.get('/charts/industry', {
    params: { limit, min_jobs: minJobs }
  })
}

/**
 * 获取行业薪资分析
 * @returns {Promise<Object>} 行业薪资数据
 */
export async function getIndustrySalary() {
  return await apiClient.get('/charts/industry/salary')
}

/**
 * 获取行业详细信息
 * @param {string} industryName - 行业名称
 * @returns {Promise<Object>} 行业详细信息
 */
export async function getIndustryDetail(industryName) {
  return await apiClient.get(`/charts/industry/detail/${encodeURIComponent(industryName)}`)
}

/**
 * 获取职位综合排名柱状图数据
 * @returns {Promise<Object>} 职位排名数据
 */
export async function getJobRanking(topN = 5) {
  return await apiClient.get('/industry/ranking/jobs', {
    params: { top_n: topN }
  })
}

/**
 * 获取行业双环嵌套玫瑰图数据
 * @returns {Promise<Object>} 行业趋势数据
 */
export async function getIndustryTrendRose() {
  return await apiClient.get('/industry/trend/rose')
}

/**
 * 获取 Q5 引力图顶部新兴岗位（默认前5）
 * @param {number} topN - 返回岗位数量
 * @returns {Promise<Object>}
 */
export async function getQ5ForceEmergingJobs(topN = 5) {
  return await apiClient.get('/q5/force/emerging-jobs', {
    params: { top_n: topN }
  })
}

/**
 * 获取单岗位行业引力网络
 * @param {string} jobTitle - 岗位编码
 * @param {number} topKIndustry - 行业数量上限
 * @param {string} tier - 城市层级
 * @returns {Promise<Object>}
 */
export async function getQ5ForceJobNetwork(jobTitle, topKIndustry = 12, tier = 'all') {
  return await apiClient.get('/q5/force/job-network', {
    params: {
      job_title: jobTitle,
      top_k_industry: topKIndustry,
      tier
    }
  })
}

/**
 * 获取 Q5 枢纽岗位排名
 * @param {number} topN - 返回条数
 * @param {number} topKIndustry - 每岗位考虑行业数量
 * @returns {Promise<Object>}
 */
export async function getQ5ForceHubRanking(topN = 30, topKIndustry = 12) {
  return await apiClient.get('/q5/force/hub-ranking', {
    params: {
      top_n: topN,
      top_k_industry: topKIndustry
    }
  })
}

/**
 * 获取 Q5 对比岗位（非新兴）
 * @param {number} topN - 返回岗位数量
 * @param {number} emergingTopN - 排除的新兴TopN
 * @returns {Promise<Object>}
 */
export async function getQ5ForceContrastJobs(topN = 4, emergingTopN = 5) {
  return await apiClient.get('/q5/force/contrast-jobs', {
    params: {
      top_n: topN,
      emerging_top_n: emergingTopN
    }
  })
}
