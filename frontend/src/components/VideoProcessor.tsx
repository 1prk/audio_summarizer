import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { videoProcessingApi, type VideoProcessResponse } from '@/lib/api';
import { Video, Upload, Loader2, CheckCircle, AlertCircle, Zap, Clock, Layers } from 'lucide-react';

export default function VideoProcessor() {
  const [singleUrl, setSingleUrl] = useState('');
  const [batchUrls, setBatchUrls] = useState('');
  const [priority, setPriority] = useState<'low' | 'normal' | 'high'>('normal');
  const [processing, setProcessing] = useState(false);
  const [processingDirect, setProcessingDirect] = useState(false);
  const [results, setResults] = useState<Array<{
    type: 'single' | 'batch' | 'direct';
    success: boolean;
    data?: any;
    error?: string;
    timestamp: Date;
  }>>([]);

  const handleSingleVideo = async () => {
    if (!singleUrl.trim()) return;
    
    setProcessing(true);
    try {
      const result = await videoProcessingApi.processVideo(singleUrl.trim(), priority);
      setResults(prev => [{
        type: 'single',
        success: true,
        data: result,
        timestamp: new Date()
      }, ...prev]);
      setSingleUrl('');
    } catch (error) {
      setResults(prev => [{
        type: 'single',
        success: false,
        error: error instanceof Error ? error.message : 'Processing failed',
        timestamp: new Date()
      }, ...prev]);
    } finally {
      setProcessing(false);
    }
  };

  const handleDirectProcessing = async () => {
    if (!singleUrl.trim()) return;
    
    setProcessingDirect(true);
    try {
      const result = await videoProcessingApi.processDirect(singleUrl.trim());
      setResults(prev => [{
        type: 'direct',
        success: true,
        data: result,
        timestamp: new Date()
      }, ...prev]);
      setSingleUrl('');
    } catch (error) {
      setResults(prev => [{
        type: 'direct',
        success: false,
        error: error instanceof Error ? error.message : 'Direct processing failed',
        timestamp: new Date()
      }, ...prev]);
    } finally {
      setProcessingDirect(false);
    }
  };

  const handleBatchProcessing = async () => {
    const urls = batchUrls.split('\n').map(url => url.trim()).filter(Boolean);
    if (urls.length === 0) return;
    
    setProcessing(true);
    try {
      const result = await videoProcessingApi.processBatch(urls);
      setResults(prev => [{
        type: 'batch',
        success: true,
        data: result,
        timestamp: new Date()
      }, ...prev]);
      setBatchUrls('');
    } catch (error) {
      setResults(prev => [{
        type: 'batch',
        success: false,
        error: error instanceof Error ? error.message : 'Batch processing failed',
        timestamp: new Date()
      }, ...prev]);
    } finally {
      setProcessing(false);
    }
  };

  const getPriorityIcon = (priority: string) => {
    switch (priority) {
      case 'high': return <Zap className="h-4 w-4" />;
      case 'low': return <Clock className="h-4 w-4" />;
      default: return <Layers className="h-4 w-4" />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'text-red-600';
      case 'low': return 'text-blue-600';
      default: return 'text-yellow-600';
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Video Processing</h2>
        <p className="text-muted-foreground">
          Submit videos for transcription and analysis. Supports YouTube, podcasts, and Twitch.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Single Video Processing */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Video className="h-5 w-5" />
              Single Video
            </CardTitle>
            <CardDescription>
              Process a single video with priority control and real-time progress tracking.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Video URL</label>
              <Input
                placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                value={singleUrl}
                onChange={(e) => setSingleUrl(e.target.value)}
              />
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-medium">Priority Level</label>
              <Select value={priority} onValueChange={(value: 'low' | 'normal' | 'high') => setPriority(value)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">
                    <div className="flex items-center gap-2">
                      <Clock className="h-4 w-4 text-blue-600" />
                      Low Priority
                    </div>
                  </SelectItem>
                  <SelectItem value="normal">
                    <div className="flex items-center gap-2">
                      <Layers className="h-4 w-4 text-yellow-600" />
                      Normal Priority
                    </div>
                  </SelectItem>
                  <SelectItem value="high">
                    <div className="flex items-center gap-2">
                      <Zap className="h-4 w-4 text-red-600" />
                      High Priority
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex gap-2">
              <Button
                onClick={handleSingleVideo}
                disabled={!singleUrl.trim() || processing || processingDirect}
                className="flex-1"
              >
                {processing ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Upload className="h-4 w-4 mr-2" />
                )}
                Queue Processing
              </Button>
              
              <Button
                onClick={handleDirectProcessing}
                disabled={!singleUrl.trim() || processing || processingDirect}
                variant="outline"
                className="flex-1"
              >
                {processingDirect ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Zap className="h-4 w-4 mr-2" />
                )}
                Direct Process
              </Button>
            </div>

            <div className="text-xs text-muted-foreground">
              Queue processing uses Celery for background tasks. Direct processing bypasses the queue for immediate results.
            </div>
          </CardContent>
        </Card>

        {/* Batch Processing */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Layers className="h-5 w-5" />
              Batch Processing
            </CardTitle>
            <CardDescription>
              Process multiple videos at once. Maximum 50 URLs per batch.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Video URLs (one per line)</label>
              <Textarea
                placeholder={`https://www.youtube.com/watch?v=dQw4w9WgXcQ
https://www.youtube.com/watch?v=9bZkp7q19f0
https://www.youtube.com/watch?v=astISOttCQ0`}
                value={batchUrls}
                onChange={(e) => setBatchUrls(e.target.value)}
                rows={6}
              />
            </div>

            <Button
              onClick={handleBatchProcessing}
              disabled={!batchUrls.trim() || processing}
              className="w-full"
            >
              {processing ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Upload className="h-4 w-4 mr-2" />
              )}
              Process Batch ({batchUrls.split('\n').filter(url => url.trim()).length} URLs)
            </Button>

            <div className="text-xs text-muted-foreground">
              Batch processing runs at low priority to avoid overwhelming the system.
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Processing Results</CardTitle>
            <CardDescription>
              Recent processing requests and their outcomes
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {results.map((result, index) => (
                <div
                  key={index}
                  className={`p-3 rounded-lg border ${
                    result.success ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      {result.success ? (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      ) : (
                        <AlertCircle className="h-4 w-4 text-red-600" />
                      )}
                      <Badge variant={result.type === 'direct' ? 'default' : 'secondary'}>
                        {result.type}
                      </Badge>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {result.timestamp.toLocaleTimeString()}
                    </span>
                  </div>

                  {result.success && result.data && (
                    <div className="mt-2 space-y-1">
                      {result.data.task_id && (
                        <div className="text-sm">
                          <span className="font-medium">Task ID:</span> {result.data.task_id}
                        </div>
                      )}
                      {result.data.video_id && (
                        <div className="text-sm">
                          <span className="font-medium">Video ID:</span> {result.data.video_id}
                        </div>
                      )}
                      {result.data.title && (
                        <div className="text-sm">
                          <span className="font-medium">Title:</span> {result.data.title}
                        </div>
                      )}
                      {result.data.transcript_segments && (
                        <div className="text-sm">
                          <span className="font-medium">Segments:</span> {result.data.transcript_segments}
                        </div>
                      )}
                      {result.data.tasks && (
                        <div className="text-sm">
                          <span className="font-medium">Batch Tasks:</span> {result.data.tasks.length}
                        </div>
                      )}
                      <div className="text-sm">
                        <span className="font-medium">Status:</span> {result.data.status}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {result.data.message}
                      </div>
                    </div>
                  )}

                  {!result.success && (
                    <div className="mt-2 text-sm text-red-600">
                      <span className="font-medium">Error:</span> {result.error}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Example URLs */}
      <Card>
        <CardHeader>
          <CardTitle>Example URLs</CardTitle>
          <CardDescription>
            Try these sample URLs to test the system
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <h4 className="font-medium mb-2">YouTube Videos</h4>
              <div className="space-y-1 text-sm text-muted-foreground">
                <div 
                  className="cursor-pointer hover:text-primary"
                  onClick={() => setSingleUrl('https://www.youtube.com/watch?v=dQw4w9WgXcQ')}
                >
                  • Rick Astley - Never Gonna Give You Up (4K)
                </div>
                <div 
                  className="cursor-pointer hover:text-primary"
                  onClick={() => setSingleUrl('https://www.youtube.com/watch?v=9bZkp7q19f0')}
                >
                  • Gangnam Style - PSY
                </div>
                <div 
                  className="cursor-pointer hover:text-primary"
                  onClick={() => setSingleUrl('https://www.youtube.com/watch?v=astISOttCQ0')}
                >
                  • Baby Shark Dance
                </div>
              </div>
            </div>
            <div>
              <h4 className="font-medium mb-2">Supported Features</h4>
              <div className="space-y-1 text-sm text-muted-foreground">
                <div>• Automatic metadata extraction</div>
                <div>• Whisper-powered transcription</div>
                <div>• Progress tracking and monitoring</div>
                <div>• Duplicate detection and handling</div>
                <div>• Error recovery and retry logic</div>
                <div>• Multi-platform content support</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}