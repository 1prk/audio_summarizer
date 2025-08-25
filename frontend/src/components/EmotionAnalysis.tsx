import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { intelligenceApi, type EmotionScore, type EmotionTimeline } from '../lib/api';

interface EmotionAnalysisProps {
  videoId?: string;
}

const EmotionAnalysis: React.FC<EmotionAnalysisProps> = ({ videoId }) => {
  const [emotions, setEmotions] = useState<EmotionScore[]>([]);
  const [timeline, setTimeline] = useState<EmotionTimeline[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedTimeRange, setSelectedTimeRange] = useState<{ start: number; end: number } | null>(null);
  const [filteredEmotions, setFilteredEmotions] = useState<EmotionScore[]>([]);
  const [viewMode, setViewMode] = useState<'overview' | 'timeline'>('overview');

  const loadEmotions = async () => {
    if (!videoId) return;
    
    setLoading(true);
    try {
      const response = await intelligenceApi.getVideoEmotions(videoId);
      setEmotions(response.emotions);
      setTimeline(response.timeline);
    } catch (error) {
      console.error('Failed to load emotions:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEmotions();
  }, [videoId]);

  const emotionCategories = {
    positive: ['joy', 'love', 'gratitude', 'optimism', 'caring', 'excitement', 'amusement', 'admiration', 'approval', 'relief'],
    negative: ['anger', 'annoyance', 'disappointment', 'disapproval', 'disgust', 'embarrassment', 'fear', 'grief', 'nervousness', 'remorse', 'sadness'],
    neutral: ['neutral', 'curiosity', 'confusion', 'realization', 'surprise'],
    complex: ['desire', 'pride', 'confusion']
  };

  const getEmotionColor = (emotion: string) => {
    if (emotionCategories.positive.includes(emotion)) return 'bg-green-100 text-green-800';
    if (emotionCategories.negative.includes(emotion)) return 'bg-red-100 text-red-800';
    if (emotionCategories.neutral.includes(emotion)) return 'bg-blue-100 text-blue-800';
    return 'bg-purple-100 text-purple-800';
  };

  const getEmotionCategory = (emotion: string) => {
    for (const [category, emotions] of Object.entries(emotionCategories)) {
      if (emotions.includes(emotion)) return category;
    }
    return 'other';
  };

  useEffect(() => {
    if (selectedTimeRange && timeline.length > 0) {
      const timelineInRange = timeline.filter(t => 
        t.timestamp >= selectedTimeRange.start && t.timestamp <= selectedTimeRange.end
      );
      const emotionsInRange = timelineInRange.flatMap(t => t.emotions);
      setFilteredEmotions(emotionsInRange);
    } else {
      setFilteredEmotions(emotions);
    }
  }, [selectedTimeRange, emotions, timeline]);

  const aggregatedEmotions = filteredEmotions.reduce((acc, emotion) => {
    if (!acc[emotion.emotion]) {
      acc[emotion.emotion] = { total: 0, count: 0, max: 0 };
    }
    acc[emotion.emotion].total += emotion.score;
    acc[emotion.emotion].count += 1;
    acc[emotion.emotion].max = Math.max(acc[emotion.emotion].max, emotion.score);
    return acc;
  }, {} as { [key: string]: { total: number; count: number; max: number } });

  const sortedEmotions = Object.entries(aggregatedEmotions)
    .map(([emotion, data]) => ({
      emotion,
      avgScore: data.total / data.count,
      maxScore: data.max,
      frequency: data.count
    }))
    .sort((a, b) => b.avgScore - a.avgScore);

  const emotionsByCategory = sortedEmotions.reduce((acc, emotion) => {
    const category = getEmotionCategory(emotion.emotion);
    if (!acc[category]) acc[category] = [];
    acc[category].push(emotion);
    return acc;
  }, {} as { [key: string]: typeof sortedEmotions });

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex justify-between items-center">
          Emotion Analysis
          <div className="flex gap-2">
            <button
              onClick={() => setViewMode('overview')}
              className={`px-3 py-1 text-sm rounded ${
                viewMode === 'overview' ? 'bg-blue-600 text-white' : 'bg-gray-200'
              }`}
            >
              Overview
            </button>
            <button
              onClick={() => setViewMode('timeline')}
              className={`px-3 py-1 text-sm rounded ${
                viewMode === 'timeline' ? 'bg-blue-600 text-white' : 'bg-gray-200'
              }`}
            >
              Timeline
            </button>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="text-center text-gray-500 py-8">
            Loading emotion analysis...
          </div>
        ) : viewMode === 'overview' && (
          <div className="space-y-6">
            {Object.entries(emotionsByCategory).map(([category, emotions]) => (
              <div key={category}>
                <h3 className="text-lg font-medium mb-3 capitalize">{category} Emotions</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {emotions.map((emotion) => (
                    <div key={emotion.emotion} className="p-3 border rounded-lg">
                      <div className="flex justify-between items-center mb-2">
                        <Badge className={getEmotionColor(emotion.emotion)}>
                          {emotion.emotion}
                        </Badge>
                        <span className="text-sm text-gray-500">
                          {Math.round(emotion.avgScore * 100)}%
                        </span>
                      </div>
                      <Progress value={emotion.avgScore * 100} className="mb-2" />
                      <div className="text-xs text-gray-500">
                        Max: {Math.round(emotion.maxScore * 100)}% | 
                        Freq: {emotion.frequency}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {viewMode === 'timeline' && timeline.length > 0 && (
          <div className="space-y-4">
            <div className="h-64 border rounded-lg p-4 overflow-y-auto">
              {timeline.map((point, index) => (
                <div 
                  key={index}
                  className="flex items-center gap-4 py-2 border-b last:border-b-0 cursor-pointer hover:bg-gray-50"
                  onClick={() => setSelectedTimeRange({
                    start: point.timestamp - 30,
                    end: point.timestamp + 30
                  })}
                >
                  <div className="w-16 text-sm text-gray-600">
                    {Math.floor(point.timestamp / 60)}:{String(Math.floor(point.timestamp % 60)).padStart(2, '0')}
                  </div>
                  <Badge className={getEmotionColor(point.dominantEmotion)}>
                    {point.dominantEmotion}
                  </Badge>
                  <div className="flex-1">
                    <div className="flex gap-1">
                      {point.emotions.slice(0, 3).map((emotion, i) => (
                        <div key={i} className="text-xs bg-gray-100 px-2 py-1 rounded">
                          {emotion.emotion}: {Math.round(emotion.score * 100)}%
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
            
            {selectedTimeRange && (
              <div className="p-3 bg-blue-50 border-l-4 border-blue-400">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium">
                    Selected Range: {Math.floor(selectedTimeRange.start / 60)}:{String(Math.floor(selectedTimeRange.start % 60)).padStart(2, '0')} - 
                    {Math.floor(selectedTimeRange.end / 60)}:{String(Math.floor(selectedTimeRange.end % 60)).padStart(2, '0')}
                  </span>
                  <button
                    onClick={() => setSelectedTimeRange(null)}
                    className="text-blue-600 hover:text-blue-800 text-sm"
                  >
                    Clear Selection
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {emotions.length === 0 && timeline.length === 0 && !loading && (
          <div className="text-center text-gray-500 py-8">
            {videoId ? 'No emotion analysis data available' : 'Select a video to view emotion analysis'}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default EmotionAnalysis;