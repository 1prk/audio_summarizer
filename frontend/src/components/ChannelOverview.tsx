import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { dataApi, type Channel, formatTime } from '@/lib/api';
import { 
  Users, 
  Video, 
  ExternalLink, 
  Search, 
  RefreshCw,
  Youtube,
  Mic,
  Radio,
  Globe
} from 'lucide-react';

export default function ChannelOverview() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const loadChannels = async () => {
    setLoading(true);
    try {
      const response = await dataApi.getChannels();
      setChannels(response.channels);
    } catch (error) {
      console.error('Failed to load channels:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadChannels();
  }, []);

  const filteredChannels = channels.filter(channel =>
    channel.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    channel.platform.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getPlatformIcon = (platform: string) => {
    switch (platform.toLowerCase()) {
      case 'youtube':
        return <Youtube className="h-5 w-5 text-red-600" />;
      case 'podcast':
        return <Mic className="h-5 w-5 text-purple-600" />;
      case 'twitch':
        return <Radio className="h-5 w-5 text-purple-500" />;
      default:
        return <Globe className="h-5 w-5 text-gray-600" />;
    }
  };

  const getPlatformBadgeVariant = (platform: string) => {
    switch (platform.toLowerCase()) {
      case 'youtube':
        return 'destructive' as const;
      case 'podcast':
        return 'secondary' as const;
      case 'twitch':
        return 'outline' as const;
      default:
        return 'default' as const;
    }
  };

  const platformStats = channels.reduce((acc, channel) => {
    acc[channel.platform] = (acc[channel.platform] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const totalVideos = channels.reduce((sum, channel) => sum + channel.video_count, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Channel Overview</h2>
          <p className="text-muted-foreground">
            Manage and monitor content sources across different platforms
          </p>
        </div>
        <Button 
          onClick={loadChannels} 
          variant="outline"
          size="sm"
          disabled={loading}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Statistics Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Total Channels
            </CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{channels.length}</div>
            <p className="text-xs text-muted-foreground">
              Active content sources
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Total Videos
            </CardTitle>
            <Video className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalVideos}</div>
            <p className="text-xs text-muted-foreground">
              Processed content items
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              YouTube Channels
            </CardTitle>
            <Youtube className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{platformStats.youtube || 0}</div>
            <p className="text-xs text-muted-foreground">
              YouTube content sources
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Other Platforms
            </CardTitle>
            <Globe className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {(platformStats.podcast || 0) + (platformStats.twitch || 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              Podcasts, Twitch, etc.
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Search and Filters */}
      <div className="flex gap-4 items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search channels by name or platform..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      {/* Platform Distribution */}
      {Object.keys(platformStats).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Platform Distribution</CardTitle>
            <CardDescription>
              Breakdown of channels by platform type
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4">
              {Object.entries(platformStats).map(([platform, count]) => (
                <div key={platform} className="flex items-center gap-2">
                  {getPlatformIcon(platform)}
                  <span className="font-medium capitalize">{platform}</span>
                  <Badge variant={getPlatformBadgeVariant(platform)}>
                    {count}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Channels List */}
      <Card>
        <CardHeader>
          <CardTitle>Channels ({filteredChannels.length})</CardTitle>
          <CardDescription>
            {searchTerm && filteredChannels.length !== channels.length && 
              `Showing ${filteredChannels.length} of ${channels.length} channels`
            }
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="h-6 w-6 animate-spin" />
            </div>
          ) : filteredChannels.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              {searchTerm ? (
                <>
                  <Search className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No channels match your search criteria</p>
                  <p className="text-sm">Try adjusting your search terms</p>
                </>
              ) : (
                <>
                  <Users className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No channels found</p>
                  <p className="text-sm">Start by processing some videos to create channels</p>
                </>
              )}
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {filteredChannels.map((channel) => (
                <Card key={channel.id} className="hover:shadow-md transition-shadow">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {getPlatformIcon(channel.platform)}
                        <Badge variant={getPlatformBadgeVariant(channel.platform)}>
                          {channel.platform}
                        </Badge>
                      </div>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => window.open(channel.url, '_blank')}
                      >
                        <ExternalLink className="h-3 w-3" />
                      </Button>
                    </div>
                    <CardTitle className="text-base leading-tight line-clamp-2">
                      {channel.name}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="flex items-center gap-1 text-muted-foreground">
                          <Video className="h-3 w-3" />
                          Videos
                        </span>
                        <span className="font-medium">{channel.video_count}</span>
                      </div>
                      
                      <div className="text-xs text-muted-foreground">
                        <div>ID: {channel.external_id}</div>
                        <div>Added: {formatTime(channel.created_at)}</div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Help Section */}
      <Card>
        <CardHeader>
          <CardTitle>About Channels</CardTitle>
          <CardDescription>
            Understanding how channels work in the audio summarizer
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <h4 className="font-medium mb-2">How Channels Are Created</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• Channels are automatically created when processing videos</li>
                <li>• Each platform (YouTube, podcast, Twitch) has its own channel structure</li>
                <li>• Channel information is extracted from video metadata</li>
                <li>• Duplicate channels are automatically detected and merged</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium mb-2">Channel Information</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• Name and platform are extracted from source</li>
                <li>• Video count shows processed videos from this channel</li>
                <li>• External ID links to the original platform identifier</li>
                <li>• URLs provide direct access to the source channel</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}