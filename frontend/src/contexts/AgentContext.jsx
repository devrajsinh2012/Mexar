
import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import client from '../api/client';
import { useAuth } from './AuthContext';

const AgentContext = createContext(null);

export const AgentProvider = ({ children }) => {
    const [agents, setAgents] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const { user } = useAuth();

    const fetchAgents = useCallback(async () => {
        if (!user) return;
        setLoading(true);
        try {
            const response = await client.get('/api/agents/');
            setAgents(response.data);
            setError(null);
        } catch (err) {
            console.error('Error fetching agents:', err);
            setError('Failed to load agents');
        } finally {
            setLoading(false);
        }
    }, [user]);

    useEffect(() => {
        if (user) {
            fetchAgents();
        } else {
            setAgents([]);
        }
    }, [user, fetchAgents]);

    const addAgent = async (name, systemPrompt) => {
        try {
            const response = await client.post('/api/agents/', {
                name,
                system_prompt: systemPrompt
            });
            setAgents(prev => [...prev, response.data]);
            return response.data;
        } catch (err) {
            throw err;
        }
    };

    const deleteAgent = async (name) => {
        try {
            await client.delete(`/api/agents/${name}`);
            setAgents(prev => prev.filter(a => a.name !== name));
        } catch (err) {
            throw err;
        }
    };

    return (
        <AgentContext.Provider value={{ agents, loading, error, fetchAgents, addAgent, deleteAgent }}>
            {children}
        </AgentContext.Provider>
    );
};

export const useAgents = () => {
    const context = useContext(AgentContext);
    if (!context) {
        throw new Error('useAgents must be used within an AgentProvider');
    }
    return context;
};
