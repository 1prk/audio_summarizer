import React, { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { Textarea } from './ui/textarea';
import { intelligenceApi, type SearchResult } from '../lib/api';

interface VectorSearchProps {
  placeholder?: string;
}

const VectorSearch: React.FC<VectorSearchProps> = ({ 
  placeholder = "Search by semantic meaning..."
}) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [threshold, setThreshold] = useState(0.7);
  const [limit, setLimit] = useState(20);
  const [searchHistory, setSearchHistory] = useState<string[]>([]);

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return;

    setIsLoading(true);
    try {
      const searchResults = await intelligenceApi.semanticSearch(query, {
        threshold,
        limit,
        includeMetadata: true
      });
      
      setResults(searchResults);
      
      // Add to search history
      setSearchHistory(prev => {
        const newHistory = [query, ...prev.filter(h => h !== query)];
        return newHistory.slice(0, 10);
      });
    } catch (error) {
      console.error('Search failed:', error);
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  }, [query, threshold, limit]);

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
  };

  const getSimilarityColor = (similarity: number) => {
    if (similarity >= 0.9) return 'bg-green-100 text-green-800';
    if (similarity >= 0.8) return 'bg-blue-100 text-blue-800';
    if (similarity >= 0.7) return 'bg-yellow-100 text-yellow-800';
    return 'bg-gray-100 text-gray-800';
  };

  const formatTimestamp = (timestamp: number) => {
    const minutes = Math.floor(timestamp / 60);
    const seconds = Math.floor(timestamp % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Semantic Search</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-4">
            <div className="flex-1">
              <Textarea
                placeholder={placeholder}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                className="min-h-[100px]"
              />
            </div>
            <div className="flex flex-col gap-2 w-48">
              <div>
                <label className="text-sm font-medium">Similarity Threshold</label>
                <Input
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={threshold}
                  onChange={(e) => setThreshold(parseFloat(e.target.value))}
                />
              </div>
              <div>
                <label className="text-sm font-medium">Max Results</label>
                <Input
                  type="number"
                  min="1"
                  max="100"
                  value={limit}
                  onChange={(e) => setLimit(parseInt(e.target.value))}
                />
              </div>
            </div>
          </div>
          
          <div className="flex justify-between items-center">
            <Button 
              onClick={handleSearch}
              disabled={!query.trim() || isLoading}
              className="px-6"
            >
              {isLoading ? 'Searching...' : 'Search'}
            </Button>
            
            {searchHistory.length > 0 && (
              <div className="flex gap-2 items-center">
                <span className="text-sm text-gray-600">Recent:</span>
                {searchHistory.slice(0, 3).map((hist, index) => (
                  <Button
                    key={index}
                    variant="outline"
                    size="sm"
                    onClick={() => setQuery(hist)}
                    className="text-xs"
                  >
                    {hist.length > 20 ? hist.substring(0, 20) + '...' : hist}
                  </Button>
                ))}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {results.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Search Results ({results.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {results.map((result) => (
                <div key={result.id} className="p-4 border rounded-lg hover:bg-gray-50">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex-1">
                      <h3 className="text-lg font-medium mb-1">{result.title}</h3>
                      {result.channel && (
                        <div className="text-sm text-gray-600 mb-2">
                          Channel: {result.channel}
                          {result.timestamp && (
                            <span> • {formatTimestamp(result.timestamp)}</span>
                          )}
                        </div>
                      )}
                    </div>
                    <Badge className={getSimilarityColor(result.similarity)}>
                      {Math.round(result.similarity * 100)}% match
                    </Badge>
                  </div>
                  
                  <p className="text-gray-700 mb-3">{result.snippet}</p>
                  
                  {result.metadata && Object.keys(result.metadata).length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(result.metadata).map(([key, value]) => (
                        <span 
                          key={key}
                          className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded"
                        >
                          {key}: {String(value)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {query && results.length === 0 && !isLoading && (
        <Card>
          <CardContent className="text-center py-8 text-gray-500">
            No results found for "{query}"
            <br />
            <span className="text-sm">Try adjusting your search terms or lowering the similarity threshold</span>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default VectorSearch;