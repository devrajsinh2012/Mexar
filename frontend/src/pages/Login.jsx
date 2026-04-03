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
    Diamond as DiamondIcon
} from '@mui/icons-material';

const Login = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [rememberMe, setRememberMe] = useState(false);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const { login } = useAuth();
    const navigate = useNavigate();

    // Load remembered email on mount
    React.useEffect(() => {
        const savedEmail = localStorage.getItem('rememberedEmail');
        if (savedEmail) {
            setEmail(savedEmail);
            setRememberMe(true);
        }
    }, []);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            await login(email, password);
            // Save or remove email based on Remember Me
            if (rememberMe) {
                localStorage.setItem('rememberedEmail', email);
            } else {
                localStorage.removeItem('rememberedEmail');
            }
            navigate('/dashboard');
        } catch (err) {
            setError('Invalid email or password');
        } finally {
            setLoading(false);
        }
    };


    return (
        <Box sx={{ position: 'relative', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {/* Animated Background */}
            <div className="animated-bg">
                <div className="orb orb-1" />
                <div className="orb orb-2" />
                <div className="orb orb-3" />
            </div>

            <Container maxWidth="xs" sx={{ position: 'relative', zIndex: 10 }}>
                <Fade in timeout={800}>
                    <Box className="glass-card" sx={{ p: 5, textAlign: 'center' }}>

                        {/* Logo / Header */}
                        <Box sx={{ mb: 4 }}>
                            <Box sx={{
                                width: 60,
                                height: 60,
                                borderRadius: '20px',
                                background: 'linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                margin: '0 auto',
                                mb: 2,
                                boxShadow: '0 0 20px rgba(139, 92, 246, 0.4)'
                            }}>
                                <DiamondIcon sx={{ fontSize: '32px', color: 'white' }} />
                            </Box>
                            <Typography variant="h4" fontWeight="bold" className="text-gradient">
                                MEXAR Ultimate
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                                Enter your credentials to access the ultimate reasoning engine
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
                                        placeholder="••••••••"
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

                            {/* Remember Me & Forgot Password */}
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                                <Box
                                    sx={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}
                                    onClick={() => setRememberMe(!rememberMe)}
                                >
                                    <Box
                                        sx={{
                                            width: 18,
                                            height: 18,
                                            borderRadius: '4px',
                                            border: rememberMe ? 'none' : '2px solid rgba(255,255,255,0.3)',
                                            background: rememberMe ? 'linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%)' : 'transparent',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            mr: 1,
                                            transition: 'all 0.2s ease'
                                        }}
                                    >
                                        {rememberMe && (
                                            <Typography sx={{ color: 'white', fontSize: '12px', fontWeight: 'bold' }}>✓</Typography>
                                        )}
                                    </Box>
                                    <Typography variant="body2" sx={{ color: 'text.secondary', userSelect: 'none' }}>
                                        Remember me
                                    </Typography>
                                </Box>
                                <Link to="/forgot-password" style={{ color: 'var(--primary)', textDecoration: 'none', fontSize: '0.875rem' }}>
                                    Forgot password?
                                </Link>
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
                                    gap: '8px'
                                }}
                                disabled={loading}
                            >
                                {loading ? <CircularProgress size={24} color="inherit" /> : (
                                    <>
                                        Sign In <ArrowForward sx={{ fontSize: 20 }} />
                                    </>
                                )}
                            </button>
                        </form>

                        {/* Footer */}
                        <Box sx={{ mt: 4 }}>
                            <Typography variant="body2" color="text.secondary">
                                New here? {' '}
                                <Link to="/register" style={{ color: 'var(--primary)', textDecoration: 'none', fontWeight: 600 }}>
                                    Create an account
                                </Link>
                            </Typography>
                        </Box>
                    </Box>
                </Fade>
            </Container>
        </Box>
    );
};

export default Login;
