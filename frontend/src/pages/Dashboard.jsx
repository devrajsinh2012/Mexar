import React, { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useAgents } from '../contexts/AgentContext';
import AgentCard from '../components/AgentCard'; // We'll update this next
import ProfileDropdown from '../components/ProfileDropdown';
import {
    Box,
    Typography,
    Container,
    Grid,
    CircularProgress,
    IconButton,
    Tooltip,
    Fade
} from '@mui/material';
import {
    Add as AddIcon,
    Logout as LogoutIcon,
    Dashboard as DashboardIcon,
    Storage as StorageIcon,
    Speed as SpeedIcon,
    Diamond as DiamondIcon,
    Description as DescriptionIcon
} from '@mui/icons-material';

const Dashboard = () => {
    const { user, logout } = useAuth();
    const { agents, loading, fetchAgents } = useAgents();
    const navigate = useNavigate();

    // Force refresh on mount
    React.useEffect(() => {
        fetchAgents();
    }, [fetchAgents]);

    // Calculate stats
    const stats = useMemo(() => {
        const totalAgents = agents.length;
        const totalDocs = agents.reduce((acc, curr) => acc + (curr.stats?.source_files || 0), 0);
        const activeAgents = agents.filter(a => a.status === 'ready').length;
        return { totalAgents, totalDocs, activeAgents };
    }, [agents]);

    return (
        <Box sx={{ position: 'relative', minHeight: '100vh', pb: 8 }}>
            {/* Animated Background */}
            <div className="animated-bg">
                <div className="orb orb-1" style={{ width: '800px', height: '800px', opacity: 0.2 }} />
                <div className="orb orb-2" style={{ width: '600px', height: '600px', opacity: 0.2 }} />
            </div>

            {/* Glass Header */}
            <Box
                className="glass-panel"
                sx={{
                    position: 'sticky',
                    top: 0,
                    zIndex: 100,
                    width: '100%',
                    backdropFilter: 'blur(12px)',
                    background: 'rgba(15, 15, 26, 0.8)',
                    borderBottom: '1px solid rgba(255,255,255,0.05)',
                    py: 2
                }}
            >
                <Container maxWidth="xl" sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Box display="flex" alignItems="center" gap={2}>
                        <Box sx={{
                            p: 1,
                            borderRadius: '12px',
                            background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(139, 92, 246, 0.1))',
                            border: '1px solid rgba(139, 92, 246, 0.2)'
                        }}>
                            <DiamondIcon color="primary" />
                        </Box>
                        <Box>
                            <Typography variant="h6" fontWeight="bold" sx={{ letterSpacing: '0.5px' }}>
                                MEXAR <span style={{ opacity: 0.5, fontWeight: 400 }}>Ultimate</span>
                            </Typography>
                        </Box>
                    </Box>

                    <Box display="flex" alignItems="center" gap={3}>
                        <ProfileDropdown />
                    </Box>
                </Container>
            </Box>



            <Container maxWidth="xl" sx={{ py: 4 }}>
                <Fade in timeout={800}>
                    <Box>
                        {/* Welcome Section */}
                        <Box sx={{ mb: 6, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: 2 }}>
                            <Box>
                                <Typography variant="h3" fontWeight="bold" sx={{ mb: 1 }} className="text-gradient">
                                    Your Agents
                                </Typography>
                                <Typography color="text.secondary" variant="h6" fontWeight="400">
                                    Manage and deploy your reasoning engines
                                </Typography>
                            </Box>

                            <button
                                className="btn-primary"
                                onClick={() => navigate('/create')}
                                style={{
                                    padding: '12px 24px',
                                    fontSize: '1rem',
                                    fontWeight: 600,
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '8px'
                                }}
                            >
                                <AddIcon /> New Agent
                            </button>
                        </Box>

                        {/* Stats Cards */}
                        <Grid container spacing={3} sx={{ mb: 6 }}>
                            <Grid item xs={12} sm={4}>
                                <Box className="glass-card" sx={{ p: 3, display: 'flex', alignItems: 'center', gap: 3 }}>
                                    <Box sx={{ p: 2, borderRadius: '16px', bgcolor: 'rgba(139, 92, 246, 0.1)', color: 'var(--primary)' }}>
                                        <DiamondIcon sx={{ fontSize: 32 }} />
                                    </Box>
                                    <Box>
                                        <Typography variant="h4" fontWeight="bold">{stats.totalAgents}</Typography>
                                        <Typography variant="body2" color="text.secondary">Total Agents</Typography>
                                    </Box>
                                </Box>
                            </Grid>
                            <Grid item xs={12} sm={4}>
                                <Box className="glass-card" sx={{ p: 3, display: 'flex', alignItems: 'center', gap: 3 }}>
                                    <Box sx={{ p: 2, borderRadius: '16px', bgcolor: 'rgba(6, 182, 212, 0.1)', color: 'var(--secondary)' }}>
                                        <SpeedIcon sx={{ fontSize: 32 }} />
                                    </Box>
                                    <Box>
                                        <Typography variant="h4" fontWeight="bold">{stats.activeAgents}</Typography>
                                        <Typography variant="body2" color="text.secondary">Active & Ready</Typography>
                                    </Box>
                                </Box>
                            </Grid>
                            <Grid item xs={12} sm={4}>
                                <Box className="glass-card" sx={{ p: 3, display: 'flex', alignItems: 'center', gap: 3 }}>
                                    <Box sx={{ p: 2, borderRadius: '16px', bgcolor: 'rgba(16, 185, 129, 0.1)', color: 'var(--success)' }}>
                                        <DescriptionIcon sx={{ fontSize: 32 }} />
                                    </Box>
                                    <Box>
                                        <Typography variant="h4" fontWeight="bold">{stats.totalDocs}</Typography>
                                        <Typography variant="body2" color="text.secondary">Total Documents</Typography>
                                    </Box>
                                </Box>
                            </Grid>
                        </Grid>

                        {/* Agents Grid */}
                        {loading ? (
                            <Box display="flex" justifyContent="center" mt={8}>
                                <CircularProgress color="secondary" />
                            </Box>
                        ) : (
                            <>
                                {agents.length === 0 ? (
                                    <Box
                                        className="glass-card"
                                        sx={{
                                            textAlign: 'center',
                                            py: 12,
                                            px: 4,
                                            borderStyle: 'dashed',
                                            borderColor: 'rgba(255,255,255,0.1)'
                                        }}
                                    >
                                        <Box sx={{
                                            width: 80, height: 80, borderRadius: '50%',
                                            bgcolor: 'rgba(255,255,255,0.05)',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            mx: 'auto', mb: 3
                                        }}>
                                            <AddIcon sx={{ fontSize: 40, opacity: 0.5 }} />
                                        </Box>
                                        <Typography variant="h5" gutterBottom fontWeight="bold">No agents yet</Typography>
                                        <Typography color="text.secondary" mb={4} maxWidth="sm" mx="auto">
                                            Create your first AI reasoning agent by uploading documents. MEXAR will build a knowledge graph and vector index automatically.
                                        </Typography>
                                        <button
                                            className="btn-secondary"
                                            onClick={() => navigate('/create')}
                                            style={{
                                                padding: '12px 32px',
                                                fontSize: '1rem',
                                                cursor: 'pointer',
                                                borderRadius: '30px'
                                            }}
                                        >
                                            Create Agent
                                        </button>
                                    </Box>
                                ) : (
                                    <Grid container spacing={3}>
                                        {agents.map((agent, index) => (
                                            <Grid item xs={12} sm={6} md={4} lg={3} key={agent.id}>
                                                <Fade in timeout={500 + (index * 100)}>
                                                    <div>
                                                        <AgentCard agent={agent} />
                                                    </div>
                                                </Fade>
                                            </Grid>
                                        ))}
                                    </Grid>
                                )}
                            </>
                        )}
                    </Box>
                </Fade>
            </Container>
        </Box >
    );
};

export default Dashboard;
