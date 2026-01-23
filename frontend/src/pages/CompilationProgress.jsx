import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    Box,
    Typography,
    Card,
    CardContent,
    LinearProgress,
    Button,
    Alert,
    Stepper,
    Step,
    StepLabel,
    StepContent,
    CircularProgress,
} from '@mui/material';
import {
    Check as CheckIcon,
    Error as ErrorIcon,
    Refresh as RefreshIcon,
} from '@mui/icons-material';
import client from '../api/client';

// Compilation steps
const COMPILATION_STEPS = [
    { label: 'Initializing', description: 'Setting up agent environment' },
    { label: 'Analyzing Prompt', description: 'Extracting domain and configuration' },
    { label: 'Compiling Knowledge', description: 'Building knowledge base' },
    { label: 'Generating Embeddings', description: 'Creating vector store' },
    { label: 'Finalizing', description: 'Saving agent artifacts' },
];

function CompilationProgress() {
    const { agentName } = useParams();
    const navigate = useNavigate();

    const [status, setStatus] = useState({
        status: 'starting',
        percentage: 0,
        current_step: 'Initializing...',
        error: null,
    });
    const [activeStep, setActiveStep] = useState(0);

    useEffect(() => {
        const pollStatus = async () => {
            try {
                // Use Phase 2 API
                const response = await client.get(`/api/compile/${agentName}/status`);
                const data = response.data;

                // Map to expected format
                const mappedStatus = {
                    status: data.agent_status === 'ready' ? 'complete' :
                        data.agent_status === 'failed' ? 'error' : 'processing',
                    percentage: data.job?.progress || 0,
                    current_step: data.job?.current_step || 'Processing...',
                    error: data.job?.error_message,
                    stats: null
                };

                setStatus(mappedStatus);

                // Update active step based on percentage
                if (mappedStatus.percentage < 20) setActiveStep(0);
                else if (mappedStatus.percentage < 40) setActiveStep(1);
                else if (mappedStatus.percentage < 60) setActiveStep(2);
                else if (mappedStatus.percentage < 90) setActiveStep(3);
                else setActiveStep(4);

                // Continue polling if not complete
                if (mappedStatus.status !== 'complete' && mappedStatus.status !== 'error') {
                    setTimeout(pollStatus, 2000);
                }
            } catch (err) {
                console.error('Failed to get status:', err);
                // Fallback to Phase 1 API
                try {
                    const fallbackResponse = await client.get(`/api/compile-status/${agentName}`);
                    setStatus(fallbackResponse.data);
                } catch {
                    setStatus({
                        status: 'error',
                        percentage: 0,
                        current_step: 'Failed to get status',
                        error: err.message,
                    });
                }
            }
        };

        pollStatus();
    }, [agentName]);

    const getStatusColor = () => {
        switch (status.status) {
            case 'complete': return 'success';
            case 'error': return 'error';
            default: return 'primary';
        }
    };

    const handleContinue = () => {
        navigate(`/ready/${agentName}`);
    };

    const handleRetry = () => {
        navigate('/create');
    };

    return (
        <Box
            className="fade-in"
            sx={{
                maxWidth: 800,
                mx: 'auto',
                mt: 4,
            }}
        >
            {/* Header */}
            <Box sx={{ textAlign: 'center', mb: 4 }}>
                <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
                    {status.status === 'complete'
                        ? '🎉 Agent Ready!'
                        : status.status === 'error'
                            ? '❌ Compilation Failed'
                            : '⚙️ Compiling Agent'}
                </Typography>
                <Typography color="text.secondary" sx={{ fontWeight: 600, letterSpacing: '1px' }}>
                    MEXAR <span style={{ color: 'var(--primary)' }}>ULTIMATE</span> | {agentName.replace(/_/g, ' ').toUpperCase()}
                </Typography>
            </Box>

            {/* Progress Card */}
            <Card sx={{ mb: 4 }}>
                <CardContent>
                    {/* Progress Bar */}
                    <Box sx={{ mb: 3 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                            <Typography variant="body2" color="text.secondary">
                                {status.current_step}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                {status.percentage}%
                            </Typography>
                        </Box>
                        <LinearProgress
                            variant="determinate"
                            value={status.percentage}
                            color={getStatusColor()}
                            sx={{
                                height: 12,
                                borderRadius: 6,
                                backgroundColor: 'background.paper',
                                '& .MuiLinearProgress-bar': {
                                    borderRadius: 6,
                                    background: status.status === 'complete'
                                        ? 'linear-gradient(90deg, #22c55e 0%, #06b6d4 100%)'
                                        : status.status === 'error'
                                            ? '#ef4444'
                                            : 'linear-gradient(90deg, #8b5cf6 0%, #06b6d4 100%)',
                                },
                            }}
                        />
                    </Box>

                    {/* Status Steps */}
                    <Stepper activeStep={activeStep} orientation="vertical">
                        {COMPILATION_STEPS.map((step, index) => (
                            <Step key={step.label}>
                                <StepLabel
                                    optional={
                                        <Typography variant="caption" color="text.secondary">
                                            {step.description}
                                        </Typography>
                                    }
                                    StepIconComponent={() => {
                                        if (status.status === 'error' && index === activeStep) {
                                            return <ErrorIcon color="error" />;
                                        }
                                        if (index < activeStep || status.status === 'complete') {
                                            return <CheckIcon color="success" />;
                                        }
                                        if (index === activeStep) {
                                            return <CircularProgress size={24} />;
                                        }
                                        return (
                                            <Box
                                                sx={{
                                                    width: 24,
                                                    height: 24,
                                                    borderRadius: '50%',
                                                    border: '2px solid',
                                                    borderColor: 'divider',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                }}
                                            >
                                                <Typography variant="caption">{index + 1}</Typography>
                                            </Box>
                                        );
                                    }}
                                >
                                    {step.label}
                                </StepLabel>
                                <StepContent>
                                    {index === activeStep && status.status !== 'complete' && status.status !== 'error' && (
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                                            <CircularProgress size={16} />
                                            <Typography variant="body2" color="text.secondary">
                                                Processing...
                                            </Typography>
                                        </Box>
                                    )}
                                </StepContent>
                            </Step>
                        ))}
                    </Stepper>
                </CardContent>
            </Card>

            {/* Error Message */}
            {status.status === 'error' && (
                <Alert severity="error" sx={{ mb: 3 }}>
                    <Typography variant="subtitle2" gutterBottom>
                        Compilation Error
                    </Typography>
                    <Typography variant="body2">
                        {status.error || 'An unexpected error occurred during compilation.'}
                    </Typography>
                </Alert>
            )}

            {/* Statistics Preview (when complete) */}
            {status.status === 'complete' && status.stats && (
                <Card sx={{ mb: 3, borderColor: 'success.main', borderWidth: 2 }}>
                    <CardContent>
                        <Typography variant="h6" gutterBottom>
                            📊 Compilation Statistics
                        </Typography>
                        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 2 }}>
                            <Box>
                                <Typography variant="h4" color="primary.main" sx={{ fontWeight: 700 }}>
                                    {status.stats.nodes_count}
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                    Knowledge Nodes
                                </Typography>
                            </Box>
                            <Box>
                                <Typography variant="h4" color="secondary.main" sx={{ fontWeight: 700 }}>
                                    {status.stats.edges_count}
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                    Relationships
                                </Typography>
                            </Box>
                            <Box>
                                <Typography variant="h4" color="success.main" sx={{ fontWeight: 700 }}>
                                    Ready
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                    Status
                                </Typography>
                            </Box>
                        </Box>
                    </CardContent>
                </Card>
            )}

            {/* Action Buttons */}
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
                {status.status === 'complete' && (
                    <Button
                        variant="contained"
                        size="large"
                        onClick={handleContinue}
                        sx={{
                            px: 6,
                            py: 1.5,
                            background: 'linear-gradient(135deg, #22c55e 0%, #06b6d4 100%)',
                        }}
                    >
                        Continue to Chat
                    </Button>
                )}

                {status.status === 'error' && (
                    <>
                        <Button
                            variant="outlined"
                            onClick={() => navigate('/')}
                        >
                            Back to Agents
                        </Button>
                        <Button
                            variant="contained"
                            startIcon={<RefreshIcon />}
                            onClick={handleRetry}
                        >
                            Try Again
                        </Button>
                    </>
                )}

                {status.status === 'processing' && (
                    <Button
                        variant="text"
                        onClick={() => navigate('/dashboard')}
                        sx={{ color: 'text.secondary' }}
                    >
                        Go to Dashboard
                    </Button>
                )}
            </Box>

            {/* Tips while waiting */}
            {status.status !== 'complete' && status.status !== 'error' && (
                <Card sx={{ mt: 4, background: 'rgba(139, 92, 246, 0.1)' }}>
                    <CardContent>
                        <Typography variant="subtitle2" gutterBottom>
                            💡 Did you know?
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                            MEXAR uses a high-performance Vector Database architecture. The semantic search
                            context enables fast responses, while the retrieval mechanism provides explainable
                            reasoning paths for every answer.
                        </Typography>
                    </CardContent>
                </Card>
            )}
        </Box>
    );
}

export default CompilationProgress;
