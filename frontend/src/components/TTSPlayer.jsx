import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Box, IconButton, Slider, Typography, Tooltip, CircularProgress } from '@mui/material';
import {
    VolumeUp as SpeakerIcon,
    PlayArrow as PlayIcon,
    Pause as PauseIcon,
    Stop as StopIcon,
    VolumeOff as MuteIcon
} from '@mui/icons-material';
import { generateTTS, getTTSAudioURL } from '../api/client';

/**
 * TTSPlayer Component
 * Plays text-to-speech audio with playback controls and word highlighting
 */
function TTSPlayer({ text, provider = 'elevenlabs', autoPlay = false, onError, onWordChange }) {
    const [isPlaying, setIsPlaying] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [progress, setProgress] = useState(0);
    const [volume, setVolume] = useState(1);
    const [audioURL, setAudioURL] = useState(null);
    const [duration, setDuration] = useState(0);
    const [currentWordIndex, setCurrentWordIndex] = useState(-1);
    const [words, setWords] = useState([]);

    const audioRef = useRef(null);
    const utteranceRef = useRef(null);
    const wordTimerRef = useRef(null);

    // Parse text into words on mount
    useEffect(() => {
        if (text) {
            // Split text into words while preserving punctuation
            const wordList = text.split(/(\s+)/).filter(w => w.trim().length > 0);
            setWords(wordList);
        }
    }, [text]);

    useEffect(() => {
        if (autoPlay && text) {
            handlePlay();
        }

        return () => {
            cleanup();
        };
    }, []);

    const cleanup = useCallback(() => {
        if (audioRef.current) {
            audioRef.current.pause();
            audioRef.current = null;
        }
        if (window.speechSynthesis) {
            window.speechSynthesis.cancel();
        }
        if (wordTimerRef.current) {
            clearInterval(wordTimerRef.current);
            wordTimerRef.current = null;
        }
        setCurrentWordIndex(-1);
    }, []);

    const handlePlay = async () => {
        if (!audioURL) {
            // Generate TTS first
            setIsLoading(true);

            try {
                const result = await generateTTS(text, provider);

                if (result.success) {
                    if (provider === 'web_speech' || result.client_side) {
                        // Use Web Speech API with word highlighting
                        speakWithWebSpeech(text);
                    } else {
                        // Use ElevenLabs audio file
                        const url = getTTSAudioURL(result.audio_url.split('/').pop());
                        setAudioURL(url);
                        playAudio(url);
                    }
                } else {
                    // Fallback to Web Speech API
                    if (result.fallback === 'web_speech') {
                        speakWithWebSpeech(text);
                    } else {
                        throw new Error(result.error || 'TTS generation failed');
                    }
                }
            } catch (error) {
                console.error('TTS error:', error);
                if (onError) onError(error);

                // Final fallback to Web Speech API
                speakWithWebSpeech(text);
            } finally {
                setIsLoading(false);
            }
        } else {
            // Resume existing audio
            if (audioRef.current) {
                audioRef.current.play();
                setIsPlaying(true);
            }
        }
    };

    const playAudio = (url) => {
        const audio = new Audio(url);
        audioRef.current = audio;

        audio.volume = volume;

        audio.addEventListener('loadedmetadata', () => {
            setDuration(audio.duration);
        });

        audio.addEventListener('timeupdate', () => {
            const progressPercent = (audio.currentTime / audio.duration) * 100;
            setProgress(progressPercent);

            // Estimate word highlighting for audio playback
            if (words.length > 0) {
                const wordIndex = Math.floor((progressPercent / 100) * words.length);
                if (wordIndex !== currentWordIndex && wordIndex < words.length) {
                    setCurrentWordIndex(wordIndex);
                    if (onWordChange) onWordChange(wordIndex, words[wordIndex]);
                }
            }
        });

        audio.addEventListener('ended', () => {
            setIsPlaying(false);
            setProgress(0);
            setCurrentWordIndex(-1);
            if (onWordChange) onWordChange(-1, null);
        });

        audio.addEventListener('error', (e) => {
            console.error('Audio playback error:', e);
            // Fallback to Web Speech
            speakWithWebSpeech(text);
        });

        audio.play().catch(err => {
            console.error('Audio play failed:', err);
            speakWithWebSpeech(text);
        });
        setIsPlaying(true);
    };

    const speakWithWebSpeech = (text) => {
        if ('speechSynthesis' in window) {
            // Cancel any ongoing speech
            window.speechSynthesis.cancel();

            const utterance = new SpeechSynthesisUtterance(text);
            utteranceRef.current = utterance;
            utterance.volume = volume;
            utterance.rate = 1.0;
            utterance.pitch = 1.0;

            // Word boundary event for real-time word highlighting
            let currentCharIndex = 0;

            utterance.onboundary = (event) => {
                if (event.name === 'word') {
                    // Find which word is being spoken based on character index
                    const charIndex = event.charIndex;
                    let wordIdx = 0;
                    let charCount = 0;

                    for (let i = 0; i < words.length; i++) {
                        charCount += words[i].length + 1; // +1 for space
                        if (charCount > charIndex) {
                            wordIdx = i;
                            break;
                        }
                    }

                    setCurrentWordIndex(wordIdx);
                    if (onWordChange) onWordChange(wordIdx, words[wordIdx]);

                    // Update progress
                    const progressPercent = ((wordIdx + 1) / words.length) * 100;
                    setProgress(progressPercent);
                }
            };

            utterance.onstart = () => {
                setIsPlaying(true);
                setCurrentWordIndex(0);
                if (onWordChange && words.length > 0) onWordChange(0, words[0]);
            };

            utterance.onend = () => {
                setIsPlaying(false);
                setProgress(100);
                setCurrentWordIndex(-1);
                if (onWordChange) onWordChange(-1, null);

                // Reset progress after a short delay
                setTimeout(() => setProgress(0), 500);
            };

            utterance.onerror = (error) => {
                console.error('Web Speech error:', error);
                setIsPlaying(false);
                setCurrentWordIndex(-1);
                if (onError) onError(error);
            };

            window.speechSynthesis.speak(utterance);
        } else {
            alert('Text-to-speech is not supported in your browser');
        }
    };

    const handlePause = () => {
        if (audioRef.current) {
            audioRef.current.pause();
            setIsPlaying(false);
        } else if (window.speechSynthesis) {
            window.speechSynthesis.pause();
            setIsPlaying(false);
        }
    };

    const handleResume = () => {
        if (audioRef.current) {
            audioRef.current.play();
            setIsPlaying(true);
        } else if (window.speechSynthesis) {
            window.speechSynthesis.resume();
            setIsPlaying(true);
        }
    };

    const handleStop = () => {
        cleanup();
        setIsPlaying(false);
        setProgress(0);
        setAudioURL(null);
    };

    const handleVolumeChange = (event, newValue) => {
        setVolume(newValue);
        if (audioRef.current) {
            audioRef.current.volume = newValue;
        }
    };

    const handleProgressChange = (event, newValue) => {
        if (audioRef.current && duration) {
            audioRef.current.currentTime = (newValue / 100) * duration;
            setProgress(newValue);
        }
    };

    // Render highlighted text
    const renderHighlightedText = () => {
        if (!isPlaying || words.length === 0) return null;

        return (
            <Box sx={{
                mt: 1,
                p: 1.5,
                bgcolor: 'rgba(139, 92, 246, 0.05)',
                borderRadius: 2,
                border: '1px solid rgba(139, 92, 246, 0.1)',
                maxHeight: 100,
                overflowY: 'auto',
                fontSize: '0.9rem',
                lineHeight: 1.8
            }}>
                {words.map((word, idx) => (
                    <span
                        key={idx}
                        style={{
                            padding: '2px 4px',
                            margin: '0 1px',
                            borderRadius: '4px',
                            backgroundColor: idx === currentWordIndex
                                ? 'rgba(139, 92, 246, 0.4)'
                                : idx < currentWordIndex
                                    ? 'rgba(139, 92, 246, 0.1)'
                                    : 'transparent',
                            color: idx === currentWordIndex
                                ? 'white'
                                : 'inherit',
                            fontWeight: idx === currentWordIndex ? 600 : 400,
                            transition: 'all 0.15s ease'
                        }}
                    >
                        {word}
                    </span>
                ))}
            </Box>
        );
    };

    return (
        <Box sx={{ width: '100%' }}>
            <Box sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1,
                p: 1,
                bgcolor: 'rgba(139, 92, 246, 0.05)',
                borderRadius: 2,
                border: '1px solid rgba(139, 92, 246, 0.2)',
                minWidth: 200
            }}>
                {/* Play/Pause Button */}
                <Tooltip title={isPlaying ? 'Pause' : 'Play'}>
                    <IconButton
                        onClick={isPlaying ? handlePause : handlePlay}
                        disabled={isLoading}
                        size="small"
                        sx={{
                            color: 'var(--primary)',
                            '&:hover': { bgcolor: 'rgba(139, 92, 246, 0.1)' }
                        }}
                    >
                        {isLoading ? (
                            <CircularProgress size={20} />
                        ) : isPlaying ? (
                            <PauseIcon fontSize="small" />
                        ) : (
                            <PlayIcon fontSize="small" />
                        )}
                    </IconButton>
                </Tooltip>

                {/* Progress Bar */}
                <Box sx={{ flexGrow: 1, mx: 1 }}>
                    <Slider
                        value={progress}
                        onChange={handleProgressChange}
                        disabled={!audioRef.current}
                        size="small"
                        sx={{
                            color: 'var(--primary)',
                            '& .MuiSlider-thumb': {
                                width: 12,
                                height: 12
                            }
                        }}
                    />
                </Box>

                {/* Stop Button */}
                {isPlaying && (
                    <Tooltip title="Stop">
                        <IconButton
                            onClick={handleStop}
                            size="small"
                            sx={{
                                color: 'text.secondary',
                                '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.05)' }
                            }}
                        >
                            <StopIcon fontSize="small" />
                        </IconButton>
                    </Tooltip>
                )}

                {/* Volume Control */}
                <Box sx={{ display: 'flex', alignItems: 'center', width: 80 }}>
                    <IconButton size="small" sx={{ color: 'text.secondary' }}>
                        {volume === 0 ? <MuteIcon fontSize="small" /> : <SpeakerIcon fontSize="small" />}
                    </IconButton>
                    <Slider
                        value={volume}
                        onChange={handleVolumeChange}
                        min={0}
                        max={1}
                        step={0.1}
                        size="small"
                        sx={{
                            color: 'var(--primary)',
                            ml: 0.5,
                            '& .MuiSlider-thumb': {
                                width: 10,
                                height: 10
                            }
                        }}
                    />
                </Box>
            </Box>

            {/* Word Highlighting Display */}
            {renderHighlightedText()}
        </Box>
    );
}

export default TTSPlayer;
