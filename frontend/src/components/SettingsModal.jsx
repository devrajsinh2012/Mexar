
import React, { useState, useEffect } from 'react';
import {
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    Button,
    FormControlLabel,
    Switch,
    Typography,
    Box,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    Alert
} from '@mui/material';
import { useAuth } from '../contexts/AuthContext';
import client from '../api/client';

const SettingsModal = ({ open, onClose }) => {
    const { user, refreshUser } = useAuth();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(false);

    // Default preferences
    const [preferences, setPreferences] = useState({
        tts_provider: 'elevenlabs',
        auto_play_tts: false
    });

    useEffect(() => {
        if (open && user?.preferences) {
            setPreferences(prev => ({
                ...prev,
                ...user.preferences
            }));
            setError(null);
            setSuccess(false);
        }
    }, [open, user]);

    const handleChange = (prop) => (event) => {
        const value = event.target.type === 'checkbox' ? event.target.checked : event.target.value;
        setPreferences(prev => ({ ...prev, [prop]: value }));
        setSuccess(false);
    };

    const handleSave = async () => {
        setLoading(true);
        setError(null);
        try {
            await client.put('/api/auth/preferences', preferences);
            // Refresh user data to get updated preferences
            await refreshUser();
            setSuccess(true);
            setTimeout(() => {
                if (open) onClose();
            }, 1000);
        } catch (err) {
            console.error('Failed to save settings:', err);
            setError('Failed to save settings. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog
            open={open}
            onClose={loading ? null : onClose}
            PaperProps={{
                sx: {
                    bgcolor: '#1E1E2E',
                    color: 'white',
                    minWidth: '400px',
                    border: '1px solid rgba(255,255,255,0.1)'
                }
            }}
        >
            <DialogTitle>User Settings</DialogTitle>
            <DialogContent>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, mt: 1 }}>
                    {error && <Alert severity="error">{error}</Alert>}
                    {success && <Alert severity="success">Settings saved successfully!</Alert>}

                    <Box>
                        <Typography variant="subtitle2" color="primary" gutterBottom>
                            Text-to-Speech (Voice)
                        </Typography>

                        <FormControl fullWidth margin="dense" variant="outlined">
                            <InputLabel sx={{ color: 'text.secondary' }}>TTS Provider</InputLabel>
                            <Select
                                value={preferences.tts_provider}
                                onChange={handleChange('tts_provider')}
                                label="TTS Provider"
                                sx={{
                                    color: 'white',
                                    '.MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.2)' },
                                    '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.4)' },
                                    '.MuiSvgIcon-root': { color: 'white' }
                                }}
                            >
                                <MenuItem value="elevenlabs">ElevenLabs (High Quality)</MenuItem>
                                <MenuItem value="web_speech">Web Browser (Free)</MenuItem>
                            </Select>
                        </FormControl>

                        <FormControlLabel
                            control={
                                <Switch
                                    checked={preferences.auto_play_tts}
                                    onChange={handleChange('auto_play_tts')}
                                    color="primary"
                                />
                            }
                            label={
                                <Box>
                                    <Typography variant="body1">Auto-play Responses</Typography>
                                    <Typography variant="caption" color="text.secondary">
                                        Automatically read out assistant messages
                                    </Typography>
                                </Box>
                            }
                            sx={{ mt: 2 }}
                        />
                    </Box>
                </Box>
            </DialogContent>
            <DialogActions sx={{ p: 2 }}>
                <Button
                    onClick={onClose}
                    disabled={loading}
                    sx={{ color: 'text.secondary' }}
                >
                    Cancel
                </Button>
                <Button
                    onClick={handleSave}
                    variant="contained"
                    disabled={loading}
                    sx={{ bgcolor: 'primary.main', '&:hover': { bgcolor: 'primary.dark' } }}
                >
                    {loading ? 'Saving...' : 'Save Changes'}
                </Button>
            </DialogActions>
        </Dialog>
    );
};

export default SettingsModal;
