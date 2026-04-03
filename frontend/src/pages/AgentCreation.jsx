
import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAgents } from '../contexts/AgentContext';
import client, { getPromptTemplates, analyzePrompt } from '../api/client';
import {
    Box,
    Typography,
    TextField,
    Button,
    Paper,
    CircularProgress,
    Alert,
    List,
    ListItem,
    ListItemIcon,
    ListItemText,
    IconButton,
    Chip,
    Grid,
    Card,
    CardContent,
    CardActionArea,
    Divider
} from '@mui/material';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import DeleteIcon from '@mui/icons-material/Delete';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import DiamondIcon from '@mui/icons-material/Diamond';

const AgentCreation = () => {
    const navigate = useNavigate();
    const { fetchAgents } = useAgents();
    const fileInputRef = useRef(null);

    const [name, setName] = useState('');
    const [prompt, setPrompt] = useState('');
    const [files, setFiles] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    // Prompt templates
    const [templates, setTemplates] = useState([]);
    const [selectedTemplate, setSelectedTemplate] = useState(null);

    // Prompt analysis
    const [analyzing, setAnalyzing] = useState(false);
    const [analysis, setAnalysis] = useState(null);

    // Load templates on mount
    useEffect(() => {
        loadTemplates();
    }, []);

    const loadTemplates = async () => {
        try {
            const response = await getPromptTemplates();
            if (response.templates) {
                setTemplates(response.templates);
            }
        } catch (err) {
            console.error('Failed to load templates:', err);
        }
    };

    const handleTemplateSelect = (template) => {
        setSelectedTemplate(template);
        setPrompt(template.template);
        // Auto-analyze when template is selected
        handleAnalyzePrompt(template.template);
    };

    const handleAnalyzePrompt = async (promptText = prompt) => {
        if (!promptText || promptText.length < 20) return;

        setAnalyzing(true);
        try {
            const response = await analyzePrompt(promptText);
            if (response.analysis) {
                setAnalysis(response.analysis);
                // Auto-suggest agent name if empty
                if (!name && response.analysis.suggested_name) {
                    setName(response.analysis.suggested_name.toLowerCase().replace(/\s+/g, '_'));
                }
            }
        } catch (err) {
            console.error('Failed to analyze prompt:', err);
        } finally {
            setAnalyzing(false);
        }
    };

    const handleFileSelect = (e) => {
        const selectedFiles = Array.from(e.target.files);
        setFiles(prev => [...prev, ...selectedFiles]);
    };

    const handleRemoveFile = (index) => {
        setFiles(prev => prev.filter((_, i) => i !== index));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            if (files.length === 0) {
                setError('Please upload at least one knowledge file');
                setLoading(false);
                return;
            }

            // Create FormData for file upload
            const formData = new FormData();
            formData.append('agent_name', name);
            formData.append('system_prompt', prompt);
            files.forEach(file => formData.append('files', file));

            // Call the Phase 2 compile API
            const response = await client.post('/api/compile/', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });

            // Refresh agents list and navigate
            await fetchAgents();
            navigate(`/compile/${response.data.agent_name}`);
        } catch (err) {
            const message = err.response?.data?.detail || 'Failed to create agent';
            setError(message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Box maxWidth="lg" mx="auto" mt={4} px={2}>
            <Grid container spacing={3}>
                {/* Left Column - Templates */}
                <Grid item xs={12} md={4}>
                    <Paper sx={{ p: 3, height: '100%' }}>
                        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <DiamondIcon color="primary" />
                            Prompt Templates
                        </Typography>
                        <Typography variant="body2" color="text.secondary" mb={2}>
                            Select a template to get started quickly
                        </Typography>

                        <Box sx={{ maxHeight: 400, overflowY: 'auto' }}>
                            {templates.map((template, index) => (
                                <Card
                                    key={index}
                                    sx={{
                                        mb: 1,
                                        border: selectedTemplate?.name === template.name ? 2 : 0,
                                        borderColor: 'primary.main'
                                    }}
                                >
                                    <CardActionArea onClick={() => handleTemplateSelect(template)}>
                                        <CardContent sx={{ py: 1.5 }}>
                                            <Box display="flex" justifyContent="space-between" alignItems="center">
                                                <Typography variant="subtitle2">{template.name}</Typography>
                                                {selectedTemplate?.name === template.name && (
                                                    <CheckCircleIcon color="primary" fontSize="small" />
                                                )}
                                            </Box>
                                            <Chip
                                                label={template.domain}
                                                size="small"
                                                sx={{ mt: 0.5 }}
                                            />
                                        </CardContent>
                                    </CardActionArea>
                                </Card>
                            ))}
                        </Box>
                    </Paper>
                </Grid>

                {/* Right Column - Form */}
                <Grid item xs={12} md={8}>
                    <Paper sx={{ p: 4 }}>
                        <Box display="flex" alignItems="center" gap={2} mb={3}>
                            <AutoFixHighIcon color="primary" sx={{ fontSize: 32 }} />
                            <Typography variant="h5" fontWeight="bold">
                                Create New Agent
                            </Typography>
                        </Box>

                        {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

                        <form onSubmit={handleSubmit}>
                            <TextField
                                fullWidth
                                label="Agent Name"
                                placeholder="e.g. medical_assistant"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                margin="normal"
                                required
                                helperText="Use lowercase letters and underscores"
                            />

                            <TextField
                                fullWidth
                                label="System Prompt"
                                placeholder="You are a helpful AI assistant specialized in..."
                                value={prompt}
                                onChange={(e) => setPrompt(e.target.value)}
                                onBlur={() => handleAnalyzePrompt()}
                                margin="normal"
                                required
                                multiline
                                rows={4}
                            />

                            {/* Analysis Results */}
                            {analyzing && (
                                <Box display="flex" alignItems="center" gap={1} mt={1}>
                                    <CircularProgress size={16} />
                                    <Typography variant="body2" color="text.secondary">
                                        Analyzing prompt...
                                    </Typography>
                                </Box>
                            )}

                            {analysis && !analyzing && (
                                <Alert severity="info" sx={{ mt: 2 }}>
                                    <Typography variant="subtitle2" gutterBottom>
                                        Detected Domain: <strong>{analysis.domain}</strong>
                                    </Typography>
                                    {analysis.capabilities && analysis.capabilities.length > 0 && (
                                        <Box display="flex" gap={0.5} flexWrap="wrap" mt={1}>
                                            {analysis.capabilities.slice(0, 5).map((cap, i) => (
                                                <Chip key={i} label={cap} size="small" variant="outlined" />
                                            ))}
                                        </Box>
                                    )}
                                </Alert>
                            )}

                            <Divider sx={{ my: 3 }} />

                            {/* File Upload Section */}
                            <Box>
                                <Typography variant="subtitle1" gutterBottom>
                                    Knowledge Files *
                                </Typography>

                                <input
                                    type="file"
                                    ref={fileInputRef}
                                    onChange={handleFileSelect}
                                    style={{ display: 'none' }}
                                    multiple
                                    accept=".csv,.pdf,.docx,.txt,.json"
                                />

                                <Button
                                    variant="outlined"
                                    startIcon={<CloudUploadIcon />}
                                    onClick={() => fileInputRef.current?.click()}
                                    sx={{ mb: 2 }}
                                >
                                    Upload Files
                                </Button>

                                <Box display="flex" gap={1} flexWrap="wrap" mb={1}>
                                    <Chip label="CSV" size="small" variant="outlined" />
                                    <Chip label="PDF" size="small" variant="outlined" />
                                    <Chip label="DOCX" size="small" variant="outlined" />
                                    <Chip label="TXT" size="small" variant="outlined" />
                                    <Chip label="JSON" size="small" variant="outlined" />
                                </Box>

                                {files.length > 0 && (
                                    <List dense>
                                        {files.map((file, index) => (
                                            <ListItem
                                                key={index}
                                                secondaryAction={
                                                    <IconButton
                                                        edge="end"
                                                        onClick={() => handleRemoveFile(index)}
                                                        size="small"
                                                    >
                                                        <DeleteIcon />
                                                    </IconButton>
                                                }
                                            >
                                                <ListItemIcon>
                                                    <InsertDriveFileIcon />
                                                </ListItemIcon>
                                                <ListItemText
                                                    primary={file.name}
                                                    secondary={`${(file.size / 1024).toFixed(1)} KB`}
                                                />
                                            </ListItem>
                                        ))}
                                    </List>
                                )}
                            </Box>

                            <Box mt={3} display="flex" gap={2}>
                                <Button
                                    variant="contained"
                                    type="submit"
                                    size="large"
                                    disabled={loading || !name || !prompt || files.length === 0}
                                >
                                    {loading ? <CircularProgress size={24} /> : 'Create & Compile Agent'}
                                </Button>
                                <Button
                                    variant="outlined"
                                    onClick={() => navigate('/dashboard')}
                                    disabled={loading}
                                >
                                    Cancel
                                </Button>
                            </Box>
                        </form>
                    </Paper>
                </Grid>
            </Grid>
        </Box>
    );
};

export default AgentCreation;
