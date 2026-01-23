
import React, { createContext, useState, useContext, useEffect } from 'react';
import client from '../api/client';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [token, setToken] = useState(localStorage.getItem('token'));
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const initAuth = async () => {
            if (token) {
                try {
                    // Verify token and get user data
                    const response = await client.get('/api/auth/me');
                    setUser(response.data);
                } catch (error) {
                    console.error('Auth check failed:', error);
                    logout();
                }
            }
            setLoading(false);
        };

        initAuth();
    }, [token]);

    const login = async (email, password) => {
        const response = await client.post('/api/auth/login', { email, password });
        const { access_token, user } = response.data;

        setToken(access_token);
        setUser(user);
        localStorage.setItem('token', access_token);
        return user;
    };

    const register = async (email, password) => {
        await client.post('/api/auth/register', { email, password });
        // Auto login after register
        return login(email, password);
    };

    const logout = () => {
        setToken(null);
        setUser(null);
        localStorage.removeItem('token');
    };

    const refreshUser = async () => {
        if (token) {
            try {
                const response = await client.get('/api/auth/me');
                setUser(response.data);
                return response.data;
            } catch (error) {
                console.error('Failed to refresh user:', error);
            }
        }
        return null;
    };

    return (
        <AuthContext.Provider value={{ user, token, loading, login, register, logout, refreshUser }}>
            {!loading && children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
