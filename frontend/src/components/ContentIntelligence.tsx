import React, { useState } from 'react';
import { Card, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import EntityRecognition from './EntityRecognition';
import TopicModeling from './TopicModeling';
import VectorSearch from './VectorSearch';
import NetworkAnalysis from './NetworkAnalysis';


interface ContentIntelligenceProps {
  videoId?: string;
}

type TabType = 'entities' | 'topics' | 'emotions' | 'search' | 'network';

const ContentIntelligence: React.FC<ContentIntelligenceProps> = ({ videoId }) => {
  const [activeTab, setActiveTab] = useState<TabType>('entities');

  const tabs = [
    { id: 'entities' as TabType, label: 'Entity Recognition', description: 'People, organizations, and concepts' },
    { id: 'network' as TabType, label: 'Network Analysis', description: 'Entity relationships and connections' },
    { id: 'topics' as TabType, label: 'Topic Modeling', description: 'Discovered themes and subjects' },
    { id: 'emotions' as TabType, label: 'Emotion Analysis', description: '27-emotion sentiment analysis' },
    { id: 'search' as TabType, label: 'Semantic Search', description: 'Find content by meaning' }
  ];

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Content Intelligence Dashboard</CardTitle>
          <div className="flex gap-2 mt-4">
            {tabs.map((tab) => (
              <Button
                key={tab.id}
                variant={activeTab === tab.id ? 'default' : 'outline'}
                onClick={() => setActiveTab(tab.id)}
                className="flex flex-col items-start p-4 h-auto"
              >
                <span className="font-medium">{tab.label}</span>
                <span className="text-xs text-gray-500 mt-1">{tab.description}</span>
              </Button>
            ))}
          </div>
        </CardHeader>
      </Card>

      <div className="min-h-[600px]">
        {activeTab === 'entities' && (
          <EntityRecognition />
        )}
        
        {activeTab === 'network' && (
          <NetworkAnalysis />
        )}
        
        {activeTab === 'topics' && (
          <TopicModeling videoId={videoId} />
        )}
        
        {activeTab === 'search' && (
          <VectorSearch />
        )}
      </div>
    </div>
  );
};

export default ContentIntelligence;