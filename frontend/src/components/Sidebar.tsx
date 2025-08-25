import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { 
  Activity, 
  Upload, 
  Clock, 
  Video, 
  Users, 
  Menu,
  X,
  Brain,
  Zap,
  Search
} from 'lucide-react';

const navigation = [
  {
    name: 'System Health',
    href: '/health',
    icon: Activity,
    description: 'Monitor system status and connectivity'
  },
  {
    name: 'Process Videos',
    href: '/process',
    icon: Upload,
    description: 'Submit videos for transcription'
  },
  {
    name: 'Task Manager',
    href: '/tasks',
    icon: Clock,
    description: 'Monitor background processing'
  },
  {
    name: 'Video Library',
    href: '/videos',
    icon: Video,
    description: 'Browse videos and transcripts'
  },
  {
    name: 'Channels',
    href: '/channels',
    icon: Users,
    description: 'Manage content sources'
  },
  {
    name: 'Intelligence',
    href: '/intelligence',
    icon: Search,
    description: 'Content analysis and search'
  },
];

export default function Sidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const location = useLocation();

  return (
    <div className={cn(
      "flex flex-col bg-card border-r transition-all duration-300",
      isCollapsed ? "w-16" : "w-64"
    )}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        {!isCollapsed && (
          <div className="flex items-center gap-2">
            <div className="p-2 bg-primary rounded-lg">
              <Brain className="h-5 w-5 text-primary-foreground" />
            </div>
            <div>
              <h1 className="font-semibold text-lg">Audio Summarizer</h1>
              <p className="text-xs text-muted-foreground">Video Intelligence Platform</p>
            </div>
          </div>
        )}
        
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsCollapsed(!isCollapsed)}
        >
          {isCollapsed ? <Menu className="h-4 w-4" /> : <X className="h-4 w-4" />}
        </Button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href;
          
          return (
            <Link key={item.name} to={item.href}>
              <Button
                variant={isActive ? "secondary" : "ghost"}
                className={cn(
                  "w-full justify-start gap-3 h-auto py-3",
                  isCollapsed && "px-3"
                )}
              >
                <item.icon className="h-5 w-5 shrink-0" />
                {!isCollapsed && (
                  <div className="text-left">
                    <div className="font-medium">{item.name}</div>
                    <div className="text-xs text-muted-foreground">{item.description}</div>
                  </div>
                )}
              </Button>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t">
        {!isCollapsed ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm">
              <Zap className="h-4 w-4 text-green-600" />
              <span className="text-muted-foreground">API Connected</span>
            </div>
            
            <div className="text-xs text-muted-foreground">
              <div>Phase 1-3 Implementation</div>
              <div>React + Flask + Whisper</div>
              <div className="mt-2 p-2 bg-muted rounded text-center">
                <div className="font-medium">Features Available</div>
                <div>• Multi-platform processing</div>
                <div>• Real-time transcription</div>
                <div>• Task management</div>
                <div>• Content intelligence</div>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex justify-center">
            <Zap className="h-4 w-4 text-green-600" />
          </div>
        )}
      </div>
    </div>
  );
}