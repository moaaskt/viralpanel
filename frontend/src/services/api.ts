import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
});

export interface HealthResponse {
  status: string;
  database: string;
  redis: string;
  timestamp: string;
}

export interface StatsResponse {
  total_runs: number;
  total_videos: number;
  total_scripts: number;
  total_publications: number;
  successful_runs: number;
  failed_runs: number;
  publications_by_platform: Record<string, number>;
}

export interface PipelineRun {
  id: string;
  started_at: string;
  stage: string;
  status: string;
  error_message?: string;
  duration_seconds?: number;
  run_metadata?: Record<string, any>;
}

export interface SourceVideo {
  id: string;
  platform: string;
  url: string;
  author?: string;
  metrics?: Record<string, any>;
  score?: number;
  collected_at: string;
  status: string;
}

export interface Script {
  id: string;
  source_video_id: string;
  transcription?: string;
  script_text?: string;
  hook?: string;
  version: number;
  created_at: string;
}

export interface Publication {
  id: string;
  asset_id: string;
  platform: string;
  scheduled_for?: string;
  published_at?: string;
  url?: string;
  status: string;
}

export interface TriggerResponse {
  task_id: string;
  message: string;
}

export const fetchHealth = async (): Promise<HealthResponse> => {
  const { data } = await api.get<HealthResponse>('/health');
  return data;
};

export const fetchStats = async (): Promise<StatsResponse> => {
  const { data } = await api.get<StatsResponse>('/stats');
  return data;
};

export const fetchRuns = async (): Promise<PipelineRun[]> => {
  const { data } = await api.get<PipelineRun[]>('/runs?limit=15');
  return data;
};

export const fetchVideos = async (): Promise<SourceVideo[]> => {
  const { data } = await api.get<SourceVideo[]>('/videos?limit=30');
  return data;
};

export const fetchScripts = async (videoId?: string): Promise<Script[]> => {
  const url = videoId ? `/scripts?source_video_id=${videoId}` : '/scripts';
  const { data } = await api.get<Script[]>(url);
  return data;
};

export const fetchPublications = async (): Promise<Publication[]> => {
  const { data } = await api.get<Publication[]>('/publications?limit=30');
  return data;
};

export const triggerPipeline = async (): Promise<TriggerResponse> => {
  const { data } = await api.post<TriggerResponse>('/runs/trigger');
  return data;
};

export default api;
