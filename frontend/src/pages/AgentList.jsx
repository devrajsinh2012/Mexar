import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
    Box,
    Typography,
    Button,
    Card,
    CardContent,
    Grid,
    IconButton,
    Chip,
    CircularProgress,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Alert,
    Tooltip,
    Container
} from '@mui/material';
import {
    Add as AddIcon,
    Chat as ChatIcon,
    Delete as DeleteIcon,
    Storage as StorageIcon,
    Timeline as TimelineIcon,
    Logout as LogoutIcon,
    Diamond as DiamondIcon
} from '@mui/icons-material';
import { listAgents, deleteAgent } from '../api/client';

function AgentList() {
    const navigate = useNavigate();
    const { logout } = useAuth();
    const [agents, setAgents] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [deleteDialog, setDeleteDialog] = useState({ open: false, agent: null });
    const [deleting, setDeleting] = useState(false);

    useEffect(() => {
        loadAgents();
    }, []);

    const loadAgents = async () => {
        try {
            setLoading(true);
            const response = await listAgents();
            setAgents(response.agents || []);
            setError(null);
        } catch (err) {
            setError('Failed to load agents. Make sure the backend is running.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async () => {
        if (!deleteDialog.agent) return;

        try {
            setDeleting(true);
            await deleteAgent(deleteDialog.agent.name);
            setDeleteDialog({ open: false, agent: null });
            loadAgents();
        } catch (err) {
            setError(`Failed to delete agent: ${err.message}`);
        } finally {
            setDeleting(false);
        }
    };

    const getDomainColor = (domain) => {
        const colors = {
            medical: '#ef4444',
            legal: '#3b82f6',
            cooking: '#f59e0b',
            technology: '#22c55e',
            finance: '#8b5cf6',
            education: '#06b6d4',
        };
        return colors[domain?.toLowerCase()] || '#6b7280';
    };

    return (
        <Box className="fade-in" sx={{ pb: 4 }}>
            {/* Glass Header - Consistent with Dashboard */}
            <Box
                sx={{
                    position: 'sticky',
                    top: 16,
                    mx: 2,
                    mb: 4,
                    zIndex: 100,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    p: 2,
                    bgcolor: 'rgba(26, 26, 46, 0.8)',
                    backdropFilter: 'blur(12px)',
                    borderRadius: 3,
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.2)',
                }}
            >
                <Box display="flex" alignItems="center" gap={2}>
                    <DiamondIcon color="primary" sx={{ fontSize: 32 }} />
                    <Box>
                        <Typography variant="h6" fontWeight="bold">MEXAR <span style={{ opacity: 0.7 }}>Ultimate</span></Typography>
                        <Typography variant="caption" color="text.secondary">
                            Agent Management
                        </Typography>
                    </Box>
                </Box>

                <Box display="flex" gap={2}>
                    <Button
                        variant="contained"
                        startIcon={<AddIcon />}
                        onClick={() => navigate('/create')}
                        sx={{
                            background: 'linear-gradient(135deg, #8b5cf6 0%, #06b6d4 100%)',
                            boxShadow: '0 4px 20px rgba(139, 92, 246, 0.3)',
                        }}
                    >
                        New Agent
                    </Button>
                    <Tooltip title="Logout">
                        <IconButton
                            onClick={() => { logout(); navigate('/login'); }}
                            color="error"
                            sx={{
                                bgcolor: 'rgba(239, 68, 68, 0.1)',
                                '&:hover': { bgcolor: 'rgba(239, 68, 68, 0.2)' }
                            }}
                        >
                            <LogoutIcon />
                        </IconButton>
                    </Tooltip>
                </Box>
            </Box>

            <Container maxWidth="lg">
                {/* Error Alert */}
                {error && (
                    <Alert severity="error" sx={{ mb: 4 }} onClose={() => setError(null)}>
                        {error}
                    </Alert>
                )}

                {/* Loading State */}
                {loading && (
                    <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
                        <CircularProgress />
                    </Box>
                )}

                {/* Empty State */}
                {!loading && agents.length === 0 && (
                    <Box
                        textAlign="center"
                        py={8}
                        sx={{
                            bgcolor: 'rgba(26, 26, 46, 0.6)',
                            backdropFilter: 'blur(12px)',
                            borderRadius: 4,
                            border: '1px dashed rgba(255, 255, 255, 0.1)',
                        }}
                    >
                        <DiamondIcon sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
                        <Typography variant="h5" gutterBottom fontWeight="bold">
                            No Agents Yet
                        </Typography>
                        <Typography color="text.secondary" sx={{ mb: 3 }}>
                            Create your first AI agent by uploading knowledge files.
                        </Typography>
                        <Button
                            variant="outlined"
                            startIcon={<AddIcon />}
                            onClick={() => navigate('/create')}
                        >
                            Create Agent
                        </Button>
                    </Box>
                )}

                {/* Agent Grid */}
                {!loading && agents.length > 0 && (
                    <Grid container spacing={3}>
                        {agents.map((agent) => (
                            <Grid item xs={12} sm={6} md={4} key={agent.name}>
                                <Card
                                    className="card-hover"
                                    sx={{
                                        height: '100%',
                                        display: 'flex',
                                        flexDirection: 'column',
                                        cursor: 'pointer',
                                        bgcolor: 'rgba(30, 30, 50, 0.6)',
                                        backdropFilter: 'blur(10px)',
                                        border: '1px solid rgba(255, 255, 255, 0.05)',
                                        '&:hover': {
                                            borderColor: 'primary.main',
                                            transform: 'translateY(-4px)',
                                            boxShadow: '0 12px 40px rgba(0,0,0,0.3)'
                                        },
                                        transition: 'all 0.3s ease'
                                    }}
                                    onClick={() => navigate(`/chat/${agent.name}`)}
                                >
                                    <CardContent sx={{ flexGrow: 1 }}>
                                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                                            <Chip
                                                label={agent.domain || 'General'}
                                                size="small"
                                                sx={{
                                                    backgroundColor: getDomainColor(agent.domain),
                                                    color: 'white',
                                                    fontWeight: 600,
                                                }}
                                            />
                                            <IconButton
                                                size="small"
                                                color="error"
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    setDeleteDialog({ open: true, agent });
                                                }}
                                            >
                                                <DeleteIcon fontSize="small" />
                                            </IconButton>
                                        </Box>

                                        <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, color: 'white' }}>
                                            {agent.name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                                        </Typography>

                                        <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
                                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                                <StorageIcon fontSize="small" color="primary" />
                                                <Typography variant="body2" color="text.secondary">
                                                    {agent.stats?.nodes_count || 0} nodes
                                                </Typography>
                                            </Box>
                                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                                <TimelineIcon fontSize="small" color="secondary" />
                                                <Typography variant="body2" color="text.secondary">
                                                    {agent.stats?.edges_count || 0} edges
                                                </Typography>
                                            </Box>
                                        </Box>

                                        {agent.created_at && (
                                            <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
                                                Created: {new Date(agent.created_at).toLocaleDateString()}
                                            </Typography>
                                        )}
                                    </CardContent>

                                    <Box sx={{ p: 2, pt: 0 }}>
                                        <Button
                                            fullWidth
                                            variant="contained"
                                            startIcon={<ChatIcon />}
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                navigate(`/chat/${agent.name}`);
                                            }}
                                            sx={{
                                                bgcolor: 'rgba(139, 92, 246, 0.2)',
                                                '&:hover': { bgcolor: 'primary.main' }
                                            }}
                                        >
                                            Chat
                                        </Button>
                                    </Box>
                                </Card>
                            </Grid>
                        ))}
                    </Grid>
                )}

                {/* Delete Confirmation Dialog */}
                <Dialog
                    open={deleteDialog.open}
                    onClose={() => setDeleteDialog({ open: false, agent: null })}
                    PaperProps={{
                        sx: {
                            bgcolor: '#1a1a2e',
                            color: 'white',
                            border: '1px solid rgba(255,255,255,0.1)'
                        }
                    }}
                >
                    <DialogTitle>Delete Agent</DialogTitle>
                    <DialogContent>
                        <Typography color="text.secondary">
                            Are you sure you want to delete <strong>{deleteDialog.agent?.name}</strong>? This action cannot be undone.
                        </Typography>
                    </DialogContent>
                    <DialogActions>
                        <Button onClick={() => setDeleteDialog({ open: false, agent: null })} disabled={deleting} sx={{ color: 'text.secondary' }}>
                            Cancel
                        </Button>
                        <Button onClick={handleDelete} color="error" variant="contained" disabled={deleting}>
                            {deleting ? <CircularProgress size={24} color="inherit" /> : 'Delete'}
                        </Button>
                    </DialogActions>
                </Dialog>
            </Container>
        </Box>
    );
}

export default AgentList;
