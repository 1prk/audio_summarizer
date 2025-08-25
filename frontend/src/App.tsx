import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ErrorBoundary from './components/ErrorBoundary';
import Sidebar from './components/Sidebar';
import HealthCheck from './components/HealthCheck';
import VideoProcessor from './components/VideoProcessor';
import TaskDashboard from './components/TaskDashboard';
import VideoLibrary from './components/VideoLibrary';
import ChannelOverview from './components/ChannelOverview';
import ContentIntelligence from './components/ContentIntelligence';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes
    },
  },
});

function App() {
  return (
    <ErrorBoundary fallbackMessage="The application encountered a critical error. Please refresh the page.">
      <QueryClientProvider client={queryClient}>
        <Router>
          <div className="flex h-screen bg-background">
            <ErrorBoundary fallbackMessage="The sidebar encountered an error.">
              <Sidebar />
            </ErrorBoundary>
            <main className="flex-1 overflow-y-auto p-6">
              <Routes>
                <Route path="/" element={<Navigate to="/health" replace />} />
                <Route path="/health" element={
                  <ErrorBoundary fallbackMessage="Health check component failed to load.">
                    <HealthCheck />
                  </ErrorBoundary>
                } />
                <Route path="/process" element={
                  <ErrorBoundary fallbackMessage="Video processing component failed to load.">
                    <VideoProcessor />
                  </ErrorBoundary>
                } />
                <Route path="/tasks" element={
                  <ErrorBoundary fallbackMessage="Task dashboard failed to load.">
                    <TaskDashboard />
                  </ErrorBoundary>
                } />
                <Route path="/videos" element={
                  <ErrorBoundary fallbackMessage="Video library failed to load.">
                    <VideoLibrary />
                  </ErrorBoundary>
                } />
                <Route path="/channels" element={
                  <ErrorBoundary fallbackMessage="Channel overview failed to load.">
                    <ChannelOverview />
                  </ErrorBoundary>
                } />
                <Route path="/intelligence" element={
                  <ErrorBoundary fallbackMessage="Content intelligence component failed to load.">
                    <ContentIntelligence />
                  </ErrorBoundary>
                } />
                <Route path="*" element={<Navigate to="/health" replace />} />
              </Routes>
            </main>
          </div>
        </Router>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
