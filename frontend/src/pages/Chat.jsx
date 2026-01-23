import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import client from '../api/client';
import {
    Box,
    Typography,
    TextField,
    IconButton,
    Avatar,
    CircularProgress,
    Button,
    Chip,
    Tooltip,
    Fade,
    Dialog
} from '@mui/material';
import {
    Send as SendIcon,
    ArrowBack as BackIcon,
    Mic as MicIcon,
    Image as ImageIcon,
    HelpOutline as WhyIcon,
    Diamond as DiamondIcon,
    VolumeUp as SpeakerIcon,
    Pause as PauseIcon,
    Stop as StopIcon,
    Close as CloseIcon,
    ZoomIn as ZoomInIcon
} from '@mui/icons-material';
import { sendMessage, sendMultimodalMessage, getAgent } from '../api/client';
import ExplainabilityModal from '../components/ExplainabilityModal';
import AgentSwitcher from '../components/AgentSwitcher';
import AudioRecorder from '../components/AudioRecorder';

function Chat() {
    const { agentName } = useParams();
    const navigate = useNavigate();
    const messagesEndRef = useRef(null);
    const fileInputRef = useRef(null);
    const audioInputRef = useRef(null);

    // State
    const { user } = useAuth();
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [agent, setAgent] = useState(null);
    const [selectedFile, setSelectedFile] = useState(null);
    const [selectedAudio, setSelectedAudio] = useState(null);
    const [imagePreview, setImagePreview] = useState(null);
    const [isRecording, setIsRecording] = useState(false);

    // TTS state for inline word highlighting
    const [activeTTSIndex, setActiveTTSIndex] = useState(-1);
    const [currentWordIndex, setCurrentWordIndex] = useState(-1);
    const [isTTSPlaying, setIsTTSPlaying] = useState(false);
    const utteranceRef = useRef(null);

    // Settings loaded from user profile
    const [autoPlayTTS, setAutoPlayTTS] = useState(false);
    const [ttsProvider, setTTSProvider] = useState('elevenlabs');

    const [explainabilityModal, setExplainabilityModal] = useState({ open: false, data: null });

    // Lightbox state
    const [lightboxOpen, setLightboxOpen] = useState(false);
    const [lightboxImage, setLightboxImage] = useState(null);

    // Load preferences
    useEffect(() => {
        if (user?.preferences) {
            if (user.preferences.auto_play_tts !== undefined) setAutoPlayTTS(user.preferences.auto_play_tts);
            if (user.preferences.tts_provider) setTTSProvider(user.preferences.tts_provider);
        }
    }, [user]);

    const loadAgent = React.useCallback(async () => {
        try {
            const response = await getAgent(agentName);
            setAgent(response);

            // Add welcome message
            const domain = response.metadata?.prompt_analysis?.domain || 'general';
            setMessages([{
                role: 'assistant',
                content: `Hello! I'm your **${domain}** assistant. I'm ready to answer questions based on my knowledge base.`,
                timestamp: new Date(),
            }]);
        } catch (err) {
            console.error('Failed to load agent:', err);
        }
    }, [agentName]);

    // Load agent info on mount
    useEffect(() => {
        loadAgent();
    }, [loadAgent]);

    // Consolidate scroll effects - with small delay for better timing
    useEffect(() => {
        const timer = setTimeout(() => {
            messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
        }, 100);
        return () => clearTimeout(timer);
    }, [messages, loading]);

    // TTS functions
    const handlePlayTTSInline = useCallback((msgIndex, text) => {
        // Stop any existing TTS
        if (window.speechSynthesis) {
            window.speechSynthesis.cancel();
        }

        if (!('speechSynthesis' in window)) {
            alert('Text-to-speech is not supported in your browser');
            return;
        }

        const utterance = new SpeechSynthesisUtterance(text);
        utteranceRef.current = utterance;
        utterance.rate = 1.0;
        utterance.pitch = 1.0;

        const words = text.split(/\s+/).filter(w => w.length > 0);

        utterance.onboundary = (event) => {
            if (event.name === 'word') {
                const charIndex = event.charIndex;
                let wordIdx = 0;
                let charCount = 0;

                for (let i = 0; i < words.length; i++) {
                    if (charCount >= charIndex) {
                        wordIdx = i;
                        break;
                    }
                    charCount += words[i].length + 1;
                }
                setCurrentWordIndex(wordIdx);
            }
        };

        utterance.onstart = () => {
            setActiveTTSIndex(msgIndex);
            setIsTTSPlaying(true);
            setCurrentWordIndex(0);
        };

        utterance.onend = () => {
            setActiveTTSIndex(-1);
            setIsTTSPlaying(false);
            setCurrentWordIndex(-1);
        };

        utterance.onerror = () => {
            setActiveTTSIndex(-1);
            setIsTTSPlaying(false);
            setCurrentWordIndex(-1);
        };

        window.speechSynthesis.speak(utterance);
    }, []);

    const handlePauseTTS = useCallback(() => {
        if (window.speechSynthesis) {
            window.speechSynthesis.pause();
            setIsTTSPlaying(false);
        }
    }, []);

    const handleResumeTTS = useCallback(() => {
        if (window.speechSynthesis) {
            window.speechSynthesis.resume();
            setIsTTSPlaying(true);
        }
    }, []);

    const handleStopTTS = useCallback(() => {
        if (window.speechSynthesis) {
            window.speechSynthesis.cancel();
        }
        setActiveTTSIndex(-1);
        setIsTTSPlaying(false);
        setCurrentWordIndex(-1);
    }, []);

    // Render message content with word highlighting
    const renderMessageContent = (content, msgIndex) => {
        const isThisMessagePlaying = activeTTSIndex === msgIndex;

        if (!isThisMessagePlaying || currentWordIndex < 0) {
            return <span dangerouslySetInnerHTML={{ __html: formatMarkdown(content) }} />;
        }

        // Render with word highlighting
        const words = content.split(/(\s+)/);
        let wordCount = 0;

        return (
            <span>
                {words.map((word, idx) => {
                    if (word.trim().length === 0) {
                        return <span key={idx}>{word}</span>;
                    }
                    const thisWordIndex = wordCount;
                    wordCount++;

                    const isCurrentWord = thisWordIndex === currentWordIndex;
                    const isPastWord = thisWordIndex < currentWordIndex;

                    // Handle markdown in word
                    const formattedWord = formatMarkdown(word);

                    return (
                        <span
                            key={idx}
                            style={{
                                backgroundColor: isCurrentWord
                                    ? 'rgba(139, 92, 246, 0.5)'
                                    : isPastWord
                                        ? 'rgba(139, 92, 246, 0.15)'
                                        : 'transparent',
                                borderRadius: '3px',
                                padding: isCurrentWord ? '1px 3px' : '0',
                                transition: 'background-color 0.1s ease'
                            }}
                            dangerouslySetInnerHTML={{ __html: formattedWord }}
                        />
                    );
                })}
            </span>
        );
    };



    const handleSend = async () => {
        if (!input.trim() && !selectedFile && !selectedAudio) return;

        const userMessage = {
            role: 'user',
            content: input,
            file: selectedFile?.name,
            audio: selectedAudio?.name,
            timestamp: new Date(),
            multimodal_data: {
                image_url: imagePreview // Store preview URL for display
            }
        };

        setMessages((prev) => [...prev, userMessage]);
        setInput('');
        setLoading(true);

        try {
            let response;
            if (selectedFile || selectedAudio) {
                response = await sendMultimodalMessage(
                    agentName,
                    input,
                    selectedAudio,
                    selectedFile,
                    true, // include TTS
                    ttsProvider
                );

                // Clear selections after sending
                setSelectedFile(null);
                setSelectedAudio(null);
                setImagePreview(null);
            } else {
                response = await sendMessage(agentName, input, true, ttsProvider);
            }

            const assistantMessage = {
                role: 'assistant',
                content: response.answer,
                confidence: response.confidence,
                inDomain: response.in_domain,
                explainability: response.explainability,
                tts: response.tts,
                timestamp: new Date(),
            };

            setMessages((prev) => [...prev, assistantMessage]);
        } catch (err) {
            const errorMessage = {
                role: 'assistant',
                content: `Sorry, I encountered an error: ${err.response?.data?.detail || err.message}`,
                isError: true,
                timestamp: new Date(),
            };
            setMessages((prev) => [...prev, errorMessage]);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleFileSelect = (e) => {
        const file = e.target.files[0];
        if (file) {
            setSelectedFile(file);

            // Create image preview
            if (file.type.startsWith('image/')) {
                const reader = new FileReader();
                reader.onloadend = () => {
                    setImagePreview(reader.result);
                };
                reader.readAsDataURL(file);
            }
        }
    };

    const handleAudioSelect = (e) => {
        const file = e.target.files[0];
        if (file) {
            setSelectedAudio(file);
        }
    };

    const handleTranscript = (transcript) => {
        setInput(prev => prev ? `${prev} ${transcript}` : transcript);
        setIsRecording(false);
    };

    const handleCancelRecording = () => {
        setIsRecording(false);
    };

    const openExplainability = (data) => {
        setExplainabilityModal({ open: true, data });
    };

    const formatMarkdown = (text) => {
        if (!text) return '';
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br />');
    };

    const isImageFile = (filename) => {
        if (!filename) return false;
        const ext = filename.split('.').pop().toLowerCase();
        return ['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext);
    };

    return (
        <Box sx={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            flexDirection: 'column',
            bgcolor: 'var(--background)',
            overflow: 'hidden',
            zIndex: 1000
        }}>
            {/* Animated Background */}
            <div className="animated-bg">
                <div className="orb orb-3" style={{ opacity: 0.15 }} />
            </div>

            {/* Header - Glassmorphism */}
            <Box
                className="glass-panel"
                sx={{
                    position: 'relative',
                    zIndex: 100,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 2,
                    p: { xs: 1, md: 1.5 },
                    borderRadius: 0,
                    mx: 0,
                    flexShrink: 0,
                    height: { xs: '60px', md: '64px' }
                }}
            >
                <Tooltip title="Back to Dashboard">
                    <IconButton
                        onClick={() => navigate('/dashboard')}
                        sx={{
                            bgcolor: 'rgba(255, 255, 255, 0.05)',
                            '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.1)' },
                            borderRadius: '12px'
                        }}
                    >
                        <BackIcon />
                    </IconButton>
                </Tooltip>

                <Box sx={{ position: 'relative' }}>
                    <Avatar sx={{
                        bgcolor: 'transparent',
                        border: '2px solid rgba(139, 92, 246, 0.5)',
                        boxShadow: '0 0 10px rgba(139, 92, 246, 0.3)'
                    }}>
                        <DiamondIcon color="primary" />
                    </Avatar>
                    <Box sx={{
                        position: 'absolute',
                        bottom: 0,
                        right: 0,
                        width: 10,
                        height: 10,
                        bgcolor: agent?.status === 'ready' ? '#22c55e' : '#f59e0b',
                        border: '2px solid var(--surface)',
                        borderRadius: '50%'
                    }} />
                </Box>

                <Box sx={{ flexGrow: 1 }}>
                    <Typography variant="h6" sx={{ fontWeight: 700, letterSpacing: '0.5px' }}>
                        {agentName.replace(/_/g, ' ')}
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'text.secondary', display: 'flex', alignItems: 'center', gap: 1 }}>
                        MEXAR <span style={{ fontWeight: 600, color: 'var(--primary)' }}>ULTIMATE</span> | {agent?.domain?.toUpperCase() || 'ASSISTANT'}
                    </Typography>
                </Box>

                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Tooltip title={autoPlayTTS ? 'Auto-play ON' : 'Auto-play OFF'}>
                        <IconButton
                            onClick={() => setAutoPlayTTS(!autoPlayTTS)}
                            sx={{
                                bgcolor: autoPlayTTS ? 'rgba(139, 92, 246, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                                '&:hover': { bgcolor: 'rgba(139, 92, 246, 0.3)' },
                                borderRadius: '12px'
                            }}
                        >
                            <SpeakerIcon sx={{ color: autoPlayTTS ? 'var(--primary)' : 'text.secondary' }} />
                        </IconButton>
                    </Tooltip>
                    <AgentSwitcher currentAgentName={agentName} />
                </Box>
            </Box>

            {/* Messages Area */}
            <Box
                sx={{
                    flexGrow: 1,
                    overflowY: 'auto',
                    px: { xs: 2, md: 4 },
                    py: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 3,
                    mt: 1,
                }}
            >
                {messages.map((msg, index) => (
                    <Box
                        key={index}
                        sx={{
                            display: 'flex',
                            justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                            gap: 2,
                            maxWidth: '100%'
                        }}
                    >
                        {msg.role === 'assistant' && (
                            <Avatar sx={{
                                bgcolor: 'transparent',
                                width: 28, height: 28, /* Reduced from 36 */
                                border: '1px solid rgba(139, 92, 246, 0.3)'
                            }}>
                                <DiamondIcon sx={{ fontSize: 16, color: 'var(--primary)' }} />
                            </Avatar>
                        )}

                        <Box sx={{ maxWidth: { xs: '85%', md: '70%' } }}>
                            <Box
                                className={`msg-bubble ${msg.role === 'user' ? 'msg-user' : 'msg-ai'}`}
                            >
                                {/* Image Attachment - ABOVE TEXT like Claude */}
                                {msg.file && (isImageFile(msg.file) || (msg.multimodal_data && msg.multimodal_data.image_url)) && (
                                    <Box
                                        onClick={() => {
                                            const url = msg.multimodal_data?.image_url;
                                            if (url) {
                                                setLightboxImage(url);
                                                setLightboxOpen(true);
                                            }
                                        }}
                                        sx={{
                                            mb: 1.5,
                                            cursor: 'pointer',
                                            borderRadius: '8px',
                                            overflow: 'hidden',
                                            position: 'relative',
                                            '&:hover .zoom-overlay': { opacity: 1 }
                                        }}
                                    >
                                        <img
                                            src={msg.multimodal_data?.image_url || '/placeholder_image.png'}
                                            alt="Attachment"
                                            style={{
                                                maxWidth: '100%',
                                                maxHeight: 200,
                                                display: 'block',
                                                borderRadius: '8px'
                                            }}
                                        />
                                        <Box className="zoom-overlay" sx={{
                                            position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
                                            bgcolor: 'rgba(0,0,0,0.4)',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            opacity: 0, transition: 'opacity 0.2s',
                                            borderRadius: '8px'
                                        }}>
                                            <ZoomInIcon sx={{ color: 'white', fontSize: 32 }} />
                                        </Box>
                                    </Box>
                                )}

                                {/* Text Content */}
                                <Typography
                                    variant="body1"
                                    component="div"
                                    sx={{
                                        lineHeight: 1.6,
                                        fontSize: '0.95rem',
                                        wordBreak: 'break-word',
                                        overflowWrap: 'anywhere'
                                    }}
                                >
                                    {renderMessageContent(msg.content, index)}
                                </Typography>

                                {/* Audio Attachment - shown as chip below text */}
                                {msg.audio && (
                                    <Box sx={{ display: 'flex', gap: 1, mt: 1.5 }}>
                                        <Chip
                                            size="small"
                                            icon={<MicIcon style={{ color: msg.role === 'user' ? 'white' : 'inherit' }} />}
                                            label={msg.audio}
                                            sx={{
                                                borderColor: msg.role === 'user' ? 'rgba(255,255,255,0.3)' : 'default',
                                                color: msg.role === 'user' ? 'white' : 'default',
                                                bgcolor: 'rgba(255,255,255,0.1)'
                                            }}
                                            variant="outlined"
                                        />
                                    </Box>
                                )}
                            </Box>

                            {/* Metadata footer for assistant */}
                            {msg.role === 'assistant' && !loading && (
                                <Fade in timeout={1000}>
                                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 1, ml: 1 }}>
                                        {msg.confidence !== undefined && (
                                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                                <Box sx={{
                                                    width: 6, height: 6, borderRadius: '50%',
                                                    bgcolor: msg.confidence > 0.7 ? '#22c55e' : '#f59e0b',
                                                    boxShadow: msg.confidence > 0.7 ? '0 0 8px #22c55e' : 'none'
                                                }} />
                                                <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', fontWeight: 600 }}>
                                                    {(msg.confidence * 100).toFixed(0)}% Confidence
                                                </Typography>
                                            </Box>
                                        )}

                                        {msg.explainability && (
                                            <Button
                                                size="small"
                                                startIcon={<WhyIcon sx={{ fontSize: 14 }} />}
                                                onClick={() => openExplainability(msg.explainability)}
                                                sx={{
                                                    minWidth: 0, p: '2px 8px',
                                                    textTransform: 'none',
                                                    fontSize: '0.7rem',
                                                    color: 'var(--primary-light)',
                                                    bgcolor: 'rgba(139, 92, 246, 0.1)',
                                                    borderRadius: '6px',
                                                    '&:hover': { bgcolor: 'rgba(139, 92, 246, 0.2)' }
                                                }}
                                            >
                                                Explain reasoning
                                            </Button>
                                        )}

                                        <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', ml: 'auto' }}>
                                            {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        </Typography>

                                        {/* Listen/Pause/Stop Button */}
                                        {activeTTSIndex === index ? (
                                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, ml: 1 }}>
                                                {isTTSPlaying ? (
                                                    <Tooltip title="Pause">
                                                        <IconButton
                                                            size="small"
                                                            onClick={handlePauseTTS}
                                                            sx={{
                                                                color: 'var(--primary)',
                                                                padding: '4px',
                                                                '&:hover': { bgcolor: 'rgba(139, 92, 246, 0.1)' }
                                                            }}
                                                        >
                                                            <PauseIcon sx={{ fontSize: 16 }} />
                                                        </IconButton>
                                                    </Tooltip>
                                                ) : (
                                                    <Tooltip title="Resume">
                                                        <IconButton
                                                            size="small"
                                                            onClick={handleResumeTTS}
                                                            sx={{
                                                                color: 'var(--primary)',
                                                                padding: '4px',
                                                                '&:hover': { bgcolor: 'rgba(139, 92, 246, 0.1)' }
                                                            }}
                                                        >
                                                            <SpeakerIcon sx={{ fontSize: 16 }} />
                                                        </IconButton>
                                                    </Tooltip>
                                                )}
                                                <Tooltip title="Stop">
                                                    <IconButton
                                                        size="small"
                                                        onClick={handleStopTTS}
                                                        sx={{
                                                            color: 'text.secondary',
                                                            padding: '4px',
                                                            '&:hover': { color: 'error.main', bgcolor: 'rgba(239, 68, 68, 0.1)' }
                                                        }}
                                                    >
                                                        <StopIcon sx={{ fontSize: 14 }} />
                                                    </IconButton>
                                                </Tooltip>
                                            </Box>
                                        ) : (
                                            <Tooltip title="Listen">
                                                <IconButton
                                                    size="small"
                                                    onClick={() => handlePlayTTSInline(index, msg.content)}
                                                    sx={{
                                                        ml: 1,
                                                        color: 'text.secondary',
                                                        opacity: 0.7,
                                                        '&:hover': { opacity: 1, color: 'var(--primary)' }
                                                    }}
                                                >
                                                    <SpeakerIcon fontSize="small" />
                                                </IconButton>
                                            </Tooltip>
                                        )}
                                    </Box>
                                </Fade>
                            )}
                        </Box>
                    </Box>
                ))}

                {/* Typing Indicator */}
                {loading && (
                    <Box sx={{ display: 'flex', gap: 2, maxWidth: '80%' }}>
                        <Avatar sx={{
                            bgcolor: 'transparent', width: 36, height: 36,
                            border: '1px solid rgba(139, 92, 246, 0.3)'
                        }}>
                            <DiamondIcon sx={{ fontSize: 20, color: 'var(--primary)' }} />
                        </Avatar>
                        <Box
                            className="msg-bubble msg-ai"
                            sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 60 }}
                        >
                            <div className="typing-dot"></div>
                            <div className="typing-dot"></div>
                            <div className="typing-dot"></div>
                        </Box>
                    </Box>
                )}

                <div ref={messagesEndRef} />
            </Box>

            {/* Floating Input Area */}
            <Box sx={{ p: 2, position: 'relative', zIndex: 20 }}>
                {/* Image Preview Card - ABOVE INPUT like screenshot #3 */}
                {imagePreview && (
                    <Box
                        sx={{
                            mb: 2,
                            p: 1.5,
                            bgcolor: 'rgba(255, 255, 255, 0.05)',
                            borderRadius: '12px',
                            border: '1px solid rgba(139, 92, 246, 0.3)',
                            position: 'relative',
                            display: 'inline-block',
                            maxWidth: '300px'
                        }}
                    >
                        <IconButton
                            onClick={() => {
                                setSelectedFile(null);
                                setImagePreview(null);
                            }}
                            sx={{
                                position: 'absolute',
                                top: 4,
                                right: 4,
                                bgcolor: 'rgba(0, 0, 0, 0.7)',
                                border: '1px solid rgba(255, 255, 255, 0.2)',
                                '&:hover': { bgcolor: 'rgba(0, 0, 0, 0.9)' },
                                width: 28,
                                height: 28,
                                zIndex: 10
                            }}
                            size="small"
                        >
                            <CloseIcon sx={{ fontSize: 16, color: 'white' }} />
                        </IconButton>
                        <img
                            src={imagePreview}
                            alt="Preview"
                            onClick={() => {
                                setLightboxImage(imagePreview);
                                setLightboxOpen(true);
                            }}
                            style={{
                                maxWidth: '100%',
                                maxHeight: '200px',
                                borderRadius: '8px',
                                objectFit: 'contain',
                                cursor: 'pointer',
                                display: 'block'
                            }}
                        />
                    </Box>
                )}

                {/* Input Box */}
                <Box
                    className="glass-panel"
                    sx={{
                        p: 1.5,
                        borderRadius: 4,
                        border: '1px solid rgba(139, 92, 246, 0.3)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1,
                        background: 'rgba(18, 18, 32, 0.8)'
                    }}
                >
                    {/* Live Audio Recording */}
                    {isRecording ? (
                        <Box sx={{ width: '100%', mb: 1 }}>
                            <AudioRecorder
                                onTranscript={handleTranscript}
                                onCancel={handleCancelRecording}
                            />
                        </Box>
                    ) : (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <input
                                type="file"
                                ref={fileInputRef}
                                onChange={handleFileSelect}
                                accept="image/*"
                                style={{ display: 'none' }}
                            />
                            <input
                                type="file"
                                ref={audioInputRef}
                                onChange={handleAudioSelect}
                                accept="audio/*"
                                style={{ display: 'none' }}
                            />

                            {/* Audio Chip Preview */}
                            {selectedAudio && (
                                <Chip
                                    size="small"
                                    icon={<MicIcon sx={{ fontSize: 14 }} />}
                                    label={selectedAudio.name.length > 12 ? selectedAudio.name.slice(0, 12) + '...' : selectedAudio.name}
                                    onDelete={() => setSelectedAudio(null)}
                                    sx={{
                                        bgcolor: 'rgba(6, 182, 212, 0.2)',
                                        borderRadius: '8px',
                                        height: 28,
                                        '& .MuiChip-deleteIcon': {
                                            color: 'rgba(255,255,255,0.7)',
                                            '&:hover': { color: 'white' }
                                        }
                                    }}
                                />
                            )}

                            {/* File/Image upload button */}
                            <IconButton
                                onClick={() => fileInputRef.current?.click()}
                                sx={{
                                    color: imagePreview ? 'var(--primary)' : 'text.secondary',
                                    '&:hover': { bgcolor: 'rgba(255,255,255,0.05)' }
                                }}
                            >
                                <ImageIcon />
                            </IconButton>
                            <IconButton
                                onClick={() => setIsRecording(true)}
                                sx={{
                                    color: selectedAudio ? 'var(--primary)' : 'text.secondary',
                                    '&:hover': { bgcolor: 'rgba(255,255,255,0.05)' }
                                }}
                            >
                                <MicIcon />
                            </IconButton>
                        </Box>
                    )}

                    {/* Text Field */}
                    <TextField
                        fullWidth
                        multiline
                        maxRows={4}
                        placeholder={selectedFile || selectedAudio ? "Describe the attachment..." : "Type your query here..."}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyPress={handleKeyPress}
                        disabled={loading}
                        variant="standard"
                        InputProps={{ disableUnderline: true, style: { fontSize: '16px' } }}
                        sx={{ ml: 1 }}
                    />

                    {/* Send Button */}
                    <IconButton
                        onClick={handleSend}
                        disabled={loading || (!input.trim() && !selectedFile && !selectedAudio)}
                        sx={{
                            bgcolor: 'var(--primary)',
                            color: 'white',
                            width: 44, height: 44,
                            '&:hover': { bgcolor: 'var(--primary-dark)', transform: 'scale(1.05)' },
                            '&:disabled': { bgcolor: 'rgba(255,255,255,0.1)' },
                            transition: 'all 0.2s',
                            boxShadow: '0 0 15px rgba(139, 92, 246, 0.4)'
                        }}
                    >
                        {loading ? <CircularProgress size={20} color="inherit" /> : <SendIcon fontSize="small" />}
                    </IconButton>
                </Box>
            </Box>

            {/* Modal */}
            <ExplainabilityModal
                open={explainabilityModal.open}
                data={explainabilityModal.data}
                onClose={() => setExplainabilityModal({ open: false, data: null })}
            />

            {/* Image Preview Lightbox */}
            <Dialog
                open={lightboxOpen}
                onClose={() => setLightboxOpen(false)}
                maxWidth="xl"
                PaperProps={{
                    style: { backgroundColor: 'transparent', boxShadow: 'none' }
                }}
            >
                <Box sx={{ position: 'relative' }}>
                    <IconButton
                        onClick={() => setLightboxOpen(false)}
                        sx={{
                            position: 'absolute',
                            top: -40,
                            right: -40,
                            color: 'white',
                            bgcolor: 'rgba(0,0,0,0.5)',
                            '&:hover': { bgcolor: 'rgba(0,0,0,0.8)' }
                        }}
                    >
                        <CloseIcon />
                    </IconButton>
                    <img
                        src={lightboxImage}
                        alt="Full Preview"
                        style={{ maxWidth: '90vw', maxHeight: '90vh', borderRadius: 8 }}
                    />
                </Box>
            </Dialog>
        </Box>
    );
}

export default Chat;
