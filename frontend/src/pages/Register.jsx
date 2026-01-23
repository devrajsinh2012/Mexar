import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
    Box,
    Typography,
    Container,
    IconButton,
    CircularProgress,
    Fade
} from '@mui/material';
import {
    Email as EmailIcon,
    Lock as LockIcon,
    Visibility,
    VisibilityOff,
    ArrowForward,
    Person as PersonIcon,
    Diamond as DiamondIcon
} from '@mui/icons-material';

const Register = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const { register } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            await register(email, password);
            navigate('/dashboard');
        } catch (err) {
            setError('Registration failed. Try a different email.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Box sx={{ position: 'relative', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {/* Animated Background */}
            <div className="animated-bg">
                <div className="orb orb-1" style={{ animationDelay: '-10s' }} />
                <div className="orb orb-2" style={{ animationDelay: '-15s' }} />
                <div className="orb orb-3" />
            </div>

            <Container maxWidth="xs" sx={{ position: 'relative', zIndex: 10 }}>
                <Fade in timeout={800}>
                    <Box className="glass-card" sx={{ p: 5, textAlign: 'center' }}>

                        {/* Header */}
                        <Box sx={{ mb: 4 }}>
                            <Box sx={{
                                width: 60,
                                height: 60,
                                borderRadius: '20px',
                                background: 'linear-gradient(135deg, var(--secondary) 0%, var(--secondary-dark) 100%)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                margin: '0 auto',
                                mb: 2,
                                boxShadow: '0 0 20px rgba(6, 182, 212, 0.4)'
                            }}>
                                <DiamondIcon sx={{ fontSize: 32, color: 'white' }} />
                            </Box>
                            <Typography variant="h4" fontWeight="bold" className="text-gradient">
                                MEXAR Ultimate
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                                Create your reasoning agents today
                            </Typography>
                        </Box>

                        {/* Form */}
                        <form onSubmit={handleSubmit}>
                            {/* Email Input */}
                            <Box sx={{ mb: 3, textAlign: 'left' }}>
                                <Typography variant="caption" sx={{ color: 'text.secondary', ml: 1, mb: 0.5, display: 'block' }}>
                                    EMAIL ADDRESS
                                </Typography>
                                <Box sx={{ position: 'relative' }}>
                                    <input
                                        type="email"
                                        className="premium-input"
                                        style={{ width: '100%', padding: '14px 16px 14px 44px', outline: 'none', fontSize: '1rem' }}
                                        placeholder="name@company.com"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        required
                                    />
                                    <EmailIcon sx={{ position: 'absolute', left: 14, top: 14, color: 'text.secondary', fontSize: 20 }} />
                                </Box>
                            </Box>

                            {/* Password Input */}
                            <Box sx={{ mb: 4, textAlign: 'left' }}>
                                <Typography variant="caption" sx={{ color: 'text.secondary', ml: 1, mb: 0.5, display: 'block' }}>
                                    PASSWORD
                                </Typography>
                                <Box sx={{ position: 'relative' }}>
                                    <input
                                        type={showPassword ? "text" : "password"}
                                        className="premium-input"
                                        style={{ width: '100%', padding: '14px 44px 14px 44px', outline: 'none', fontSize: '1rem' }}
                                        placeholder="Create a strong password"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        required
                                    />
                                    <LockIcon sx={{ position: 'absolute', left: 14, top: 14, color: 'text.secondary', fontSize: 20 }} />
                                    <IconButton
                                        onClick={() => setShowPassword(!showPassword)}
                                        sx={{ position: 'absolute', right: 8, top: 8, color: 'text.secondary' }}
                                        size="small"
                                    >
                                        {showPassword ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                                    </IconButton>
                                </Box>
                            </Box>

                            {/* Error Message */}
                            {error && (
                                <Fade in>
                                    <Typography color="error" variant="body2" sx={{ mb: 2, bgcolor: 'rgba(239, 68, 68, 0.1)', p: 1, borderRadius: 1 }}>
                                        ⚠️ {error}
                                    </Typography>
                                </Fade>
                            )}

                            {/* Submit Button */}
                            <button
                                type="submit"
                                className="btn-primary"
                                style={{
                                    width: '100%',
                                    padding: '16px',
                                    fontSize: '1rem',
                                    fontWeight: 600,
                                    cursor: loading ? 'not-allowed' : 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    gap: '8px',
                                    background: 'linear-gradient(135deg, var(--secondary) 0%, var(--secondary-dark) 100%)'
                                }}
                                disabled={loading}
                            >
                                {loading ? <CircularProgress size={24} color="inherit" /> : (
                                    <>
                                        Register <ArrowForward sx={{ fontSize: 20 }} />
                                    </>
                                )}
                            </button>
                        </form>

                        {/* Footer */}
                        <Box sx={{ mt: 4 }}>
                            <Typography variant="body2" color="text.secondary">
                                Already have an account? {' '}
                                <Link to="/login" style={{ color: 'var(--secondary)', textDecoration: 'none', fontWeight: 600 }}>
                                    Sign In
                                </Link>
                            </Typography>
                        </Box>
                    </Box>
                </Fade>
            </Container>
        </Box>
    );
};

export default Register;
