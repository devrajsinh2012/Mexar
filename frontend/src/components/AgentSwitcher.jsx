
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Box,
    FormControl,
    Select,
    MenuItem,
    Typography,
    Chip,
    Avatar,
    IconButton,
    Tooltip
} from '@mui/material';
import {
    Diamond as DiamondIcon,
    SwapHoriz as SwitchIcon,
    Add as AddIcon
} from '@mui/icons-material';
import { useAgents } from '../contexts/AgentContext';

const AgentSwitcher = ({ currentAgentName, onSwitch }) => {
    const navigate = useNavigate();
    const { agents, loading } = useAgents();

    // Filter only ready agents
    const readyAgents = agents.filter(a => a.status === 'ready');

    const handleChange = (event) => {
        const newAgentName = event.target.value;
        if (newAgentName === '__create__') {
            navigate('/create');
        } else if (newAgentName !== currentAgentName) {
            if (onSwitch) {
                onSwitch(newAgentName);
            } else {
                navigate(`/chat/${newAgentName}`);
            }
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'ready': return 'success';
            case 'failed': return 'error';
            case 'compiling': return 'warning';
            default: return 'default';
        }
    };

    if (loading) {
        return null;
    }

    return (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Tooltip title="Switch Agent">
                <SwitchIcon sx={{ color: 'text.secondary' }} />
            </Tooltip>

            <FormControl size="small" sx={{ minWidth: 200 }}>
                <Select
                    value={readyAgents.some(a => a.name === currentAgentName) ? currentAgentName : ''}
                    onChange={handleChange}
                    displayEmpty
                    renderValue={(selected) => {
                        if (!selected) {
                            return <Typography variant="body2">{currentAgentName || 'Select Agent'}</Typography>;
                        }
                        return selected.replace(/_/g, ' ');
                    }}
                    sx={{
                        bgcolor: 'rgba(255,255,255,0.05)',
                        '& .MuiSelect-select': {
                            display: 'flex',
                            alignItems: 'center',
                            gap: 1
                        }
                    }}
                >
                    {readyAgents.map((agent) => (
                        <MenuItem key={agent.name} value={agent.name}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Avatar sx={{ width: 24, height: 24, bgcolor: 'primary.main' }}>
                                    <DiamondIcon sx={{ fontSize: 14 }} />
                                </Avatar>
                                <Typography variant="body2">
                                    {agent.name.replace(/_/g, ' ')}
                                </Typography>
                                <Chip
                                    label={agent.status}
                                    size="small"
                                    color={getStatusColor(agent.status)}
                                    sx={{ height: 18, fontSize: '0.65rem' }}
                                />
                            </Box>
                        </MenuItem>
                    ))}

                    <MenuItem value="__create__">
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'primary.main' }}>
                            <AddIcon sx={{ fontSize: 20 }} />
                            <Typography variant="body2">Create New Agent</Typography>
                        </Box>
                    </MenuItem>
                </Select>
            </FormControl>
        </Box>
    );
};

export default AgentSwitcher;
