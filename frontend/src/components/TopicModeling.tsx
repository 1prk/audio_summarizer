import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Input } from './ui/input';
import { Progress } from './ui/progress';
import { intelligenceApi, type Topic } from '../lib/api';

interface TopicModelingProps {
  videoId?: string;
}

const TopicModeling: React.FC<TopicModelingProps> = ({ videoId }) => {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [filteredTopics, setFilteredTopics] = useState<Topic[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState<'coherence' | 'documents' | 'label'>('coherence');
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null);
  const [viewMode, setViewMode] = useState<'all' | 'video'>('all');

  const loadTopics = async () => {
    setLoading(true);
    try {
      if (viewMode === 'video' && videoId) {
        const response = await intelligenceApi.getVideoTopics(videoId);
        setTopics(response.topics);
      } else {
        const response = await intelligenceApi.getTopics();
        setTopics(response.topics);
      }
    } catch (error) {
      console.error('Failed to load topics:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTopics();
  }, [viewMode, videoId]);

  useEffect(() => {
    let filtered = topics;

    if (searchTerm) {
      filtered = filtered.filter(topic => 
        topic.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
        topic.keywords.some(keyword => 
          keyword.toLowerCase().includes(searchTerm.toLowerCase())
        )
      );
    }

    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'coherence':
          return b.coherence - a.coherence;
        case 'documents':
          return b.documentCount - a.documentCount;
        case 'label':
          return a.label.localeCompare(b.label);
        default:
          return 0;
      }
    });

    setFilteredTopics(filtered);
  }, [topics, searchTerm, sortBy]);

  const handleTopicClick = (topic: Topic) => {
    setSelectedTopic(topic);
  };

  const getCoherenceColor = (coherence: number) => {
    if (coherence >= 0.7) return 'bg-green-100 text-green-800';
    if (coherence >= 0.5) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  return (
    <div className="flex gap-6">
      <Card className="flex-1">
        <CardHeader>
          <CardTitle>Topic Discovery</CardTitle>
          <div className="flex gap-4 mt-4">
            <Input
              placeholder="Search topics and keywords..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="max-w-xs"
            />
            <select 
              value={sortBy} 
              onChange={(e) => setSortBy(e.target.value as 'coherence' | 'documents' | 'label')}
              className="px-3 py-2 border rounded-md"
            >
              <option value="coherence">By Coherence</option>
              <option value="documents">By Document Count</option>
              <option value="label">By Name</option>
            </select>
            <select 
              value={viewMode} 
              onChange={(e) => setViewMode(e.target.value as 'all' | 'video')}
              className="px-3 py-2 border rounded-md"
            >
              <option value="all">All Topics</option>
              {videoId && <option value="video">Video Topics</option>}
            </select>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center text-gray-500 py-8">
              Loading topics...
            </div>
          ) : (
            <div className="space-y-4">
              {filteredTopics.map((topic) => (
              <div 
                key={topic.id}
                className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                  selectedTopic?.id === topic.id ? 'bg-blue-50 border-blue-300' : 'hover:bg-gray-50'
                }`}
                onClick={() => handleTopicClick(topic)}
              >
                <div className="flex justify-between items-start mb-2">
                  <h3 className="text-lg font-medium">{topic.label}</h3>
                  <div className="flex gap-2">
                    <Badge className={getCoherenceColor(topic.coherence)}>
                      {Math.round(topic.coherence * 100)}% coherent
                    </Badge>
                    <Badge variant="secondary">
                      {topic.documentCount} docs
                    </Badge>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1 mb-2">
                  {topic.keywords.slice(0, 8).map((keyword, index) => (
                    <span 
                      key={index}
                      className="px-2 py-1 bg-gray-100 text-gray-700 text-sm rounded"
                    >
                      {keyword}
                    </span>
                  ))}
                  {topic.keywords.length > 8 && (
                    <span className="px-2 py-1 text-gray-500 text-sm">
                      +{topic.keywords.length - 8} more
                    </span>
                  )}
                </div>
                <Progress value={topic.coherence * 100} className="h-2" />
              </div>
            ))}
            </div>
          )}
          {filteredTopics.length === 0 && !loading && (
            <div className="text-center text-gray-500 py-8">
              No topics found matching current search
            </div>
          )}
        </CardContent>
      </Card>

      {selectedTopic && (
        <Card className="w-96">
          <CardHeader>
            <CardTitle>Topic Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-medium mb-2">{selectedTopic.label}</h3>
                <div className="flex gap-2 mb-4">
                  <Badge className={getCoherenceColor(selectedTopic.coherence)}>
                    {Math.round(selectedTopic.coherence * 100)}% coherent
                  </Badge>
                  <Badge variant="secondary">
                    {selectedTopic.documentCount} documents
                  </Badge>
                </div>
              </div>
              
              <div>
                <h4 className="font-medium mb-2">Keywords</h4>
                <div className="flex flex-wrap gap-1">
                  {selectedTopic.keywords.map((keyword, index) => (
                    <span 
                      key={index}
                      className="px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded"
                    >
                      {keyword}
                    </span>
                  ))}
                </div>
              </div>

              {selectedTopic.evolution && selectedTopic.evolution.length > 0 && (
                <div>
                  <h4 className="font-medium mb-2">Topic Evolution</h4>
                  <div className="space-y-2">
                    {selectedTopic.evolution.slice(-5).map((point, index) => (
                      <div key={index} className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">
                          {new Date(point.timestamp).toLocaleDateString()}
                        </span>
                        <div className="flex items-center gap-2">
                          <Progress value={point.strength * 100} className="w-20 h-2" />
                          <span className="text-sm">{Math.round(point.strength * 100)}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default TopicModeling;