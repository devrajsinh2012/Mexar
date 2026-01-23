import React, { useState, useRef, useEffect } from 'react';
import { Box, IconButton, Tooltip } from '@mui/material';
import {
    PlayArrow as PlayIcon,
    Pause as PauseIcon,
    Stop as StopIcon
} from '@mui/icons-material';

/**
 * MessageContent Component
 * Renders message text with inline word highlighting during TTS playback
 */
function MessageContent({ content, isPlaying, currentWordIndex, formatMarkdown }) {
    if (!isPlaying || currentWordIndex < 0) {
        // Normal rendering without highlighting
        return (
            <span dangerouslySetInnerHTML={{ __html: formatMarkdown(content) }} />
        );
    }

    // Parse content into words for highlighting
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
                            padding: isCurrentWord ? '1px 2px' : '0',
                            transition: 'background-color 0.1s ease'
                        }}
                    >
                        {word}
                    </span>
                );
            })}
        </span>
    );
}

/**
 * InlineTTSControls Component
 * Simple play/pause/stop controls for TTS - no progress bar, no loaders
 */
function InlineTTSControls({ isPlaying, onPlay, onPause, onStop }) {
    return (
        <Box sx={{ display: 'inline-flex', alignItems: 'center', ml: 1, gap: 0.5 }}>
            {!isPlaying ? (
                <Tooltip title="Listen">
                    <IconButton
                        size="small"
                        onClick={onPlay}
                        sx={{
                            color: 'text.secondary',
                            padding: '4px',
                            '&:hover': { color: 'var(--primary)', bgcolor: 'rgba(139, 92, 246, 0.1)' }
                        }}
                    >
                        <PlayIcon sx={{ fontSize: 16 }} />
                    </IconButton>
                </Tooltip>
            ) : (
                <>
                    <Tooltip title="Pause">
                        <IconButton
                            size="small"
                            onClick={onPause}
                            sx={{
                                color: 'var(--primary)',
                                padding: '4px',
                                '&:hover': { bgcolor: 'rgba(139, 92, 246, 0.1)' }
                            }}
                        >
                            <PauseIcon sx={{ fontSize: 16 }} />
                        </IconButton>
                    </Tooltip>
                    <Tooltip title="Stop">
                        <IconButton
                            size="small"
                            onClick={onStop}
                            sx={{
                                color: 'text.secondary',
                                padding: '4px',
                                '&:hover': { color: 'error.main', bgcolor: 'rgba(239, 68, 68, 0.1)' }
                            }}
                        >
                            <StopIcon sx={{ fontSize: 14 }} />
                        </IconButton>
                    </Tooltip>
                </>
            )}
        </Box>
    );
}

/**
 * useTTS Hook
 * Handles Web Speech API with word boundary tracking
 */
export function useTTS(text) {
    const [isPlaying, setIsPlaying] = useState(false);
    const [isPaused, setIsPaused] = useState(false);
    const [currentWordIndex, setCurrentWordIndex] = useState(-1);
    const utteranceRef = useRef(null);
    const wordsRef = useRef([]);

    useEffect(() => {
        if (text) {
            wordsRef.current = text.split(/\s+/).filter(w => w.length > 0);
        }
        return () => {
            if (window.speechSynthesis) {
                window.speechSynthesis.cancel();
            }
        };
    }, [text]);

    const play = () => {
        if (isPaused && window.speechSynthesis) {
            window.speechSynthesis.resume();
            setIsPlaying(true);
            setIsPaused(false);
            return;
        }

        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();

            const utterance = new SpeechSynthesisUtterance(text);
            utteranceRef.current = utterance;
            utterance.rate = 1.0;
            utterance.pitch = 1.0;

            // Track word boundaries
            utterance.onboundary = (event) => {
                if (event.name === 'word') {
                    const charIndex = event.charIndex;
                    let wordIdx = 0;
                    let charCount = 0;

                    for (let i = 0; i < wordsRef.current.length; i++) {
                        if (charCount >= charIndex) {
                            wordIdx = i;
                            break;
                        }
                        charCount += wordsRef.current[i].length + 1;
                    }
                    setCurrentWordIndex(wordIdx);
                }
            };

            utterance.onstart = () => {
                setIsPlaying(true);
                setIsPaused(false);
                setCurrentWordIndex(0);
            };

            utterance.onend = () => {
                setIsPlaying(false);
                setIsPaused(false);
                setCurrentWordIndex(-1);
            };

            utterance.onerror = () => {
                setIsPlaying(false);
                setIsPaused(false);
                setCurrentWordIndex(-1);
            };

            window.speechSynthesis.speak(utterance);
        }
    };

    const pause = () => {
        if (window.speechSynthesis) {
            window.speechSynthesis.pause();
            setIsPlaying(false);
            setIsPaused(true);
        }
    };

    const stop = () => {
        if (window.speechSynthesis) {
            window.speechSynthesis.cancel();
        }
        setIsPlaying(false);
        setIsPaused(false);
        setCurrentWordIndex(-1);
    };

    return {
        isPlaying,
        isPaused,
        currentWordIndex,
        play,
        pause,
        stop
    };
}

export { MessageContent, InlineTTSControls };
