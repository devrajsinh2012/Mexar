import React, { useState } from 'react';
import {
    Box,
    Typography,
    Avatar,
    Menu,
    MenuItem,
    ListItemIcon,
    Divider,
    IconButton,
    Tooltip
} from '@mui/material';
import {
    Logout as LogoutIcon,
    LockReset as LockResetIcon,
    Person as PersonIcon,
    Settings as SettingsIcon,
    AccountCircle as AccountCircleIcon
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import ChangePasswordModal from './ChangePasswordModal';
import SettingsModal from './SettingsModal';

const ProfileDropdown = () => {
    const { user, logout } = useAuth();
    const [anchorEl, setAnchorEl] = useState(null);
    const [passwordModalOpen, setPasswordModalOpen] = useState(false);
    const [settingsModalOpen, setSettingsModalOpen] = useState(false);

    const open = Boolean(anchorEl);

    const handleClick = (event) => {
        setAnchorEl(event.currentTarget);
    };

    const handleClose = () => {
        setAnchorEl(null);
    };

    const handleLogout = () => {
        handleClose();
        logout();
    };

    const handleChangePassword = () => {
        handleClose();
        setPasswordModalOpen(true);
    };

    // Generate initials for avatar
    const getInitials = (name) => {
        if (!name) return 'U';
        return name.substring(0, 2).toUpperCase();
    };

    return (
        <>
            <Box display="flex" alignItems="center" gap={1}>
                {/* Profile Button - Replaces the old text/logout combo */}
                <Tooltip title="Account Settings">
                    <IconButton
                        onClick={handleClick}
                        size="small"
                        sx={{ ml: 2 }}
                        aria-controls={open ? 'account-menu' : undefined}
                        aria-haspopup="true"
                        aria-expanded={open ? 'true' : undefined}
                    >
                        <Avatar
                            sx={{ width: 40, height: 40, bgcolor: 'primary.main', fontWeight: 'bold' }}
                        >
                            {/* Use first letter of email if name is not available, generic fallback */}
                            {user?.email ? user.email.charAt(0).toUpperCase() : <AccountCircleIcon />}
                        </Avatar>
                    </IconButton>
                </Tooltip>
            </Box>

            <Menu
                anchorEl={anchorEl}
                id="account-menu"
                open={open}
                onClose={handleClose}
                onClick={handleClose}
                PaperProps={{
                    elevation: 0,
                    sx: {
                        overflow: 'visible',
                        filter: 'drop-shadow(0px 2px 8px rgba(0,0,0,0.32))',
                        mt: 1.5,
                        backgroundColor: '#1E1E2E', // Dark theme background matching app
                        color: 'white',
                        border: '1px solid rgba(255,255,255,0.1)',
                        '& .MuiAvatar-root': {
                            width: 32,
                            height: 32,
                            ml: -0.5,
                            mr: 1,
                        },
                        '&:before': {
                            content: '""',
                            display: 'block',
                            position: 'absolute',
                            top: 0,
                            right: 14,
                            width: 10,
                            height: 10,
                            bgcolor: '#1E1E2E',
                            transform: 'translateY(-50%) rotate(45deg)',
                            zIndex: 0,
                            borderLeft: '1px solid rgba(255,255,255,0.1)',
                            borderTop: '1px solid rgba(255,255,255,0.1)',
                        },
                    },
                }}
                transformOrigin={{ horizontal: 'right', vertical: 'top' }}
                anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
            >
                {/* User Info Section */}
                <Box sx={{ px: 2, py: 1.5 }}>
                    <Typography variant="subtitle1" fontWeight="bold">
                        {user?.email?.split('@')[0] || 'User'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                        {user?.email}
                    </Typography>
                </Box>

                <Divider sx={{ my: 0.5, borderColor: 'rgba(255,255,255,0.1)' }} />

                <MenuItem onClick={() => { handleClose(); setPasswordModalOpen(true); }}>
                    <ListItemIcon>
                        <LockResetIcon fontSize="small" sx={{ color: 'rgba(255,255,255,0.7)' }} />
                    </ListItemIcon>
                    Change Password
                </MenuItem>

                <MenuItem onClick={() => { handleClose(); setSettingsModalOpen(true); }}>
                    <ListItemIcon>
                        <SettingsIcon fontSize="small" sx={{ color: 'rgba(255,255,255,0.7)' }} />
                    </ListItemIcon>
                    Settings
                </MenuItem>

                <Divider sx={{ my: 0.5, borderColor: 'rgba(255,255,255,0.1)' }} />

                <MenuItem onClick={handleLogout}>
                    <ListItemIcon>
                        <LogoutIcon fontSize="small" sx={{ color: '#ef4444' }} />
                    </ListItemIcon>
                    <Typography color="error" variant="body2">Logout</Typography>
                </MenuItem>
            </Menu>

            {/* Change Password Modal */}
            <ChangePasswordModal
                open={passwordModalOpen}
                onClose={() => setPasswordModalOpen(false)}
            />

            {/* Settings Modal */}
            <SettingsModal
                open={settingsModalOpen}
                onClose={() => setSettingsModalOpen(false)}
            />
        </>
    );
};

export default ProfileDropdown;
