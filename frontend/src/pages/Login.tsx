import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { ShieldCheck } from 'lucide-react';

const Login = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const navigate = useNavigate();
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
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

        if (name && email) {
            try {
                await axios.post(`${API_URL}/auth/register`, {
                    name, email, user_id: userId
                });
                alert("Registered! Please login.");
            } catch (e) {
                alert("Registration failed");
            }
        }
    }

    return (
        <div className="flex items-center justify-center h-screen bg-[#6739b7]">
            <div className="bg-white p-10 rounded-2xl shadow-2xl w-96 transform transition-all hover:scale-105">
                <div className="flex justify-center mb-6">
                    <div className="bg-purple-100 p-3 rounded-full">
                        <ShieldCheck size={48} className="text-[#6739b7]" />
                    </div>
                </div>
                <h1 className="text-3xl font-bold text-center text-[#6739b7] mb-2">PhonePay</h1>
                <p className="text-center text-gray-500 mb-8">Secure Payment Gateway</p>

                <form onSubmit={handleLogin} className="space-y-5">
                    <div>
                        <label className="block text-sm font-semibold text-gray-700 mb-1">Email Address</label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#6739b7] focus:border-transparent transition"
                            placeholder="Enter your email"
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-semibold text-gray-700 mb-1">Password</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#6739b7] focus:border-transparent transition"
                            placeholder="Enter your password"
                        />
                    </div>
                    <button
                        type="submit"
                        className="w-full py-3 px-4 bg-[#6739b7] hover:bg-[#5e35b1] text-white font-bold rounded-lg shadow-md hover:shadow-lg transition duration-300 transform active:scale-95"
                    >
                        Sign In
                    </button>
                </form>

                <div className="mt-6 text-center">
                    <p className="text-sm text-gray-600">Don't have an account?</p>
                    <button onClick={handleRegister} className="text-sm font-bold text-[#6739b7] hover:underline mt-1">
                        Register Now
                    </button>
                </div>
            </div>
        </div>
    );
};

export default Login;
