import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { dataApi, type Video, type Transcript, formatDuration, formatTime, getStatusBadgeVariant } from '@/lib/api';
import { 
  Video as VideoIcon, 
  Clock, 
  Search, 
  Filter, 
  Play, 
  ExternalLink,
  RefreshCw,
  FileText,
  Download,
  Eye
} from 'lucide-react';

export default function VideoLibrary() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [selectedVideo, setSelectedVideo] = useState<Video | null>(null);
  const [transcripts, setTranscripts] = useState<Transcript[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingTranscripts, setLoadingTranscripts] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [pagination, setPagination] = useState({
    page: 1,
    per_page: 20,
    total: 0,
    pages: 0,
    has_next: false,
    has_prev: false
  });

  const loadVideos = async (page = 1, status?: string) => {
    setLoading(true);
    try {
      const params: any = { page, per_page: 20 };
      if (status && status !== 'all') {
        params.status = status;
      }
      
      const response = await dataApi.getVideos(params);
      setVideos(response.videos);
      setPagination(response.pagination);
    } catch (error) {
      console.error('Failed to load videos:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadTranscripts = async (videoId: string) => {
    setLoadingTranscripts(true);
    try {
      const response = await dataApi.getVideoTranscripts(videoId);
      setTranscripts(response.transcripts);
    } catch (error) {
      console.error('Failed to load transcripts:', error);
      setTranscripts([]);
    } finally {
      setLoadingTranscripts(false);
    }
  };

  const selectVideo = (video: Video) => {
    setSelectedVideo(video);
    if (video.processing_status === 'completed') {
      loadTranscripts(video.id);
    } else {
      setTranscripts([]);
    }
  };

  useEffect(() => {
    loadVideos();
  }, []);

  useEffect(() => {
    loadVideos(1, statusFilter === 'all' ? undefined : statusFilter);
  }, [statusFilter]);

  const filteredVideos = videos.filter(video =>
    video.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    video.channel.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const exportTranscripts = () => {
    if (!selectedVideo || transcripts.length === 0) return;
    
    const transcriptText = transcripts
      .map(t => `[${formatTime(t.start_time.toString())}] ${t.text}`)
      .join('\n');
    
    const blob = new Blob([transcriptText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedVideo.title}_transcript.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const formatTime = (seconds: number | string): string => {
    const secs = typeof seconds === 'string' ? parseFloat(seconds) : seconds;
    const mins = Math.floor(secs / 60);
    const remainingSecs = Math.floor(secs % 60);
    return `${mins}:${remainingSecs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Video Library</h2>
          <p className="text-muted-foreground">
            Browse processed videos and view their transcripts
          </p>
        </div>
        <Button 
          onClick={() => loadVideos(pagination.page, statusFilter === 'all' ? undefined : statusFilter)} 
          variant="outline"
          size="sm"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      <div className="flex gap-4 items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search videos or channels..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
        
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]">
            <Filter className="h-4 w-4 mr-2" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
            <SelectItem value="processing">Processing</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Video List */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Videos ({pagination.total})</CardTitle>
              <CardDescription>
                {filteredVideos.length !== videos.length && 
                  `Showing ${filteredVideos.length} of ${videos.length} videos`
                }
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="h-6 w-6 animate-spin" />
                </div>
              ) : filteredVideos.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  {searchTerm ? 'No videos match your search' : 'No videos found'}
                </div>
              ) : (
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {filteredVideos.map((video) => (
                    <div
                      key={video.id}
                      className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                        selectedVideo?.id === video.id 
                          ? 'border-primary bg-primary/5' 
                          : 'hover:bg-muted/50'
                      }`}
                      onClick={() => selectVideo(video)}
                    >
                      <div className="flex items-start gap-3">
                        <VideoIcon className="h-5 w-5 mt-1 text-muted-foreground" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <Badge variant={getStatusBadgeVariant(video.processing_status)}>
                              {video.processing_status}
                            </Badge>
                            <Badge variant="outline">
                              {video.channel.platform}
                            </Badge>
                          </div>
                          
                          <h4 className="font-medium leading-tight mb-1 line-clamp-2">
                            {video.title}
                          </h4>
                          
                          <div className="flex items-center gap-4 text-sm text-muted-foreground">
                            <span className="flex items-center gap-1">
                              <VideoIcon className="h-3 w-3" />
                              {video.channel.name}
                            </span>
                            {video.duration && (
                              <span className="flex items-center gap-1">
                                <Clock className="h-3 w-3" />
                                {formatDuration(video.duration)}
                              </span>
                            )}
                          </div>
                          
                          <div className="text-xs text-muted-foreground mt-1">
                            {video.processed_at 
                              ? `Processed: ${formatTime(video.processed_at)}`
                              : `Created: ${formatTime(video.created_at)}`
                            }
                          </div>
                        </div>
                        
                        <div className="flex flex-col gap-1">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={(e) => {
                              e.stopPropagation();
                              window.open(video.url, '_blank');
                            }}
                          >
                            <ExternalLink className="h-3 w-3" />
                          </Button>
                          {video.processing_status === 'completed' && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={(e) => {
                                e.stopPropagation();
                                selectVideo(video);
                              }}
                            >
                              <Eye className="h-3 w-3" />
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              
              {/* Pagination */}
              {pagination.pages > 1 && (
                <div className="flex items-center justify-between mt-4">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={!pagination.has_prev}
                    onClick={() => loadVideos(pagination.page - 1, statusFilter === 'all' ? undefined : statusFilter)}
                  >
                    Previous
                  </Button>
                  
                  <span className="text-sm text-muted-foreground">
                    Page {pagination.page} of {pagination.pages}
                  </span>
                  
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={!pagination.has_next}
                    onClick={() => loadVideos(pagination.page + 1, statusFilter === 'all' ? undefined : statusFilter)}
                  >
                    Next
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Transcript Viewer */}
        <div>
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Transcript Viewer</CardTitle>
                  <CardDescription>
                    {selectedVideo ? selectedVideo.title : 'Select a video to view transcripts'}
                  </CardDescription>
                </div>
                {selectedVideo && transcripts.length > 0 && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={exportTranscripts}
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Export
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {!selectedVideo ? (
                <div className="text-center py-8 text-muted-foreground">
                  <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>Select a video from the list to view its transcript</p>
                </div>
              ) : selectedVideo.processing_status !== 'completed' ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Badge variant={getStatusBadgeVariant(selectedVideo.processing_status)} className="mb-4">
                    {selectedVideo.processing_status}
                  </Badge>
                  <p>Video is still processing. Transcript will be available once processing is complete.</p>
                </div>
              ) : loadingTranscripts ? (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="h-6 w-6 animate-spin" />
                </div>
              ) : transcripts.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No transcript available for this video</p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="flex items-center justify-between text-sm text-muted-foreground">
                    <span>{transcripts.length} transcript segments</span>
                    <span>Total duration: {formatDuration(transcripts[transcripts.length - 1]?.end_time || 0)}</span>
                  </div>
                  
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {transcripts.map((transcript) => (
                      <div
                        key={transcript.id}
                        className="p-3 border rounded-lg hover:bg-muted/50"
                      >
                        <div className="flex items-start gap-3">
                          <div className="flex items-center gap-1 text-xs text-muted-foreground min-w-0 shrink-0">
                            <Clock className="h-3 w-3" />
                            <span>{formatTime(transcript.start_time)}</span>
                          </div>
                          
                          <div className="flex-1 min-w-0">
                            <p className="text-sm leading-relaxed">
                              {transcript.text}
                            </p>
                            
                            {transcript.confidence && (
                              <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                                <span>Confidence: {(transcript.confidence * 100).toFixed(1)}%</span>
                                {transcript.speaker && (
                                  <span>Speaker: {transcript.speaker}</span>
                                )}
                              </div>
                            )}
                          </div>
                          
                          <div className="text-xs text-muted-foreground shrink-0">
                            {formatTime(transcript.end_time)}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Video Details */}
      {selectedVideo && (
        <Card>
          <CardHeader>
            <CardTitle>Video Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <h4 className="font-medium mb-2">Basic Information</h4>
                <div className="space-y-1 text-sm text-muted-foreground">
                  <div>ID: {selectedVideo.id}</div>
                  <div>External ID: {selectedVideo.external_id}</div>
                  <div>Platform: {selectedVideo.channel.platform}</div>
                  <div>Channel: {selectedVideo.channel.name}</div>
                </div>
              </div>
              
              <div>
                <h4 className="font-medium mb-2">Processing Status</h4>
                <div className="space-y-1 text-sm text-muted-foreground">
                  <div className="flex items-center gap-2">
                    Status: 
                    <Badge variant={getStatusBadgeVariant(selectedVideo.processing_status)}>
                      {selectedVideo.processing_status}
                    </Badge>
                  </div>
                  {selectedVideo.duration && (
                    <div>Duration: {formatDuration(selectedVideo.duration)}</div>
                  )}
                  {transcripts.length > 0 && (
                    <div>Transcript segments: {transcripts.length}</div>
                  )}
                </div>
              </div>
              
              <div>
                <h4 className="font-medium mb-2">Timeline</h4>
                <div className="space-y-1 text-sm text-muted-foreground">
                  <div>Created: {formatTime(selectedVideo.created_at)}</div>
                  {selectedVideo.processed_at && (
                    <div>Processed: {formatTime(selectedVideo.processed_at)}</div>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}