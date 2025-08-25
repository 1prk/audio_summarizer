import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { intelligenceApi, type NetworkNode, type NetworkEdge, type NetworkResponse, type EntityNeighborsResponse } from '../lib/api';

interface NetworkAnalysisProps {
  className?: string;
}

const NetworkAnalysis: React.FC<NetworkAnalysisProps> = ({ className }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [networkData, setNetworkData] = useState<NetworkResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [nodeDetails, setNodeDetails] = useState<EntityNeighborsResponse | null>(null);
  const [minCooccurrence, setMinCooccurrence] = useState(2);
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);

  const entityTypes = ['PERSON', 'ORG', 'PRODUCT', 'TECH', 'LOCATION', 'MISC'];
  
  const loadNetworkData = async () => {
    setLoading(true);
    try {
      const response = await intelligenceApi.getEntityNetwork({
        min_cooccurrence: minCooccurrence,
        types: selectedTypes.length > 0 ? selectedTypes : undefined
      });
      setNetworkData(response);
    } catch (error) {
      console.error('Failed to load network data:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadNodeDetails = async (nodeId: string) => {
    try {
      const response = await intelligenceApi.getEntityNeighbors(nodeId);
      setNodeDetails(response);
    } catch (error) {
      console.error('Failed to load node details:', error);
    }
  };

  useEffect(() => {
    loadNetworkData();
  }, [minCooccurrence, selectedTypes]);

  useEffect(() => {
    if (!networkData || !svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = 800;
    const height = 800;
    const margin = { top: 20, right: 20, bottom: 20, left: 20 };

    svg.attr('width', width).attr('height', height);

    const g = svg.append('g');

    // Create zoom behavior
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });

    svg.call(zoom);

    // Color scale for entity types
    const colorScale = d3.scaleOrdinal<string>()
      .domain(entityTypes)
      .range(['#3b82f6', '#10b981', '#8b5cf6', '#f59e0b', '#ef4444', '#6b7280']);

    // Create force simulation
    const simulation = d3.forceSimulation<NetworkNode>(networkData.nodes)
      .force('link', d3.forceLink<NetworkNode, NetworkEdge>(networkData.edges)
        .id((d) => d.id)
        .distance(d => Math.max(50, 200 / Math.sqrt(d.weight)))
        .strength(d => Math.min(1, d.weight / 10))
      )
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(d => Math.max(15, Math.sqrt(d.connections) * 3)));

    // Create links
    const link = g.append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(networkData.edges)
      .enter()
      .append('line')
      .attr('stroke', '#999')
      .attr('stroke-opacity', d => Math.min(1, d.confidence + 0.3))
      .attr('stroke-width', d => Math.max(1, Math.sqrt(d.weight)));

    // Create nodes
    const node = g.append('g')
      .attr('class', 'nodes')
      .selectAll('circle')
      .data(networkData.nodes)
      .enter()
      .append('circle')
      .attr('r', d => Math.max(8, Math.sqrt(d.connections) * 3))
      .attr('fill', d => colorScale(d.type))
      .attr('stroke', '#fff')
      .attr('stroke-width', 2)
      .style('cursor', 'pointer')
      .call(d3.drag<SVGCircleElement, NetworkNode>()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x;
          d.fy = d.y;
        })
        .on('drag', (event, d) => {
          d.fx = event.x;
          d.fy = event.y;
        })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        })
      );

    // Add labels
    const label = g.append('g')
      .attr('class', 'labels')
      .selectAll('text')
      .data(networkData.nodes)
      .enter()
      .append('text')
      .text(d => d.canonical_name || d.name)
      .attr('font-size', d => Math.max(10, Math.sqrt(d.connections) * 2))
      .attr('dx', d => Math.max(8, Math.sqrt(d.connections) * 3) + 5)
      .attr('dy', '.35em')
      .style('pointer-events', 'none')
      .style('fill', '#374151');

    // Add click handlers
    node.on('click', (event, d) => {
      setSelectedNode(d.id);
      loadNodeDetails(d.id);
      
      // Highlight connected nodes
      const connectedNodes = new Set<string>();
      networkData.edges.forEach(edge => {
        if (edge.source === d.id) connectedNodes.add(edge.target);
        if (edge.target === d.id) connectedNodes.add(edge.source);
      });
      
      node.style('opacity', n => n.id === d.id || connectedNodes.has(n.id) ? 1 : 0.3);
      link.style('opacity', l => l.source === d.id || l.target === d.id ? 1 : 0.1);
      label.style('opacity', n => n.id === d.id || connectedNodes.has(n.id) ? 1 : 0.3);
    });

    // Add double-click to reset
    svg.on('dblclick', () => {
      node.style('opacity', 1);
      link.style('opacity', 1);
      label.style('opacity', 1);
      setSelectedNode(null);
      setNodeDetails(null);
    });

    // Update positions on simulation tick
    simulation.on('tick', () => {
      link
        .attr('x1', d => (d.source as any).x)
        .attr('y1', d => (d.source as any).y)
        .attr('x2', d => (d.target as any).x)
        .attr('y2', d => (d.target as any).y);

      node
        .attr('cx', d => (d as any).x)
        .attr('cy', d => (d as any).y);

      label
        .attr('x', d => (d as any).x)
        .attr('y', d => (d as any).y);
    });

  }, [networkData]);

  const toggleEntityType = (type: string) => {
    if (selectedTypes.includes(type)) {
      setSelectedTypes(selectedTypes.filter(t => t !== type));
    } else {
      setSelectedTypes([...selectedTypes, type]);
    }
  };

  return (
    <div className={`space-y-4 ${className}`}>
      <Card>
        <CardHeader>
          <CardTitle>Entity Network Analysis</CardTitle>
          <div className="flex flex-wrap gap-4 items-center">
            <div className="flex items-center gap-2">
              <span className="text-sm">Min Co-occurrence:</span>
              <Input
                type="number"
                min="1"
                max="10"
                value={minCooccurrence}
                onChange={(e) => setMinCooccurrence(parseInt(e.target.value) || 2)}
                className="w-20"
              />
            </div>
            <div className="flex flex-wrap gap-2">
              {entityTypes.map(type => (
                <Badge
                  key={type}
                  variant={selectedTypes.includes(type) ? 'default' : 'outline'}
                  className="cursor-pointer"
                  onClick={() => toggleEntityType(type)}
                >
                  {type}
                </Badge>
              ))}
            </div>
            <Button 
              onClick={() => setSelectedTypes([])}
              variant="outline"
              size="sm"
            >
              Clear Filters
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <div className="flex-1">
              {loading ? (
                <div className="flex items-center justify-center h-96">
                  <div className="text-gray-500">Loading network visualization...</div>
                </div>
              ) : networkData ? (
                <div className="border rounded-lg overflow-hidden">
                  <svg ref={svgRef} className="w-full h-96" />
                  <div className="p-4 bg-gray-50 text-sm text-gray-600">
                    <div className="flex justify-between">
                      <span>{networkData.stats.total_nodes} entities</span>
                      <span>{networkData.stats.total_edges} connections</span>
                      <span>Min co-occurrence: {networkData.stats.min_cooccurrence_threshold}</span>
                    </div>
                    <div className="mt-2 text-xs">
                      Click nodes to explore connections • Double-click to reset • Drag to reposition
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-96 text-gray-500">
                  No network data available
                </div>
              )}
            </div>
            
            {/* Node details panel */}
            {selectedNode && networkData && (
              <div className="w-80 space-y-4">
                {(() => {
                  const node = networkData.nodes.find(n => n.id === selectedNode);
                  if (!node) return null;
                  
                  return (
                    <>
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-lg">
                            {node.canonical_name || node.name}
                          </CardTitle>
                          <div className="flex gap-2 flex-wrap">
                            <Badge variant="outline">{node.type}</Badge>
                            <Badge variant="secondary">{node.total_mentions} mentions</Badge>
                            <Badge variant="secondary">{node.connections} connections</Badge>
                          </div>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-4">
                            {/* Video appearances */}
                            {node.video_titles.length > 0 && (
                              <div>
                                <h4 className="font-medium mb-2">Appears in ({node.video_titles.length} videos)</h4>
                                <div className="max-h-32 overflow-y-auto space-y-1">
                                  {node.video_titles.map((title, idx) => (
                                    <div key={idx} className="text-sm text-gray-600 p-2 bg-gray-50 rounded">
                                      {title.length > 50 ? `${title.substring(0, 50)}...` : title}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            
                            {/* Connected entities from neighbors API */}
                            {nodeDetails && nodeDetails.entity.id === selectedNode && (
                              <div>
                                <h4 className="font-medium mb-2">Connected Entities ({nodeDetails.neighbors.length})</h4>
                                <div className="max-h-64 overflow-y-auto space-y-2">
                                  {nodeDetails.neighbors.map(neighbor => (
                                    <div key={neighbor.id} className="p-2 border rounded">
                                      <div className="flex items-center justify-between">
                                        <span className="font-medium">{neighbor.name}</span>
                                        <Badge variant="outline" className="text-xs">{neighbor.type}</Badge>
                                      </div>
                                      <div className="text-sm text-gray-600 mt-1">
                                        Co-occurs {neighbor.cooccurrence_count} time{neighbor.cooccurrence_count !== 1 ? 's' : ''}
                                      </div>
                                      {neighbor.shared_videos.length > 0 && (
                                        <div className="text-xs text-gray-500 mt-1">
                                          In: {neighbor.shared_videos.slice(0, 2).join(', ')}
                                          {neighbor.shared_videos.length > 2 && ` +${neighbor.shared_videos.length - 2} more`}
                                        </div>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </CardContent>
                      </Card>
                    </>
                  );
                })()}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default NetworkAnalysis;