# Audio Summarizer Frontend

A modern React/TypeScript frontend for the Personal Video Intelligence Platform, built with Vite and shadcn/ui components.

## 🚀 Features

### ✅ Complete Implementation
- **System Health Monitoring** - Real-time API connectivity and service status
- **Video Processing Interface** - Single video, batch processing, and direct processing modes
- **Task Management Dashboard** - Monitor background jobs with real-time progress tracking
- **Video Library** - Browse processed videos with search, filtering, and transcript viewing
- **Channel Overview** - Manage content sources across YouTube, podcasts, and Twitch
- **Responsive Design** - Works seamlessly on desktop, tablet, and mobile devices

### 🎨 UI/UX Excellence
- **shadcn/ui Components** - Modern, accessible component library
- **Dark/Light Mode Ready** - CSS variables for theme switching
- **Real-time Updates** - Auto-refreshing data for active tasks
- **Interactive Transcripts** - Searchable, exportable transcript viewer
- **Progress Tracking** - Visual progress bars and status indicators
- **Error Handling** - Comprehensive error states and user feedback

## 🏗️ Architecture

### Tech Stack
- **Frontend Framework**: React 18 with TypeScript
- **Build Tool**: Vite 7
- **UI Components**: shadcn/ui (Radix UI + Tailwind CSS)
- **Routing**: React Router DOM
- **Data Fetching**: TanStack Query (React Query)
- **HTTP Client**: Axios
- **Styling**: Tailwind CSS with CSS variables
- **Icons**: Lucide React

### Project Structure
```
frontend/
├── src/
│   ├── components/           # React components
│   │   ├── ui/              # shadcn/ui base components
│   │   ├── HealthCheck.tsx  # System health monitoring
│   │   ├── VideoProcessor.tsx # Video processing interface
│   │   ├── TaskDashboard.tsx # Task management
│   │   ├── VideoLibrary.tsx # Video browser and transcript viewer
│   │   ├── ChannelOverview.tsx # Channel management
│   │   └── Sidebar.tsx      # Navigation sidebar
│   ├── lib/
│   │   ├── api.ts          # API client and types
│   │   └── utils.ts        # Utility functions
│   ├── App.tsx             # Main application with routing
│   ├── main.tsx            # Application entry point
│   └── index.css           # Global styles and CSS variables
├── package.json            # Dependencies and scripts
├── vite.config.ts          # Vite configuration
├── tailwind.config.js      # Tailwind CSS configuration
└── tsconfig.json           # TypeScript configuration
```

## 🚀 Quick Start

### Prerequisites
- Node.js 20.12+ (with npm 10.5+)
- Backend API running on `http://localhost:5000`

### Development Setup

1. **Install Dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Start Development Server**:
   ```bash
   npm run dev
   ```

3. **Open Browser**:
   Navigate to `http://localhost:5173`

### Production Build

```bash
npm run build
npm run preview  # Preview production build
```

## 📡 API Integration

The frontend connects to the Flask backend API with comprehensive coverage of all endpoints:

### Health & Status
- `GET /api/ping` - Basic connectivity test
- `GET /api/health` - Comprehensive system health check

### Video Processing
- `POST /api/process/video` - Queue video processing with priority
- `POST /api/process/direct` - Direct processing (bypass queue)
- `POST /api/process/batch` - Batch processing (up to 50 URLs)

### Task Management
- `GET /api/tasks` - List tasks with pagination and filtering
- `GET /api/tasks/{id}` - Get detailed task status with Celery integration
- `POST /api/tasks/{id}/cancel` - Cancel running tasks

### Data Retrieval
- `GET /api/videos` - Browse processed videos with pagination
- `GET /api/videos/{id}/transcripts` - View video transcripts
- `GET /api/channels` - Channel overview and statistics

## 🎯 Key Features Breakdown

### 1. System Health Dashboard
- Real-time API connectivity monitoring
- Database and Whisper service status
- System information and capabilities overview
- Automatic health checks with manual refresh

### 2. Video Processing Interface
- **Single Video Processing**: Submit individual videos with priority levels (low/normal/high)
- **Direct Processing**: Bypass Celery queue for immediate processing
- **Batch Processing**: Submit up to 50 URLs simultaneously
- **Example URLs**: Pre-populated test URLs including Rick Roll video
- **Real-time Results**: Live processing status and results display

### 3. Task Management Dashboard
- **Real-time Monitoring**: Auto-refreshing active tasks every 5 seconds
- **Detailed Task Views**: Progress bars, timestamps, error messages
- **Filtering**: Filter by status (queued/processing/completed/failed/cancelled)
- **Task Control**: Cancel running tasks, view Celery integration details
- **Pagination**: Handle large task lists efficiently

### 4. Video Library
- **Search & Filter**: Search by title/channel, filter by processing status
- **Transcript Viewer**: Interactive transcript display with timestamps
- **Export Functionality**: Download transcripts as text files
- **Video Details**: Comprehensive metadata and processing information
- **Responsive Grid**: Optimized layout for different screen sizes

### 5. Channel Overview
- **Platform Statistics**: YouTube, podcast, Twitch channel counts
- **Channel Cards**: Visual overview of each content source
- **Search Functionality**: Find channels quickly by name or platform
- **External Links**: Direct access to original platform channels
- **Auto-discovery**: Channels created automatically during video processing

## 🎨 Design System

### Color Scheme
The interface uses CSS variables for consistent theming:
- **Primary**: Blue (#3b82f6) for actions and highlights
- **Secondary**: Gray tones for backgrounds and muted content
- **Success**: Green for completed states
- **Warning**: Yellow for processing states
- **Error**: Red for failed states

### Component Hierarchy
- **Sidebar Navigation**: Collapsible sidebar with route indicators
- **Page Layouts**: Consistent header, content, and action areas
- **Cards**: Grouped content with clear visual hierarchy
- **Interactive Elements**: Hover states, loading indicators, progress bars

## 🔄 Real-time Features

### Auto-refresh Logic
- **Health Check**: Manual refresh with loading states
- **Task Dashboard**: Auto-refresh every 5 seconds for active tasks
- **Video Processing**: Real-time result updates
- **Progress Tracking**: Live progress bars and status updates

### Error Handling
- **Network Errors**: Clear error messages and retry options
- **API Errors**: Detailed error responses with user-friendly messages
- **Loading States**: Consistent loading indicators throughout the app
- **Fallback Content**: Meaningful empty states and placeholder content

## 🧪 Example Usage Workflow

### 1. Check System Health
- Navigate to Health tab
- Verify API connectivity and service status
- Review system capabilities and version information

### 2. Process a Video
- Go to Process Videos tab
- Enter YouTube URL (e.g., Rick Roll video)
- Select priority level and submit
- Monitor progress in Task Manager

### 3. Monitor Processing
- Switch to Task Manager tab
- Watch real-time progress updates
- View detailed task information
- Cancel if needed

### 4. Browse Results
- Visit Video Library tab
- Search and filter processed videos
- Click on Rick Roll video to view transcripts
- Export transcript if desired

### 5. Explore Channels
- Check Channels tab
- View Rick Astley channel information
- See platform distribution statistics

## 🔧 Configuration

### API Endpoint
Update the API base URL in `src/lib/api.ts`:
```typescript
const API_BASE_URL = 'http://localhost:5000';
```

### Query Client Settings
Modify React Query settings in `src/App.tsx`:
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes
    },
  },
});
```

## 🚀 Deployment

### Build for Production
```bash
npm run build
```

### Deploy to Static Hosting
The built files in `dist/` can be deployed to:
- Netlify
- Vercel
- GitHub Pages
- AWS S3 + CloudFront
- Any static hosting service

### Docker Deployment
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 5173
CMD ["npm", "run", "preview"]
```

## 🎯 Rick Roll Demo

The frontend is perfectly configured to work with the Rick Roll video example:
- **Video ID**: `3c5669c0-04df-4cf5-ae4e-cd85641dfab6`
- **YouTube URL**: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
- **Transcript Segments**: 56 segments successfully processed
- **Duration**: 213 seconds (3:33)

Use this example to test all features:
1. Process the video using the pre-filled URL
2. Monitor the task in Task Manager
3. View the 56 transcript segments in Video Library
4. Explore the Rick Astley channel information

## 🔮 Future Enhancements

### Phase 4+ Features Ready
The frontend architecture supports future Phase 4+ features:
- Knowledge graph visualizations
- Content intelligence analytics
- Topic modeling displays
- Entity relationship networks
- Advanced search and discovery
- Spatial content exploration

### Planned Improvements
- Dark mode toggle
- User preferences storage
- Keyboard shortcuts
- Advanced filtering options
- Data visualization components
- Mobile app (React Native)

## 🤝 Contributing

The frontend follows modern React best practices:
- TypeScript for type safety
- Component-driven architecture
- Consistent error handling
- Accessible UI components
- Performance optimizations

## 📄 License

Part of the Personal Video Intelligence Platform - see main project README for licensing information.

---

**Built with ❤️ using React, TypeScript, Vite, and shadcn/ui**