import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    Box,
    Typography,
    Card,
    CardContent,
    Button,
    Grid,
    Chip,
    Alert,
    CircularProgress,
} from '@mui/material';
import {
    Chat as ChatIcon,
    ArrowBack as BackIcon,
    Storage as StorageIcon,
    Timeline as TimelineIcon,
    Diamond as DiamondIcon,
    Verified as VerifiedIcon,
} from '@mui/icons-material';
import { getAgent } from '../api/client';

function AgentReady() {
    const { agentName } = useParams();
    const navigate = useNavigate();

    const [agent, setAgent] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        loadAgent();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [agentName]);

    const loadAgent = async () => {
        try {
            setLoading(true);
            const response = await getAgent(agentName);
            setAgent(response);
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to load agent');
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
                <CircularProgress />
            </Box>
        );
    }

    if (error) {
        return (
            <Box sx={{ maxWidth: 600, mx: 'auto', mt: 4 }}>
                <Alert severity="error" sx={{ mb: 2 }}>
                    {error}
                </Alert>
                <Button variant="outlined" onClick={() => navigate('/')}>
                    Back to Agents
                </Button>
            </Box>
        );
    }

    const metadata = agent?.metadata || {};
    const stats = agent?.stats || {};
    const promptAnalysis = metadata?.prompt_analysis || {};

    return (
        <Box className="fade-in" sx={{ maxWidth: 900, mx: 'auto' }}>
            {/* Header */}
            <Box sx={{ mb: 4, textAlign: 'center' }}>
                <Box
                    sx={{
                        width: 80,
                        height: 80,
                        borderRadius: '50%',
                        background: 'linear-gradient(135deg, #22c55e 0%, #06b6d4 100%)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        mx: 'auto',
                        mb: 2,
                    }}
                >
                    <VerifiedIcon sx={{ fontSize: 40, color: 'white' }} />
                </Box>
                <Typography variant="h3" sx={{ fontWeight: 700, mb: 1 }}>
                    Agent Ready! 🎉
                </Typography>
                <Typography variant="h5" color="primary.main" sx={{ fontWeight: 600 }}>
                    {agentName.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                </Typography>
                <Chip
                    label={promptAnalysis?.domain?.toUpperCase() || 'GENERAL'}
                    sx={{
                        mt: 1,
                        background: 'linear-gradient(135deg, #8b5cf6 0%, #06b6d4 100%)',
                        color: 'white',
                        fontWeight: 600,
                    }}
                />
            </Box>

            {/* Stats Grid */}
            <Grid container spacing={3} sx={{ mb: 4 }}>
                <Grid item xs={12} sm={4}>
                    <Card sx={{ textAlign: 'center', height: '100%' }}>
                        <CardContent>
                            <StorageIcon sx={{ fontSize: 40, color: 'primary.main', mb: 1 }} />
                            <Typography variant="h3" sx={{ fontWeight: 700, color: 'primary.main' }}>
                                {agent?.entity_count || agent?.chunk_count || 0}
                            </Typography>
                            <Typography color="text.secondary">Vector Chunks</Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={4}>
                    <Card sx={{ textAlign: 'center', height: '100%' }}>
                        <CardContent>
                            <TimelineIcon sx={{ fontSize: 40, color: 'secondary.main', mb: 1 }} />
                            <Typography variant="h3" sx={{ fontWeight: 700, color: 'secondary.main' }}>
                                {stats.source_files || 0}
                            </Typography>
                            <Typography color="text.secondary">Processed Files</Typography>
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} sm={4}>
                    <Card sx={{ textAlign: 'center', height: '100%' }}>
                        <CardContent>
                            <DiamondIcon sx={{ fontSize: 40, color: 'success.main', mb: 1 }} />
                            <Typography variant="h3" sx={{ fontWeight: 700, color: 'success.main' }}>
                                Ready
                            </Typography>
                            <Typography color="text.secondary">Status</Typography>
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>

            {/* Agent Details */}
            <Card sx={{ mb: 4 }}>
                <CardContent>
                    <Typography variant="h6" gutterBottom>
                        Agent Configuration
                    </Typography>

                    <Grid container spacing={2}>
                        <Grid item xs={12} md={6}>
                            <Typography variant="caption" color="text.secondary">
                                PERSONALITY
                            </Typography>
                            <Typography variant="body1" sx={{ mb: 2 }}>
                                {promptAnalysis?.personality || 'Helpful and professional'}
                            </Typography>
                        </Grid>
                        <Grid item xs={12} md={6}>
                            <Typography variant="caption" color="text.secondary">
                                TONE
                            </Typography>
                            <Typography variant="body1" sx={{ mb: 2, textTransform: 'capitalize' }}>
                                {promptAnalysis?.tone || 'Professional'}
                            </Typography>
                        </Grid>
                        <Grid item xs={12}>
                            <Typography variant="caption" color="text.secondary">
                                CAPABILITIES
                            </Typography>
                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
                                {(promptAnalysis?.capabilities || ['Answer questions', 'Provide information']).map((cap, i) => (
                                    <Chip key={i} label={cap} size="small" variant="outlined" />
                                ))}
                            </Box>
                        </Grid>
                        <Grid item xs={12}>
                            <Typography variant="caption" color="text.secondary">
                                DOMAIN KEYWORDS
                            </Typography>
                            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
                                {(metadata?.domain_signature || promptAnalysis?.domain_keywords || [])
                                    .slice(0, 15)
                                    .map((kw, i) => (
                                        <Chip
                                            key={i}
                                            label={kw}
                                            size="small"
                                            sx={{
                                                bgcolor: 'rgba(139, 92, 246, 0.2)',
                                                fontSize: '0.75rem',
                                            }}
                                        />
                                    ))}
                            </Box>
                        </Grid>
                    </Grid>
                </CardContent>
            </Card>

            {/* Additional Info */}
            <Card sx={{ mb: 4, background: 'rgba(139, 92, 246, 0.05)' }}>
                <CardContent>
                    <Typography variant="h6" gutterBottom>
                        📊 Knowledge Base Summary
                    </Typography>
                    <Grid container spacing={2}>
                        <Grid item xs={6} sm={3}>
                            <Typography variant="caption" color="text.secondary">Source Files</Typography>
                            <Typography variant="h6">{stats.source_files || 0}</Typography>
                        </Grid>
                        <Grid item xs={6} sm={3}>
                            <Typography variant="caption" color="text.secondary">Total Entries</Typography>
                            <Typography variant="h6">{stats.total_entries || 0}</Typography>
                        </Grid>
                        <Grid item xs={6} sm={3}>
                            <Typography variant="caption" color="text.secondary">Context Window</Typography>
                            <Typography variant="h6">{stats.context_length ? (stats.context_length / 1000).toFixed(1) + 'K' : 'N/A'}</Typography>
                        </Grid>
                        <Grid item xs={6} sm={3}>
                            <Typography variant="caption" color="text.secondary">Est. Tokens</Typography>
                            <Typography variant="h6">{stats.context_tokens ? (stats.context_tokens / 1000).toFixed(1) + 'K' : 'N/A'}</Typography>
                        </Grid>
                    </Grid>
                </CardContent>
            </Card>

            {/* Action Buttons */}
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
                <Button
                    variant="outlined"
                    startIcon={<BackIcon />}
                    onClick={() => navigate('/')}
                >
                    Back to Agents
                </Button>
                <Button
                    variant="contained"
                    size="large"
                    startIcon={<ChatIcon />}
                    onClick={() => navigate(`/chat/${agentName}`)}
                    sx={{
                        px: 6,
                        py: 1.5,
                        background: 'linear-gradient(135deg, #8b5cf6 0%, #06b6d4 100%)',
                        '&:hover': {
                            background: 'linear-gradient(135deg, #a78bfa 0%, #22d3ee 100%)',
                        },
                    }}
                >
                    Start Chatting
                </Button>
            </Box>
        </Box>
    );
}

export default AgentReady;
