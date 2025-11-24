import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const Login = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState(''); // Mock password
    const navigate = useNavigate();
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            // Mock login - in real app, use password
            const response = await axios.post(`${API_URL}/auth/login`, { email });
            localStorage.setItem('token', response.data.token);
            localStorage.setItem('user', JSON.stringify(response.data.user));
            navigate('/dashboard');
        } catch (error) {
            alert('Login failed');
        }
    };

    const handleRegister = async () => {
        const name = prompt("Enter Name:");
        const email = prompt("Enter Email:");
        const userId = "USR" + Math.floor(Math.random() * 10000);

        try {
            await axios.post(`${API_URL}/auth/register`, {
                name, email, user_id: userId
            });
            alert("Registered! Please login.");
        } catch (e) {
            alert("Registration failed");
        }
    }

    return (
        <div className="flex items-center justify-center h-screen bg-purple-600">
            <div className="bg-white p-8 rounded-lg shadow-xl w-96">
                <h1 className="text-3xl font-bold text-center text-purple-700 mb-6">PhonePay</h1>
                <form onSubmit={handleLogin} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Email</label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Password</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
                        />
                    </div>
                    <button
                        type="submit"
                        className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
                    >
                        Sign In
                    </button>
                </form>
                <div className="mt-4 text-center">
                    <button onClick={handleRegister} className="text-sm text-purple-600 hover:underline">
                        New user? Register here
                    </button>
                </div>
            </div>
        </div>
    );
};

export default Login;
