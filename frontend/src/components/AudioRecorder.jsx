import React, { useState, useRef, useEffect } from 'react';
import { Box, IconButton, Typography, Tooltip, CircularProgress } from '@mui/material';
import {
    Mic as MicIcon,
    Stop as StopIcon,
    Close as CloseIcon,
    Check as CheckIcon
} from '@mui/icons-material';
import { transcribeAudio } from '../api/client';

/**
 * AudioRecorder Component
 * Provides live audio recording with real-time visualization and transcription
 */
function AudioRecorder({ onTranscript, onCancel }) {
    const [isRecording, setIsRecording] = useState(false);
    const [recordingTime, setRecordingTime] = useState(0);
    const [isProcessing, setIsProcessing] = useState(false);
    const [audioLevel, setAudioLevel] = useState(0);

    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);
    const timerRef = useRef(null);
    const analyserRef = useRef(null);
    const animationRef = useRef(null);

    useEffect(() => {
        return () => {
            // Cleanup on unmount
            stopRecording();
            if (animationRef.current) {
                cancelAnimationFrame(animationRef.current);
            }
        };
    }, []);

    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            // Setup audio analyzer for visualization
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const source = audioContext.createMediaStreamSource(stream);
            const analyser = audioContext.createAnalyser();
            analyser.fftSize = 256;
            source.connect(analyser);
            analyserRef.current = analyser;

            // Start visualization
            visualizeAudio();

            // Setup media recorder
            const mediaRecorder = new MediaRecorder(stream);
            mediaRecorderRef.current = mediaRecorder;
            audioChunksRef.current = [];

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
                await handleTranscription(audioBlob);

                // Stop all tracks
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            setIsRecording(true);

            // Start timer
            timerRef.current = setInterval(() => {
                setRecordingTime(prev => prev + 1);
            }, 1000);

        } catch (error) {
            console.error('Failed to start recording:', error);
            alert('Microphone access denied or not available');
        }
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);

            if (timerRef.current) {
                clearInterval(timerRef.current);
                timerRef.current = null;
            }

            if (animationRef.current) {
                cancelAnimationFrame(animationRef.current);
            }
        }
    };

    const visualizeAudio = () => {
        if (!analyserRef.current) return;

        const analyser = analyserRef.current;
        const dataArray = new Uint8Array(analyser.frequencyBinCount);

        const updateLevel = () => {
            analyser.getByteFrequencyData(dataArray);
            const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
            setAudioLevel(Math.min(100, (average / 255) * 100));

            if (isRecording) {
                animationRef.current = requestAnimationFrame(updateLevel);
            }
        };

        updateLevel();
    };

    const handleTranscription = async (audioBlob) => {
        setIsProcessing(true);

        try {
            const result = await transcribeAudio(audioBlob);

            if (result.success && result.transcript) {
                onTranscript(result.transcript);
            } else {
                alert('Transcription failed. Please try again.');
            }
        } catch (error) {
            console.error('Transcription error:', error);
            alert('Failed to transcribe audio: ' + error.message);
        } finally {
            setIsProcessing(false);
            setRecordingTime(0);
            setAudioLevel(0);
        }
    };

    const handleCancel = () => {
        if (isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);

            if (timerRef.current) {
                clearInterval(timerRef.current);
            }
        }

        setRecordingTime(0);
        setAudioLevel(0);
        onCancel();
    };

    const formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    if (isProcessing) {
        return (
            <Box sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 2,
                p: 2,
                bgcolor: 'rgba(139, 92, 246, 0.1)',
                borderRadius: 2,
                border: '1px solid rgba(139, 92, 246, 0.3)'
            }}>
                <CircularProgress size={24} sx={{ color: 'var(--primary)' }} />
                <Typography variant="body2">Transcribing audio...</Typography>
            </Box>
        );
    }

    return (
        <Box sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 2,
            p: 2,
            bgcolor: isRecording ? 'rgba(239, 68, 68, 0.1)' : 'rgba(139, 92, 246, 0.1)',
            borderRadius: 2,
            border: `1px solid ${isRecording ? 'rgba(239, 68, 68, 0.3)' : 'rgba(139, 92, 246, 0.3)'}`,
            animation: isRecording ? 'pulse 2s infinite' : 'none'
        }}>
            {/* Record/Stop Button */}
            <Tooltip title={isRecording ? 'Stop Recording' : 'Start Recording'}>
                <IconButton
                    onClick={isRecording ? stopRecording : startRecording}
                    sx={{
                        bgcolor: isRecording ? '#ef4444' : 'var(--primary)',
                        color: 'white',
                        '&:hover': {
                            bgcolor: isRecording ? '#dc2626' : 'var(--primary-dark)'
                        },
                        width: 48,
                        height: 48
                    }}
                >
                    {isRecording ? <StopIcon /> : <MicIcon />}
                </IconButton>
            </Tooltip>

            {/* Recording Info */}
            <Box sx={{ flexGrow: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {isRecording ? 'Recording...' : 'Ready to record'}
                </Typography>
                {isRecording && (
                    <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                        {formatTime(recordingTime)}
                    </Typography>
                )}
            </Box>

            {/* Audio Level Indicator */}
            {isRecording && (
                <Box sx={{
                    width: 100,
                    height: 4,
                    bgcolor: 'rgba(255,255,255,0.1)',
                    borderRadius: 2,
                    overflow: 'hidden'
                }}>
                    <Box sx={{
                        width: `${audioLevel}%`,
                        height: '100%',
                        bgcolor: '#ef4444',
                        transition: 'width 0.1s'
                    }} />
                </Box>
            )}

            {/* Cancel Button */}
            <Tooltip title="Cancel">
                <IconButton
                    onClick={handleCancel}
                    sx={{
                        color: 'text.secondary',
                        '&:hover': { bgcolor: 'rgba(255,255,255,0.05)' }
                    }}
                >
                    <CloseIcon />
                </IconButton>
            </Tooltip>
        </Box>
    );
}

export default AudioRecorder;
