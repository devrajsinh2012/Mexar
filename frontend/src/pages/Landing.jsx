import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Typography, Button, Container, Grid, Card, CardContent, Fade } from '@mui/material';
import {
    Diamond as DiamondIcon,
    Psychology as BrainIcon,
    Speed as SpeedIcon,
    Security as SecurityIcon,
    AutoAwesome as AutoAwesomeIcon,
    ArrowForward as ArrowForwardIcon
} from '@mui/icons-material';

const Landing = () => {
    const navigate = useNavigate();

    const features = [
        {
            icon: <BrainIcon sx={{ fontSize: 40 }} />,
            title: 'RAG-Powered Reasoning',
            description: 'Advanced retrieval-augmented generation for accurate, context-aware responses'
        },
        {
            icon: <SpeedIcon sx={{ fontSize: 40 }} />,
            title: 'Lightning Fast',
            description: 'Optimized hybrid search with semantic and keyword matching for instant results'
        },
        {
            icon: <SecurityIcon sx={{ fontSize: 40 }} />,
            title: 'Source Attribution',
            description: 'Every answer includes citations and confidence scores for transparency'
        },
        {
            icon: <AutoAwesomeIcon sx={{ fontSize: 40 }} />,
            title: 'Multi-Agent System',
            description: 'Create specialized agents for different domains with custom knowledge bases'
        }
    ];

    return (
        <Box sx={{ position: 'relative', minHeight: '100vh', overflowY: 'auto' }}>
            {/* Animated Background */}
            <div className="animated-bg">
                <div className="orb orb-1" style={{ animationDelay: '-10s' }} />
                <div className="orb orb-2" style={{ animationDelay: '-15s' }} />
                <div className="orb orb-3" />
            </div>

            {/* Header */}
            <Box
                sx={{
                    position: 'relative',
                    zIndex: 10,
                    py: 3,
                    px: 4,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                }}
            >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Box sx={{
                        p: 1.5,
                        borderRadius: '12px',
                        background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(139, 92, 246, 0.1))',
                        border: '1px solid rgba(139, 92, 246, 0.2)'
                    }}>
                        <DiamondIcon sx={{ fontSize: 32, color: 'var(--primary)' }} />
                    </Box>
                    <Typography variant="h5" fontWeight="bold" sx={{ letterSpacing: '0.5px' }}>
                        MEXAR <span style={{ opacity: 0.5, fontWeight: 400 }}>Ultimate</span>
                    </Typography>
                </Box>
            </Box>

            {/* Hero Section */}
            <Container maxWidth="lg" sx={{ position: 'relative', zIndex: 10, py: { xs: 8, md: 12 } }}>
                <Fade in timeout={800}>
                    <Box sx={{ textAlign: 'center', mb: 8 }}>
                        <Typography
                            variant="h1"
                            sx={{
                                fontSize: { xs: '2.5rem', md: '4rem' },
                                fontWeight: 800,
                                mb: 3,
                                background: 'linear-gradient(135deg, #fff 0%, #a5b4fc 100%)',
                                WebkitBackgroundClip: 'text',
                                backgroundClip: 'text',
                                WebkitTextFillColor: 'transparent'
                            }}
                        >
                            Advanced AI Reasoning
                            <br />
                            Engine
                        </Typography>

                        <Typography
                            variant="h5"
                            color="text.secondary"
                            sx={{ mb: 5, maxWidth: '800px', mx: 'auto', lineHeight: 1.6 }}
                        >
                            Build intelligent agents powered by RAG technology. Upload your knowledge base and get accurate, cited answers in seconds.
                        </Typography>

                        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
                            <button
                                className="btn-primary"
                                onClick={() => navigate('/login')}
                                style={{
                                    padding: '16px 48px',
                                    fontSize: '1.1rem',
                                    fontWeight: 600,
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '12px'
                                }}
                            >
                                Get Started <ArrowForwardIcon />
                            </button>
                        </Box>
                    </Box>
                </Fade>

                {/* Features Grid */}
                <Grid container spacing={4} sx={{ mt: 8 }}>
                    {features.map((feature, index) => (
                        <Grid item xs={12} sm={6} md={3} key={index}>
                            <Fade in timeout={1000 + (index * 200)}>
                                <Card
                                    className="glass-card"
                                    sx={{
                                        height: '100%',
                                        p: 3,
                                        textAlign: 'center',
                                        transition: 'all 0.3s ease',
                                        '&:hover': {
                                            transform: 'translateY(-8px)',
                                            boxShadow: '0 20px 40px rgba(139, 92, 246, 0.2)'
                                        }
                                    }}
                                >
                                    <Box
                                        sx={{
                                            width: 80,
                                            height: 80,
                                            borderRadius: '20px',
                                            background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(6, 182, 212, 0.2))',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            mx: 'auto',
                                            mb: 3,
                                            color: 'var(--primary)'
                                        }}
                                    >
                                        {feature.icon}
                                    </Box>
                                    <Typography variant="h6" fontWeight="bold" gutterBottom>
                                        {feature.title}
                                    </Typography>
                                    <Typography variant="body2" color="text.secondary">
                                        {feature.description}
                                    </Typography>
                                </Card>
                            </Fade>
                        </Grid>
                    ))}
                </Grid>

                {/* CTA Section */}
                <Fade in timeout={1600}>
                    <Box
                        className="glass-card"
                        sx={{
                            mt: 12,
                            p: 6,
                            textAlign: 'center',
                            background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(6, 182, 212, 0.1))',
                            border: '1px solid rgba(139, 92, 246, 0.3)'
                        }}
                    >
                        <Typography variant="h3" fontWeight="bold" gutterBottom>
                            Ready to get started?
                        </Typography>
                        <Typography variant="h6" color="text.secondary" sx={{ mb: 4 }}>
                            Create your first AI agent in minutes
                        </Typography>
                        <button
                            className="btn-primary"
                            onClick={() => navigate('/register')}
                            style={{
                                padding: '16px 64px',
                                fontSize: '1.1rem',
                                fontWeight: 600,
                                cursor: 'pointer'
                            }}
                        >
                            Create Free Account
                        </button>
                    </Box>
                </Fade>
            </Container>

            {/* Footer */}
            <Box
                sx={{
                    position: 'relative',
                    zIndex: 10,
                    py: 4,
                    textAlign: 'center',
                    borderTop: '1px solid rgba(255, 255, 255, 0.05)'
                }}
            >
                <Typography variant="body2" color="text.secondary">
                    © 2026 MEXAR Ultimate. Advanced Multimodal AI Reasoning Engine.
                </Typography>
            </Box>
        </Box>
    );
};

export default Landing;
