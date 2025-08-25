import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout for API calls
  validateStatus: function (status) {
    // Accept 2xx status codes as successful
    return status >= 200 && status < 300;
  },
});

// Separate instance for long-running processing requests
export const processingApi = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 300000, // 5 minute timeout for processing requests
  validateStatus: function (status) {
    return status >= 200 && status < 300;
  },
});

// Types for API responses
export interface HealthResponse {
  status: string;
  timestamp: string;
  version: string;
  services: {
    database: string;
    whisper: string;
  };
}

export interface PingResponse {
  message: string;
  timestamp: string;
}

export interface VideoProcessResponse {
  task_id?: string;
  video_id?: string;
  status: string;
  message: string;
  celery_task_id?: string;
}

export interface BatchProcessResponse {
  batch_id: string;
  tasks: Array<{
    task_id: string;
    url: string;
    celery_task_id: string;
  }>;
  message: string;
}

export interface TaskStatusResponse {
  task_id: string;
  status: string;
  progress: number;
  task_type: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
  result?: any;
  video?: {
    id: string;
    title: string;
    external_id: string;
    processing_status: string;
    platform: string;
  };
  celery?: {
    task_id: string;
    state: string;
    info: any;
  };
  current_step?: string;
}

export interface Task {
  id: string;
  task_type: string;
  status: string;
  progress: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  input_data: any;
  video_id?: string;
}

export interface TasksResponse {
  tasks: Task[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

export interface Video {
  id: string;
  title: string;
  external_id: string;
  url: string;
  duration: number;
  processing_status: string;
  created_at: string;
  processed_at?: string;
  channel: {
    id: string;
    name: string;
    platform: string;
  };
}

export interface VideosResponse {
  videos: Video[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

export interface Transcript {
  id: string;
  text: string;
  start_time: number;
  end_time: number;
  confidence: number;
  speaker?: string;
}

export interface TranscriptsResponse {
  video_id: string;
  video_title: string;
  transcripts: Transcript[];
}

export interface Channel {
  id: string;
  name: string;
  platform: string;
  external_id: string;
  url: string;
  video_count: number;
  created_at: string;
}

export interface ChannelsResponse {
  channels: Channel[];
}

export interface CancelTaskResponse {
  task_id: string;
  status: string;
  message: string;
}

// API functions
export const healthApi = {
  ping: (): Promise<PingResponse> =>
    api.get('/api/ping').then(res => res.data),
  
  health: (): Promise<HealthResponse> =>
    api.get('/api/health').then(res => res.data),
};

export const videoProcessingApi = {
  processVideo: (url: string, priority: 'low' | 'normal' | 'high' = 'normal'): Promise<VideoProcessResponse> =>
    processingApi.post('/api/process/video', { url, priority }).then(res => res.data),
  
  processDirect: (url: string): Promise<VideoProcessResponse> =>
    processingApi.post('/api/process/direct', { url }).then(res => res.data),
  
  processBatch: (urls: string[]): Promise<BatchProcessResponse> =>
    processingApi.post('/api/process/batch', { urls }).then(res => res.data),
};

export const tasksApi = {
  getTaskStatus: (taskId: string): Promise<TaskStatusResponse> =>
    api.get(`/api/tasks/${taskId}`).then(res => res.data),
  
  cancelTask: (taskId: string): Promise<CancelTaskResponse> =>
    api.post(`/api/tasks/${taskId}/cancel`).then(res => res.data),
  
  getTasks: (params?: {
    page?: number;
    per_page?: number;
    status?: string;
    task_type?: string;
  }): Promise<TasksResponse> =>
    api.get('/api/tasks', { params }).then(res => res.data),
};

export const dataApi = {
  getVideos: (params?: {
    page?: number;
    per_page?: number;
    status?: string;
  }): Promise<VideosResponse> =>
    api.get('/api/videos', { params }).then(res => res.data),
  
  getVideoTranscripts: (videoId: string): Promise<TranscriptsResponse> =>
    api.get(`/api/videos/${videoId}/transcripts`).then(res => res.data),
  
  getChannels: (): Promise<ChannelsResponse> =>
    api.get('/api/channels').then(res => res.data),
};

// Utility functions
export const formatDuration = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

export const formatTime = (timestamp: string): string => {
  return new Date(timestamp).toLocaleString();
};

export const getStatusColor = (status: string): string => {
  switch (status) {
    case 'completed':
      return 'text-green-600';
    case 'processing':
    case 'queued':
      return 'text-yellow-600';
    case 'failed':
    case 'cancelled':
      return 'text-red-600';
    default:
      return 'text-gray-600';
  }
};

export const getStatusBadgeVariant = (status: string): 'default' | 'secondary' | 'destructive' | 'outline' => {
  switch (status) {
    case 'completed':
      return 'default';
    case 'processing':
    case 'queued':
      return 'secondary';
    case 'failed':
    case 'cancelled':
      return 'destructive';
    default:
      return 'outline';
  }
};

// Phase 3: Content Intelligence API Types and Functions

// Network Analysis Types
export interface NetworkNode {
  id: string;
  name: string;
  canonical_name?: string;
  type: string;
  connections: number;
  total_mentions: number;
  videos: string[];
  video_titles: string[];
}

export interface NetworkEdge {
  source: string;
  target: string;
  weight: number;
  confidence: number;
}

export interface NetworkResponse {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  stats: {
    total_nodes: number;
    total_edges: number;
    min_cooccurrence_threshold: number;
  };
}

export interface EntityNeighbor {
  id: string;
  name: string;
  type: string;
  cooccurrence_count: number;
  confidence: number;
  shared_videos: string[];
}

export interface EntityNeighborsResponse {
  entity: {
    id: string;
    name: string;
    type: string;
  };
  neighbors: EntityNeighbor[];
}

export interface Entity {
  id: string;
  name: string;
  entity_type: string;
  canonical_name?: string;
  description?: string;
  confidence_score: number;
  mention_count: number;
  created_at: string;
}

export interface EntityMention {
  id: string;
  text: string;
  label: string;
  confidence: number;
  start: number;
  end: number;
  videoId?: string;
  timestamp?: number;
}

export interface EntitiesResponse {
  entities: Entity[];
  pagination?: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

export interface VideoEntitiesResponse {
  video_id: string;
  video_title: string;
  entities: EntityMention[];
}

export interface Topic {
  id: string;
  label: string;
  keywords: string[];
  coherence: number;
  documentCount: number;
  evolution?: { timestamp: number; strength: number }[];
  probability?: number;
}

export interface TopicsResponse {
  topics: Topic[];
}

export interface VideoTopicsResponse {
  video_id: string;
  video_title: string;
  topics: Topic[];
}

export interface SearchResult {
  id: string;
  title: string;
  similarity: number;
  snippet: string;
  timestamp?: number;
  channel?: string;
  videoId?: string;
  metadata?: { [key: string]: any };
}

export interface EmotionScore {
  emotion: string;
  score: number;
  timestamp?: number;
}

export interface EmotionTimeline {
  timestamp: number;
  emotions: EmotionScore[];
  dominantEmotion: string;
}

export interface VideoEmotionsResponse {
  video_id: string;
  video_title: string;
  emotions: EmotionScore[];
  timeline: EmotionTimeline[];
}

export interface Embedding {
  id: string;
  model_name: string;
  model_version: string;
  dimension: number;
  content_type: string;
  video_id: string;
  created_at: string;
}

export interface EmbeddingsResponse {
  embeddings: Embedding[];
}

// Phase 3 API Functions
export const intelligenceApi = {
  // Entity Recognition
  getEntities: (params?: {
    page?: number;
    per_page?: number;
    type?: string;
    min_confidence?: number;
    search?: string;
  }): Promise<EntitiesResponse> =>
    api.get('/api/entities', { params }).then(res => res.data),

  getVideoEntities: (videoId: string, params?: {
    min_confidence?: number;
    type?: string;
  }): Promise<VideoEntitiesResponse> =>
    api.get(`/api/videos/${videoId}/entities`, { params }).then(res => res.data),

  // Topic Modeling
  getTopics: (params?: {
    search?: string;
    min_coherence?: number;
  }): Promise<TopicsResponse> =>
    api.get('/api/topics', { params }).then(res => res.data),

  getVideoTopics: (videoId: string, params?: {
    min_probability?: number;
  }): Promise<VideoTopicsResponse> =>
    api.get(`/api/videos/${videoId}/topics`, { params }).then(res => res.data),

  // Vector Search
  semanticSearch: (query: string, options?: {
    threshold?: number;
    limit?: number;
    includeMetadata?: boolean;
  }): Promise<SearchResult[]> =>
    api.post('/api/search/semantic', {
      query,
      threshold: options?.threshold,
      limit: options?.limit
    }).then(res => res.data),

  getEmbeddings: (params?: {
    video_id?: string;
  }): Promise<EmbeddingsResponse> =>
    api.get('/api/embeddings', { params }).then(res => res.data),

  // Emotion Analysis
  getEmotions: (params?: {
    video_id?: string;
  }) =>
    api.get('/api/emotions', { params }).then(res => res.data),

  getVideoEmotions: (videoId: string): Promise<VideoEmotionsResponse> =>
    api.get(`/api/videos/${videoId}/emotions`).then(res => res.data),

  // Content Intelligence Processing
  processVideoIntelligence: (videoId: string): Promise<VideoProcessResponse> =>
    processingApi.post(`/api/videos/${videoId}/process-intelligence`).then(res => res.data),

  // Network Analysis
  getEntityNetwork: (params?: {
    min_cooccurrence?: number;
    types?: string[];
  }): Promise<NetworkResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.min_cooccurrence) searchParams.append('min_cooccurrence', params.min_cooccurrence.toString());
    if (params?.types?.length) searchParams.append('types', params.types.join(','));
    return api.get(`/api/network/entities?${searchParams.toString()}`).then(res => res.data);
  },

  getEntityNeighbors: (entityId: string): Promise<EntityNeighborsResponse> =>
    api.get(`/api/network/entities/${entityId}/neighbors`).then(res => res.data),
};