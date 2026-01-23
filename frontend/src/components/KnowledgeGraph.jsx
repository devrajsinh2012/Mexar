/**
 * KnowledgeGraph Component
 * D3.js-based force-directed graph visualization for agent knowledge.
 */

import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import {
    Box,
    Typography,
    Card,
    CardContent,
    CircularProgress,
    Alert,
    Chip,
    IconButton,
    Tooltip,
} from '@mui/material';
import {
    ZoomIn as ZoomInIcon,
    ZoomOut as ZoomOutIcon,
    CenterFocusStrong as CenterIcon,
} from '@mui/icons-material';
import { getAgentGraph } from '../api/client';

const KnowledgeGraph = ({ agentName, width = 800, height = 600 }) => {
    const svgRef = useRef(null);
    const containerRef = useRef(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [graphData, setGraphData] = useState(null);
    const [selectedNode, setSelectedNode] = useState(null);

    // Color scale for node types
    const colorScale = d3.scaleOrdinal(d3.schemeCategory10);

    useEffect(() => {
        loadGraphData();
    }, [agentName]);

    useEffect(() => {
        if (graphData && svgRef.current) {
            renderGraph();
        }
    }, [graphData]);

    const loadGraphData = async () => {
        try {
            setLoading(true);
            setError(null);
            const data = await getAgentGraph(agentName);
            setGraphData(data);
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to load knowledge graph');
        } finally {
            setLoading(false);
        }
    };

    const renderGraph = () => {
        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove();

        const { nodes, links } = graphData;

        if (!nodes || nodes.length === 0) {
            return;
        }

        // Create zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => {
                container.attr('transform', event.transform);
            });

        svg.call(zoom);

        // Create container for zoom
        const container = svg.append('g');

        // Create arrow markers for links
        svg.append('defs').append('marker')
            .attr('id', 'arrowhead')
            .attr('viewBox', '-0 -5 10 10')
            .attr('refX', 20)
            .attr('refY', 0)
            .attr('orient', 'auto')
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .append('path')
            .attr('d', 'M 0,-5 L 10,0 L 0,5')
            .attr('fill', '#666');

        // Create force simulation
        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links)
                .id(d => d.id)
                .distance(100))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(40));

        // Create links
        const link = container.append('g')
            .attr('class', 'links')
            .selectAll('line')
            .data(links)
            .enter()
            .append('line')
            .attr('stroke', '#666')
            .attr('stroke-opacity', 0.6)
            .attr('stroke-width', d => Math.sqrt(d.weight || 1))
            .attr('marker-end', 'url(#arrowhead)');

        // Create link labels
        const linkLabel = container.append('g')
            .attr('class', 'link-labels')
            .selectAll('text')
            .data(links)
            .enter()
            .append('text')
            .attr('font-size', '10px')
            .attr('fill', '#888')
            .attr('text-anchor', 'middle')
            .text(d => d.label || '');

        // Create nodes
        const node = container.append('g')
            .attr('class', 'nodes')
            .selectAll('g')
            .data(nodes)
            .enter()
            .append('g')
            .call(d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended));

        // Add circles to nodes
        node.append('circle')
            .attr('r', 15)
            .attr('fill', d => colorScale(d.type || d.group))
            .attr('stroke', '#fff')
            .attr('stroke-width', 2)
            .style('cursor', 'pointer')
            .on('click', (event, d) => {
                setSelectedNode(d);
            })
            .on('mouseover', function () {
                d3.select(this).attr('r', 20);
            })
            .on('mouseout', function () {
                d3.select(this).attr('r', 15);
            });

        // Add labels to nodes
        node.append('text')
            .attr('dx', 20)
            .attr('dy', 5)
            .attr('font-size', '12px')
            .attr('fill', '#fff')
            .text(d => d.label || d.id);

        // Update positions on tick
        simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            linkLabel
                .attr('x', d => (d.source.x + d.target.x) / 2)
                .attr('y', d => (d.source.y + d.target.y) / 2);

            node.attr('transform', d => `translate(${d.x},${d.y})`);
        });

        // Drag functions
        function dragstarted(event) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        }

        function dragged(event) {
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        }

        function dragended(event) {
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
        }

        // Store zoom for controls
        svgRef.current.zoomBehavior = zoom;
        svgRef.current.svgSelection = svg;
    };

    const handleZoomIn = () => {
        const svg = d3.select(svgRef.current);
        svg.transition().call(svgRef.current.zoomBehavior.scaleBy, 1.5);
    };

    const handleZoomOut = () => {
        const svg = d3.select(svgRef.current);
        svg.transition().call(svgRef.current.zoomBehavior.scaleBy, 0.67);
    };

    const handleCenter = () => {
        const svg = d3.select(svgRef.current);
        svg.transition().call(
            svgRef.current.zoomBehavior.transform,
            d3.zoomIdentity.translate(width / 2, height / 2).scale(1)
        );
    };

    if (loading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
                <CircularProgress />
            </Box>
        );
    }

    if (error) {
        return (
            <Alert severity="error" sx={{ m: 2 }}>
                {error}
            </Alert>
        );
    }

    return (
        <Card sx={{ m: 2 }}>
            <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h6">
                        🕸️ Knowledge Graph
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                        {graphData?.stats && (
                            <>
                                <Chip
                                    label={`${graphData.stats.node_count} nodes`}
                                    size="small"
                                    color="primary"
                                />
                                <Chip
                                    label={`${graphData.stats.link_count} links`}
                                    size="small"
                                    color="secondary"
                                />
                            </>
                        )}
                        <Tooltip title="Zoom In">
                            <IconButton onClick={handleZoomIn} size="small">
                                <ZoomInIcon />
                            </IconButton>
                        </Tooltip>
                        <Tooltip title="Zoom Out">
                            <IconButton onClick={handleZoomOut} size="small">
                                <ZoomOutIcon />
                            </IconButton>
                        </Tooltip>
                        <Tooltip title="Center">
                            <IconButton onClick={handleCenter} size="small">
                                <CenterIcon />
                            </IconButton>
                        </Tooltip>
                    </Box>
                </Box>

                <Box
                    ref={containerRef}
                    sx={{
                        bgcolor: 'rgba(0,0,0,0.3)',
                        borderRadius: 2,
                        overflow: 'hidden'
                    }}
                >
                    <svg
                        ref={svgRef}
                        width={width}
                        height={height}
                        style={{ display: 'block' }}
                    />
                </Box>

                {selectedNode && (
                    <Box sx={{ mt: 2, p: 2, bgcolor: 'rgba(139, 92, 246, 0.1)', borderRadius: 1 }}>
                        <Typography variant="subtitle2" color="primary">
                            Selected Node
                        </Typography>
                        <Typography variant="body2">
                            <strong>ID:</strong> {selectedNode.id}
                        </Typography>
                        <Typography variant="body2">
                            <strong>Label:</strong> {selectedNode.label}
                        </Typography>
                        <Typography variant="body2">
                            <strong>Type:</strong> {selectedNode.type || 'entity'}
                        </Typography>
                    </Box>
                )}
            </CardContent>
        </Card>
    );
};

export default KnowledgeGraph;
