import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { healthApi, type HealthResponse, type PingResponse } from '@/lib/api';
import { Activity, Database, Mic, RefreshCw } from 'lucide-react';

export default function HealthCheck() {
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);
  const [pingData, setPingData] = useState<PingResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const checkHealth = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const [health, ping] = await Promise.all([
        healthApi.health(),
        healthApi.ping()
      ]);
      
      setHealthData(health);
      setPingData(ping);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Health check failed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
  }, []);

  const getStatusBadge = (status: string) => {
    const isHealthy = status === 'healthy';
    return (
      <Badge variant={isHealthy ? 'default' : 'destructive'}>
        {status}
      </Badge>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">System Health</h2>
          <p className="text-muted-foreground">
            Monitor the health and status of all system components
          </p>
        </div>
        <Button 
          onClick={checkHealth} 
          disabled={loading}
          variant="outline"
          size="sm"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {error && (
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-destructive">Connection Error</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
        </Card>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        {/* Overall Status */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Overall Status
            </CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {healthData ? (
                <>
                  <div className="flex items-center justify-between">
                    <span>System Status</span>
                    {getStatusBadge(healthData.status)}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Version: {healthData.version}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Last checked: {new Date(healthData.timestamp).toLocaleString()}
                  </div>
                </>
              ) : (
                <div className="text-sm text-muted-foreground">
                  {loading ? 'Checking...' : 'No data available'}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* API Connectivity */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              API Connectivity
            </CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {pingData ? (
                <>
                  <div className="flex items-center justify-between">
                    <span>API Status</span>
                    <Badge variant="default">Connected</Badge>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Response: {pingData.message}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Ping time: {new Date(pingData.timestamp).toLocaleString()}
                  </div>
                </>
              ) : (
                <div className="text-sm text-muted-foreground">
                  {loading ? 'Checking...' : 'No connectivity data'}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Database Status */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Database
            </CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {healthData?.services ? (
                <>
                  <div className="flex items-center justify-between">
                    <span>Database Status</span>
                    {getStatusBadge(healthData.services.database)}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    PostgreSQL with SQLAlchemy ORM
                  </div>
                </>
              ) : (
                <div className="text-sm text-muted-foreground">
                  {loading ? 'Checking...' : 'No database status available'}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Whisper Status */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Whisper Transcription
            </CardTitle>
            <Mic className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {healthData?.services ? (
                <>
                  <div className="flex items-center justify-between">
                    <span>Whisper Status</span>
                    {getStatusBadge(healthData.services.whisper)}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    OpenAI Whisper model for audio transcription
                  </div>
                </>
              ) : (
                <div className="text-sm text-muted-foreground">
                  {loading ? 'Checking...' : 'No Whisper status available'}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* System Info */}
      {healthData && (
        <Card>
          <CardHeader>
            <CardTitle>System Information</CardTitle>
            <CardDescription>
              Detailed information about the audio summarizer platform
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <h4 className="font-medium">Backend Features</h4>
                <ul className="text-sm text-muted-foreground mt-1 space-y-1">
                  <li>• Multi-platform video processing</li>
                  <li>• Real-time transcription with Whisper</li>
                  <li>• Background task management</li>
                  <li>• Content intelligence analysis</li>
                </ul>
              </div>
              <div>
                <h4 className="font-medium">Supported Platforms</h4>
                <ul className="text-sm text-muted-foreground mt-1 space-y-1">
                  <li>• YouTube videos</li>
                  <li>• Podcast episodes</li>
                  <li>• Twitch streams</li>
                  <li>• Direct audio files</li>
                </ul>
              </div>
              <div>
                <h4 className="font-medium">API Capabilities</h4>
                <ul className="text-sm text-muted-foreground mt-1 space-y-1">
                  <li>• RESTful API endpoints</li>
                  <li>• Real-time progress tracking</li>
                  <li>• Batch processing support</li>
                  <li>• Comprehensive error handling</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}