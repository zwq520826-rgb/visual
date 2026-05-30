import apiClient from './apiClient';

export function getRegionsSummary({ nClusters = 4, algorithm = 'kmeans', sampleSize = 0 } = {}) {
  return apiClient.get('/regions/summary', {
    params: {
      n_clusters: nClusters,
      algorithm,
      sample_size: sampleSize,
    },
  });
}

export function getRegionDetail(regionId, { nClusters = 4, algorithm = 'kmeans', sampleSize = 0 } = {}) {
  return apiClient.get(`/regions/${encodeURIComponent(regionId)}`, {
    params: {
      n_clusters: nClusters,
      algorithm,
      sample_size: sampleSize,
    },
  });
}

export function getRegionClusterSummary({ nClusters = 4, algorithm = 'kmeans', sampleSize = 0 } = {}) {
  return apiClient.get('/regions/cluster_summary', {
    params: {
      n_clusters: nClusters,
      algorithm,
      sample_size: sampleSize,
    },
  });
}

export function getIndustryRegionMatrix({ topM = 20, topN = 15, tier = 'all' } = {}) {
  return apiClient.get('/industry_region_matrix', {
    params: {
      top_m: topM,
      top_n: topN,
      tier,
    },
  });
}

export function getPositionIndustryCooccurrence({ regionId = null, topJobs = 8, topIndustries = 8 } = {}) {
  const params = {
    top_jobs: topJobs,
    top_industries: topIndustries,
  };
  if (regionId) params.region_id = regionId;
  return apiClient.get('/regions/position_industry_cooccurrence', { params });
}

export function getQ4DataQuality({ nClusters = 4, algorithm = 'kmeans', sampleSize = 0 } = {}) {
  return apiClient.get('/data_quality', {
    params: {
      n_clusters: nClusters,
      algorithm,
      sample_size: sampleSize,
    },
  });
}
