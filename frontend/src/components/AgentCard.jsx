
import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Card,
    Typography,
    Box,
    Chip,
    IconButton,
    Button,
    Fade
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import ChatIcon from '@mui/icons-material/Chat';
import BuildIcon from '@mui/icons-material/Build';
import DiamondIcon from '@mui/icons-material/Diamond';
import { useAgents } from '../contexts/AgentContext';

const AgentCard = ({ agent }) => {
    const navigate = useNavigate();
    const { deleteAgent } = useAgents();

    const handleDelete = (e) => {
        e.stopPropagation();
        if (window.confirm(`Are you sure you want to delete ${agent.name}?`)) {
            deleteAgent(agent.name);
        }
    };

    const handleInteract = () => {
        if (agent.status === 'ready') {
            navigate(`/chat/${agent.name}`);
        } else {
            navigate(`/compile/${agent.name}`);
        }
    };

    return (
        <Card
            className="glass-card"
            sx={{
                height: '100%',
                display: 'flex',
                alignItems: 'stretch',
                flexDirection: 'column',
                p: 3,
                cursor: 'pointer',
                position: 'relative',
                overflow: 'hidden'
            }}
            onClick={handleInteract}
        >
            {/* Status Indicator */}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                <Box sx={{
                    width: 48, height: 48, borderRadius: '14px',
                    background: agent.status === 'ready'
                        ? 'linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(139, 92, 246, 0.1))'
                        : 'linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(245, 158, 11, 0.1))',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    border: '1px solid',
                    borderColor: agent.status === 'ready' ? 'rgba(139, 92, 246, 0.2)' : 'rgba(245, 158, 11, 0.2)'
                }}>
                    <DiamondIcon sx={{
                        color: agent.status === 'ready' ? '#a78bfa' : '#fbbf24',
                        fontSize: 28
                    }} />
                </Box>

                <Chip
                    label={agent.status.toUpperCase()}
                    size="small"
                    sx={{
                        borderRadius: '8px',
                        fontSize: '0.7rem',
                        fontWeight: 700,
                        bgcolor: agent.status === 'ready' ? 'rgba(34, 197, 94, 0.1)' : 'rgba(245, 158, 11, 0.1)',
                        color: agent.status === 'ready' ? '#22c55e' : '#fbbf24',
                        border: '1px solid',
                        borderColor: agent.status === 'ready' ? 'rgba(34, 197, 94, 0.2)' : 'rgba(245, 158, 11, 0.2)'
                    }}
                />
            </Box>

            <Typography variant="h6" fontWeight="bold" gutterBottom sx={{ mb: 0.5 }}>
                {agent.name.replace(/_/g, ' ')}
            </Typography>

            <Typography variant="body2" color="text.secondary" sx={{ mb: 3, flexGrow: 1 }}>
                Domain: {agent.domain || 'General'}
            </Typography>

            {/* Footer Stats & Actions */}
            <Box sx={{ pt: 2, borderTop: '1px solid rgba(255,255,255,0.05)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                    {agent.stats?.nodes_count || 0} ITEMS
                </Typography>

                <Box onClick={(e) => e.stopPropagation()}>
                    <IconButton
                        onClick={handleDelete}
                        size="small"
                        sx={{
                            color: 'text.secondary',
                            '&:hover': { color: '#ef4444', bgcolor: 'rgba(239, 68, 68, 0.1)' }
                        }}
                    >
                        <DeleteIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                        onClick={handleInteract}
                        size="small"
                        sx={{
                            ml: 1,
                            color: 'white',
                            bgcolor: 'var(--primary)',
                            '&:hover': { bgcolor: 'var(--primary-dark)' }
                        }}
                    >
                        {agent.status === 'ready' ? <ChatIcon fontSize="small" /> : <BuildIcon fontSize="small" />}
                    </IconButton>
                </Box>
            </Box>
        </Card>
    );
};

export default AgentCard;
