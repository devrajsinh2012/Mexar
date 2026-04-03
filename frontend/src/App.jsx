import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Box, Container } from '@mui/material';
import { AuthProvider } from './contexts/AuthContext';
import { AgentProvider } from './contexts/AgentContext';
import ProtectedRoute from './components/ProtectedRoute';

// Pages
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import AgentCreation from './pages/AgentCreation';
import CompilationProgress from './pages/CompilationProgress';
import AgentReady from './pages/AgentReady';
import Chat from './pages/Chat';
import AgentList from './pages/AgentList';
import Landing from './pages/Landing';

function App() {
    return (
        <AuthProvider>
            <AgentProvider>
                <Box
                    sx={{
                        minHeight: '100vh',
                        background: 'linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #0f0f1a 100%)',
                        position: 'relative',
                        overflow: 'hidden',
                    }}
                >
                    {/* Background decorative elements */}
                    <Box
                        sx={{
                            position: 'absolute',
                            top: '-20%',
                            right: '-10%',
                            width: '600px',
                            height: '600px',
                            borderRadius: '50%',
                            background: 'radial-gradient(circle, rgba(139, 92, 246, 0.1) 0%, transparent 70%)',
                            pointerEvents: 'none',
                        }}
                    />
                    <Box
                        sx={{
                            position: 'absolute',
                            bottom: '-20%',
                            left: '-10%',
                            width: '500px',
                            height: '500px',
                            borderRadius: '50%',
                            background: 'radial-gradient(circle, rgba(6, 182, 212, 0.1) 0%, transparent 70%)',
                            pointerEvents: 'none',
                        }}
                    />

                    {/* Main Content */}
                    <Box
                        sx={{
                            position: 'relative',
                            zIndex: 1,
                            minHeight: '100vh',
                        }}
                    >
                        <Routes>
                            {/* Public Routes */}
                            <Route path="/" element={<Landing />} />
                            <Route path="/login" element={<Login />} />
                            <Route path="/register" element={<Register />} />

                            {/* Protected Routes */}
                            <Route element={<ProtectedRoute />}>
                                <Route path="/dashboard" element={<Dashboard />} />
                                <Route path="/agents" element={<AgentList />} />
                                <Route path="/create" element={<AgentCreation />} />
                                <Route path="/compile/:agentName" element={<CompilationProgress />} />
                                <Route path="/ready/:agentName" element={<AgentReady />} />
                                <Route path="/chat/:agentName" element={<Chat />} />
                            </Route>

                            {/* Catch all */}
                            <Route path="*" element={<Navigate to="/" replace />} />
                        </Routes>
                    </Box>
                </Box>
            </AgentProvider>
        </AuthProvider>
    );
}

export default App;
