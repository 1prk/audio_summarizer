import { useEffect, useState, useRef } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { tasksApi, type Task, type TaskStatusResponse, formatTime, getStatusBadgeVariant } from '@/lib/api';
import { 
  RefreshCw, 
  Play, 
  Pause, 
  Square, 
  Clock, 
  CheckCircle, 
  XCircle, 
  AlertTriangle,
  Filter,
  Eye,
  StopCircle
} from 'lucide-react';

export default function TaskDashboard() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedTask, setSelectedTask] = useState<TaskStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const [pagination, setPagination] = useState({
    page: 1,
    per_page: 20,
    total: 0,
    pages: 0,
    has_next: false,
    has_prev: false
  });

  const loadTasks = async (page = 1, status?: string) => {
    setLoading(true);
    try {
      const params: any = { page, per_page: 20 };
      if (status && status !== 'all') {
        params.status = status;
      }
      
      const response = await tasksApi.getTasks(params);
      setTasks(response.tasks);
      setPagination(response.pagination);
    } catch (error) {
      console.error('Failed to load tasks:', error);
    } finally {
      setLoading(false);
    }
  };

  const refreshTasks = async () => {
    if (refreshing) return; // Prevent concurrent refresh calls
    setRefreshing(true);
    try {
      await loadTasks(pagination.page, statusFilter === 'all' ? undefined : statusFilter);
    } catch (error) {
      console.error('Failed to refresh tasks:', error);
    } finally {
      setRefreshing(false);
    }
  };

  const loadTaskDetails = async (taskId: string) => {
    try {
      const taskDetails = await tasksApi.getTaskStatus(taskId);
      setSelectedTask(taskDetails);
    } catch (error) {
      console.error('Failed to load task details:', error);
    }
  };

  const cancelTask = async (taskId: string) => {
    try {
      await tasksApi.cancelTask(taskId);
      await refreshTasks();
      if (selectedTask?.task_id === taskId) {
        await loadTaskDetails(taskId);
      }
    } catch (error) {
      console.error('Failed to cancel task:', error);
    }
  };

  useEffect(() => {
    loadTasks();
  }, []);

  useEffect(() => {
    loadTasks(1, statusFilter === 'all' ? undefined : statusFilter);
  }, [statusFilter]);

  // Auto-refresh for active tasks - also refresh completed tasks to ensure progress is 100%
  useEffect(() => {
    // Clear existing interval
    if (refreshIntervalRef.current) {
      clearInterval(refreshIntervalRef.current);
    }

    const hasActiveTasks = tasks.some(task => 
      task.status === 'processing' || task.status === 'queued'
    );
    
    // Also refresh if we have completed tasks with progress < 100%
    const hasIncompleteCompleted = tasks.some(task =>
      task.status === 'completed' && task.progress < 100
    );
    
    if (hasActiveTasks || hasIncompleteCompleted) {
      refreshIntervalRef.current = setInterval(() => {
        if (!refreshing) { // Only refresh if not already refreshing
          refreshTasks();
        }
      }, 5000);
    }

    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, [tasks, refreshing]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'processing':
        return <Play className="h-4 w-4 text-blue-600" />;
      case 'queued':
        return <Clock className="h-4 w-4 text-yellow-600" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-600" />;
      case 'cancelled':
        return <StopCircle className="h-4 w-4 text-gray-600" />;
      default:
        return <AlertTriangle className="h-4 w-4 text-gray-600" />;
    }
  };

  const getTaskTypeIcon = (taskType: string) => {
    switch (taskType) {
      case 'transcription':
        return '🎵';
      default:
        return '📄';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Task Management</h2>
          <p className="text-muted-foreground">
            Monitor and manage background processing tasks
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[180px]">
              <Filter className="h-4 w-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="queued">Queued</SelectItem>
              <SelectItem value="processing">Processing</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="cancelled">Cancelled</SelectItem>
            </SelectContent>
          </Select>
          
          <Button 
            onClick={refreshTasks} 
            disabled={refreshing}
            variant="outline"
            size="sm"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Task List */}
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Tasks ({pagination.total})</CardTitle>
              <CardDescription>
                Background processing tasks and their current status
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="h-6 w-6 animate-spin" />
                </div>
              ) : tasks.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No tasks found
                </div>
              ) : (
                <div className="space-y-3">
                  {tasks.map((task) => (
                    <div
                      key={task.id}
                      className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 cursor-pointer"
                      onClick={() => loadTaskDetails(task.id)}
                    >
                      <div className="flex items-center gap-3 flex-1">
                        <span className="text-lg">{getTaskTypeIcon(task.task_type)}</span>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            {getStatusIcon(task.status)}
                            <Badge variant={getStatusBadgeVariant(task.status)}>
                              {task.status}
                            </Badge>
                            <span className="text-sm text-muted-foreground">
                              {task.task_type}
                            </span>
                          </div>
                          <div className="text-sm text-muted-foreground truncate">
                            ID: {task.id}
                          </div>
                          {task.status === 'processing' && (
                            <Progress value={task.progress} className="mt-2 h-2" />
                          )}
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <div className="text-right">
                          <div className="text-sm">
                            {task.progress.toFixed(1)}%
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {formatTime(task.created_at)}
                          </div>
                        </div>
                        
                        {(task.status === 'processing' || task.status === 'queued') && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={(e) => {
                              e.stopPropagation();
                              cancelTask(task.id);
                            }}
                          >
                            <Square className="h-3 w-3" />
                          </Button>
                        )}
                        
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={(e) => {
                            e.stopPropagation();
                            loadTaskDetails(task.id);
                          }}
                        >
                          <Eye className="h-3 w-3" />
                        </Button>
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
                    onClick={() => loadTasks(pagination.page - 1, statusFilter === 'all' ? undefined : statusFilter)}
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
                    onClick={() => loadTasks(pagination.page + 1, statusFilter === 'all' ? undefined : statusFilter)}
                  >
                    Next
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Task Details */}
        <div>
          <Card>
            <CardHeader>
              <CardTitle>Task Details</CardTitle>
              <CardDescription>
                Detailed information about the selected task
              </CardDescription>
            </CardHeader>
            <CardContent>
              {selectedTask ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(selectedTask.status)}
                      <Badge variant={getStatusBadgeVariant(selectedTask.status)}>
                        {selectedTask.status}
                      </Badge>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => loadTaskDetails(selectedTask.task_id)}
                    >
                      <RefreshCw className="h-3 w-3" />
                    </Button>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <h4 className="font-medium">Task ID</h4>
                      <p className="text-sm text-muted-foreground font-mono">
                        {selectedTask.task_id}
                      </p>
                    </div>

                    <div>
                      <h4 className="font-medium">Type</h4>
                      <p className="text-sm text-muted-foreground">
                        {selectedTask.task_type}
                      </p>
                    </div>

                    <div>
                      <h4 className="font-medium">Progress</h4>
                      <div className="space-y-2">
                        <Progress value={selectedTask.progress} />
                        <p className="text-sm text-muted-foreground">
                          {selectedTask.progress.toFixed(1)}%
                        </p>
                        {selectedTask.current_step && (
                          <p className="text-sm text-muted-foreground">
                            {selectedTask.current_step}
                          </p>
                        )}
                      </div>
                    </div>

                    <div>
                      <h4 className="font-medium">Timeline</h4>
                      <div className="text-sm text-muted-foreground space-y-1">
                        <div>Created: {formatTime(selectedTask.created_at)}</div>
                        {selectedTask.started_at && (
                          <div>Started: {formatTime(selectedTask.started_at)}</div>
                        )}
                        {selectedTask.completed_at && (
                          <div>Completed: {formatTime(selectedTask.completed_at)}</div>
                        )}
                      </div>
                    </div>

                    {selectedTask.error && (
                      <div>
                        <h4 className="font-medium text-red-600">Error</h4>
                        <p className="text-sm text-red-600">
                          {selectedTask.error}
                        </p>
                      </div>
                    )}

                    {selectedTask.video && (
                      <div>
                        <h4 className="font-medium">Video</h4>
                        <div className="text-sm text-muted-foreground space-y-1">
                          <div>Title: {selectedTask.video.title}</div>
                          <div>ID: {selectedTask.video.id}</div>
                          <div>Platform: {selectedTask.video.platform}</div>
                          <div>Status: {selectedTask.video.processing_status}</div>
                        </div>
                      </div>
                    )}

                    {selectedTask.celery && (
                      <div>
                        <h4 className="font-medium">Celery Info</h4>
                        <div className="text-sm text-muted-foreground space-y-1">
                          <div>Task ID: {selectedTask.celery.task_id}</div>
                          <div>State: {selectedTask.celery.state}</div>
                        </div>
                      </div>
                    )}

                    {selectedTask.result && (
                      <div>
                        <h4 className="font-medium">Result</h4>
                        <pre className="text-xs text-muted-foreground bg-muted p-2 rounded overflow-auto">
                          {JSON.stringify(selectedTask.result, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>

                  {(selectedTask.status === 'processing' || selectedTask.status === 'queued') && (
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => cancelTask(selectedTask.task_id)}
                      className="w-full"
                    >
                      <Square className="h-4 w-4 mr-2" />
                      Cancel Task
                    </Button>
                  )}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  Select a task to view details
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}