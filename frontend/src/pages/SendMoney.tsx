import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

const SendMoney = () => {
    const [receiverId, setReceiverId] = useState('');
    const [amount, setAmount] = useState('');
    const [status, setStatus] = useState<string | null>(null);
    const navigate = useNavigate();
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

    const handlePayment = async (e: React.FormEvent) => {
        e.preventDefault();
        setStatus('PROCESSING');

        try {
            const token = localStorage.getItem('token');
            const config = { headers: { Authorization: `Bearer ${token}` } };

            const payload = {
                sender_id: user.user_id,
                receiver_id: receiverId,
                amount: parseFloat(amount)
            };

            const response = await axios.post(`${API_URL}/api/payment/initiate`, payload, config);

            if (response.data.status === 'SUCCESS') {
                setStatus('SUCCESS');
                setTimeout(() => navigate('/dashboard'), 2000);
            } else {
                setStatus(`FAILED: ${response.data.reason}`);
            }
        } catch (error: any) {
            setStatus(`ERROR: ${error.response?.data?.error || error.message}`);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 p-4">
            <button onClick={() => navigate('/dashboard')} className="flex items-center text-gray-600 mb-6 hover:text-gray-900">
                <ArrowLeft size={20} className="mr-2" /> Back to Dashboard
            </button>

            <div className="max-w-md mx-auto bg-white rounded-xl shadow-md p-8">
                <h2 className="text-2xl font-bold text-center text-purple-700 mb-6">Send Money</h2>

                <form onSubmit={handlePayment} className="space-y-6">
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Receiver ID</label>
                        <input
                            type="text"
                            value={receiverId}
                            onChange={(e) => setReceiverId(e.target.value)}
                            placeholder="e.g. USR456 or MERCHANT123"
                            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
                            required
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700">Amount (₹)</label>
                        <input
                            type="number"
                            value={amount}
                            onChange={(e) => setAmount(e.target.value)}
                            placeholder="0.00"
                            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-purple-500 focus:border-purple-500"
                            required
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={status === 'PROCESSING'}
                        className={`w-full py-3 px-4 rounded-md shadow-sm text-white font-bold transition
              ${status === 'PROCESSING' ? 'bg-gray-400 cursor-not-allowed' : 'bg-purple-600 hover:bg-purple-700'}`}
                    >
                        {status === 'PROCESSING' ? 'Processing...' : 'Pay Now'}
                    </button>
                </form>

                {status && status !== 'PROCESSING' && (
                    <div className={`mt-6 p-4 rounded-lg text-center font-medium ${status === 'SUCCESS' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                        {status === 'SUCCESS' ? 'Payment Successful!' : status}
                    </div>
                )}
            </div>
        </div>
    );
};

export default SendMoney;
