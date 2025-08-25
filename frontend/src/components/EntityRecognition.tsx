import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { intelligenceApi, type Entity } from '../lib/api';

interface EntityRecognitionProps {
  // No video ID needed - shows all entities
}

const EntityRecognition: React.FC<EntityRecognitionProps> = () => {
  const [entities, setEntities] = useState<Entity[]>([]);
  const [filteredEntities, setFilteredEntities] = useState<Entity[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedLabel, setSelectedLabel] = useState('all');
  const [minConfidence, setMinConfidence] = useState(0.5);

  const entityTypes = [...new Set(entities.map(e => e.entity_type))];

  const loadEntities = async () => {
    setLoading(true);
    try {
      const response = await intelligenceApi.getEntities({
        min_confidence: minConfidence,
        search: searchTerm || undefined,
        type: selectedLabel !== 'all' ? selectedLabel : undefined,
        per_page: 100
      });
      setEntities(response.entities);
    } catch (error) {
      console.error('Failed to load entities:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEntities();
  }, [minConfidence, searchTerm, selectedLabel]);

  useEffect(() => {
    // Filtering is now done server-side in loadEntities
    setFilteredEntities(entities);
  }, [entities]);

  const getEntityColor = (label: string) => {
    const colors: { [key: string]: string } = {
      PERSON: 'bg-blue-100 text-blue-800',
      ORG: 'bg-green-100 text-green-800',
      PRODUCT: 'bg-purple-100 text-purple-800',
      TECH: 'bg-orange-100 text-orange-800',
      LOCATION: 'bg-red-100 text-red-800',
      MISC: 'bg-gray-100 text-gray-800'
    };
    return colors[label] || 'bg-gray-100 text-gray-800';
  };

  const entityCounts = entityTypes.reduce((acc, type) => {
    acc[type] = filteredEntities.filter(e => e.entity_type === type).length;
    return acc;
  }, {} as { [key: string]: number });

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Entity Recognition</CardTitle>
        <div className="flex gap-4 mt-4">
          <Input
            placeholder="Search entities..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="max-w-xs"
          />
          <select 
            value={selectedLabel} 
            onChange={(e) => setSelectedLabel(e.target.value)}
            className="px-3 py-2 border rounded-md w-48"
          >
            <option value="all">All Types</option>
            {entityTypes.map(type => (
              <option key={type} value={type}>
                {type} ({entityCounts[type]})
              </option>
            ))}
          </select>
          <div className="flex items-center gap-2">
            <span className="text-sm">Min Confidence:</span>
            <Input
              type="number"
              min="0"
              max="1"
              step="0.1"
              value={minConfidence}
              onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
              className="w-20"
            />
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="text-center text-gray-500 py-8">
            Loading entities...
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredEntities.map((entity) => (
                <div key={entity.id} className="p-3 border rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <Badge className={getEntityColor(entity.entity_type)}>
                      {entity.entity_type}
                    </Badge>
                    <span className="text-sm text-gray-500">
                      {Math.round(entity.confidence_score * 100)}%
                    </span>
                  </div>
                  <div className="text-lg font-medium mb-1">{entity.name}</div>
                  <div className="text-sm text-gray-600 mb-1">
                    {entity.canonical_name && entity.canonical_name !== entity.name && (
                      <span>({entity.canonical_name})</span>
                    )}
                  </div>
                  {entity.description && (
                    <div className="text-sm text-gray-500 mb-2">{entity.description}</div>
                  )}
                  <div className="text-xs text-gray-400">
                    Mentioned {entity.mention_count} time{entity.mention_count !== 1 ? 's' : ''}
                  </div>
                </div>
              ))}
            </div>
            {filteredEntities.length === 0 && !loading && (
              <div className="text-center text-gray-500 py-8">
                No entities found matching current filters
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
};

export default EntityRecognition;