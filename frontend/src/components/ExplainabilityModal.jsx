import React from 'react';
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    Typography,
    Box,
    Chip,
    Divider,
    LinearProgress,
    Accordion,
    AccordionSummary,
    AccordionDetails,
    Stepper,
    Step,
    StepLabel,
    StepContent,
    IconButton,
} from '@mui/material';
import {
    Close as CloseIcon,
    ExpandMore as ExpandIcon,
    Diamond as DiamondIcon,
    Timeline as TimelineIcon,
    Verified as VerifiedIcon,
    Description as SourceIcon,
    BubbleChart as GraphIcon,
} from '@mui/icons-material';

function ExplainabilityModal({ open, data, onClose }) {
    if (!data) return null;

    const summary = data.summary || {};
    const entities = data.entities || data.identified_entities || [];
    const steps = data.reasoning_steps || data.reasoning_trace || [];
    const confidence = data.confidence || data.confidence_breakdown || {};
    const sources = data.sources || data.sources_cited || [];
    const graphData = data.graph_data || data.graph_visualization || {};

    const getConfidenceColor = (level) => {
        switch (level) {
            case 'high': return '#22c55e';
            case 'moderate': return '#eab308';
            case 'low': return '#f97316';
            default: return '#6b7280';
        }
    };

    return (
        <Dialog
            open={open}
            onClose={onClose}
            maxWidth="md"
            fullWidth
            PaperProps={{
                sx: {
                    bgcolor: 'background.paper',
                    backgroundImage: 'linear-gradient(135deg, rgba(139, 92, 246, 0.03) 0%, rgba(6, 182, 212, 0.03) 100%)',
                },
            }}
        >
            <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <DiamondIcon color="primary" />
                    <Typography variant="h6" sx={{ fontWeight: 600 }}>
                        Why This Answer?
                    </Typography>
                </Box>
                <IconButton onClick={onClose} size="small">
                    <CloseIcon />
                </IconButton>
            </DialogTitle>

            <DialogContent dividers>
                {/* Summary Card */}
                {summary.message && (
                    <Box
                        sx={{
                            p: 2,
                            mb: 3,
                            borderRadius: 2,
                            bgcolor: `${getConfidenceColor(summary.color || confidence.level)}20`,
                            border: `1px solid ${getConfidenceColor(summary.color || confidence.level)}40`,
                        }}
                    >
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                            <VerifiedIcon sx={{ color: getConfidenceColor(summary.color || confidence.level) }} />
                            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                                {summary.status?.replace('_', ' ').toUpperCase() || 'RESULT'}
                            </Typography>
                        </Box>
                        <Typography variant="body2" color="text.secondary">
                            {summary.message}
                        </Typography>
                        {summary.quick_stats && (
                            <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
                                <Chip
                                    size="small"
                                    label={`${summary.quick_stats.entities_found} entities`}
                                    variant="outlined"
                                />
                                <Chip
                                    size="small"
                                    label={`${summary.quick_stats.reasoning_paths} paths`}
                                    variant="outlined"
                                />
                                <Chip
                                    size="small"
                                    label={summary.quick_stats.confidence_percent}
                                    sx={{ bgcolor: `${getConfidenceColor(confidence.level)}40` }}
                                />
                            </Box>
                        )}
                    </Box>
                )}

                {/* Confidence Breakdown */}
                <Accordion defaultExpanded>
                    <AccordionSummary expandIcon={<ExpandIcon />}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                                📊 Confidence Breakdown
                            </Typography>
                            <Chip
                                size="small"
                                label={confidence.overall || confidence.overall_percent || 'N/A'}
                                sx={{
                                    bgcolor: getConfidenceColor(confidence.level),
                                    color: 'white',
                                    fontWeight: 600,
                                }}
                            />

                        </Box>
                    </AccordionSummary>
                    <AccordionDetails>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                            {confidence.message}
                        </Typography>

                        {(confidence.factors || []).map((factor, i) => (
                            <Box key={i} sx={{ mb: 2 }}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                                    <Typography variant="body2">{factor.name}</Typography>
                                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                        {factor.percent}
                                    </Typography>
                                </Box>
                                <LinearProgress
                                    variant="determinate"
                                    value={factor.score * 100}
                                    sx={{
                                        height: 6,
                                        borderRadius: 3,
                                        bgcolor: 'background.paper',
                                    }}
                                />
                                <Typography variant="caption" color="text.secondary">
                                    {factor.description}
                                </Typography>
                            </Box>
                        ))}

                        {/* Fallback if no factors - use RAG metrics */}
                        {!confidence.factors && (
                            <Box>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                    <Typography variant="body2">Domain Relevance</Typography>
                                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                        {confidence.domain_relevance || 'N/A'}
                                    </Typography>
                                </Box>
                                <LinearProgress
                                    variant="determinate"
                                    value={parseFloat(confidence.domain_relevance) || 0}
                                    sx={{ height: 6, borderRadius: 3, mb: 2 }}
                                />

                                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                    <Typography variant="body2">Retrieval Quality</Typography>
                                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                        {confidence.retrieval_quality || 'N/A'}
                                    </Typography>
                                </Box>
                                <LinearProgress
                                    variant="determinate"
                                    value={parseFloat(confidence.retrieval_quality) || 0}
                                    color="secondary"
                                    sx={{ height: 6, borderRadius: 3, mb: 2 }}
                                />

                                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                    <Typography variant="body2">Faithfulness</Typography>
                                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                        {confidence.faithfulness || 'N/A'}
                                    </Typography>
                                </Box>
                                <LinearProgress
                                    variant="determinate"
                                    value={parseFloat(confidence.faithfulness) || 0}
                                    color="success"
                                    sx={{ height: 6, borderRadius: 3, mb: 2 }}
                                />

                                {confidence.claims_supported && (
                                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                        <Typography variant="body2">Claims Supported</Typography>
                                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                            {confidence.claims_supported}
                                        </Typography>
                                    </Box>
                                )}
                            </Box>
                        )}

                    </AccordionDetails>
                </Accordion>

                {/* Identified Entities */}
                {entities.length > 0 && (
                    <Accordion>
                        <AccordionSummary expandIcon={<ExpandIcon />}>
                            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                                🏷️ Identified Entities ({entities.length})
                            </Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                                {entities.map((entity, i) => (
                                    <Chip
                                        key={i}
                                        label={`${entity.icon || '📌'} ${entity.name}`}
                                        variant="outlined"
                                        size="small"
                                        sx={{
                                            borderColor: 'primary.main',
                                            '&:hover': {
                                                bgcolor: 'rgba(139, 92, 246, 0.1)',
                                            },
                                        }}
                                    />
                                ))}
                            </Box>
                        </AccordionDetails>
                    </Accordion>
                )}

                {/* Reasoning Steps */}
                {steps.length > 0 && (
                    <Accordion>
                        <AccordionSummary expandIcon={<ExpandIcon />}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <TimelineIcon color="secondary" />
                                <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                                    Reasoning Trace ({steps.length} steps)
                                </Typography>
                            </Box>
                        </AccordionSummary>
                        <AccordionDetails>
                            <Stepper orientation="vertical">
                                {steps.map((step, i) => (
                                    <Step key={i} active expanded>
                                        <StepLabel
                                            StepIconComponent={() => (
                                                <Box
                                                    sx={{
                                                        width: 28,
                                                        height: 28,
                                                        borderRadius: '50%',
                                                        bgcolor: 'primary.main',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        justifyContent: 'center',
                                                        color: 'white',
                                                        fontSize: '0.8rem',
                                                        fontWeight: 600,
                                                    }}
                                                >
                                                    {step.icon || step.step_number || i + 1}
                                                </Box>
                                            )}
                                        >
                                            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                                                {step.action_display || step.action?.replace('_', ' ').toUpperCase()}
                                            </Typography>
                                        </StepLabel>
                                        <StepContent>
                                            <Typography variant="body2" color="text.secondary">
                                                {step.explanation}
                                            </Typography>
                                            {step.path_visualization && (
                                                <Box
                                                    sx={{
                                                        mt: 1,
                                                        p: 1,
                                                        bgcolor: 'background.paper',
                                                        borderRadius: 1,
                                                        fontFamily: 'monospace',
                                                        fontSize: '0.8rem',
                                                        overflowX: 'auto',
                                                    }}
                                                >
                                                    {step.path_visualization}
                                                </Box>
                                            )}
                                        </StepContent>
                                    </Step>
                                ))}
                            </Stepper>
                        </AccordionDetails>
                    </Accordion>
                )}

                {/* Graph Visualization */}
                {(graphData.nodes?.length > 0 || graphData.edges?.length > 0) && (
                    <Accordion>
                        <AccordionSummary expandIcon={<ExpandIcon />}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <GraphIcon color="secondary" />
                                <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                                    Knowledge Graph ({graphData.node_count || graphData.nodes?.length || 0} nodes)
                                </Typography>
                            </Box>
                        </AccordionSummary>
                        <AccordionDetails>
                            <Box
                                sx={{
                                    bgcolor: 'background.paper',
                                    borderRadius: 2,
                                    p: 2,
                                    minHeight: 200,
                                    display: 'flex',
                                    flexDirection: 'column',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                }}
                            >
                                {/* Simple node visualization */}
                                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, justifyContent: 'center' }}>
                                    {(graphData.nodes || []).slice(0, 15).map((node, i) => (
                                        <Chip
                                            key={i}
                                            label={node.label || node.id || node}
                                            sx={{
                                                bgcolor: node.color || (i === 0 ? 'primary.main' : 'secondary.main'),
                                                color: 'white',
                                            }}
                                        />
                                    ))}
                                </Box>
                                {(graphData.nodes?.length || 0) > 15 && (
                                    <Typography variant="caption" color="text.secondary" sx={{ mt: 2 }}>
                                        +{graphData.nodes.length - 15} more nodes
                                    </Typography>
                                )}

                                {/* Edges count */}
                                {graphData.edges?.length > 0 && (
                                    <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                                        {graphData.edges.length} relationships found
                                    </Typography>
                                )}
                            </Box>
                        </AccordionDetails>
                    </Accordion>
                )}

                {/* Sources */}
                {sources.length > 0 && (
                    <Accordion>
                        <AccordionSummary expandIcon={<ExpandIcon />}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <SourceIcon color="primary" />
                                <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                                    Sources ({sources.length})
                                </Typography>
                            </Box>
                        </AccordionSummary>
                        <AccordionDetails>
                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                                {sources.map((source, i) => (
                                    <Box
                                        key={i}
                                        sx={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: 1,
                                            p: 1,
                                            bgcolor: 'background.paper',
                                            borderRadius: 1,
                                        }}
                                    >
                                        <Typography>{source.icon || '📎'}</Typography>
                                        <Typography variant="body2">
                                            {source.citation || source}
                                        </Typography>
                                    </Box>
                                ))}
                            </Box>
                        </AccordionDetails>
                    </Accordion>
                )}
            </DialogContent>

            <DialogActions>
                <Button onClick={onClose} variant="contained">
                    Got It!
                </Button>
            </DialogActions>
        </Dialog>
    );
}

export default ExplainabilityModal;
