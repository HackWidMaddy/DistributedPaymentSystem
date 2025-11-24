import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, User, IndianRupee, CheckCircle, XCircle } from 'lucide-react';

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
        <div className="min-h-screen bg-gray-50 flex flex-col">
            <div className="bg-[#6739b7] p-6 pb-24 text-white shadow-lg">
                <div className="container mx-auto max-w-md">
                    <button onClick={() => navigate('/dashboard')} className="flex items-center text-purple-100 hover:text-white transition mb-4">
                        <ArrowLeft size={20} className="mr-2" /> Back
                    </button>
                    <h1 className="text-3xl font-bold">Send Money</h1>
                    <p className="text-purple-200 mt-1">Securely transfer funds to anyone</p>
                </div>
            </div>

            <div className="container mx-auto max-w-md -mt-16 px-4 flex-grow">
                <div className="bg-white rounded-2xl shadow-xl p-8">
                    <form onSubmit={handlePayment} className="space-y-8">

                        {/* Receiver Input */}
                        <div className="space-y-2">
                            <label className="text-sm font-bold text-gray-600 uppercase tracking-wide">To</label>
                            <div className="flex items-center border-b-2 border-gray-200 focus-within:border-[#6739b7] transition py-2">
                                <User className="text-gray-400 mr-3" size={24} />
                                <input
                                    type="text"
                                    value={receiverId}
                                    onChange={(e) => setReceiverId(e.target.value)}
                                    placeholder="Enter Receiver ID / Mobile"
                                    className="flex-grow outline-none text-lg font-medium text-gray-800 placeholder-gray-300"
                                    required
                                />
                            </div>
                        </div>

                        {/* Amount Input */}
                        <div className="space-y-2">
                            <label className="text-sm font-bold text-gray-600 uppercase tracking-wide">Amount</label>
                            <div className="flex items-center border-b-2 border-gray-200 focus-within:border-[#6739b7] transition py-2">
                                <IndianRupee className="text-gray-400 mr-3" size={24} />
                                <input
                                    type="number"
                                    value={amount}
                                    onChange={(e) => setAmount(e.target.value)}
                                    placeholder="0.00"
                                    className="flex-grow outline-none text-3xl font-bold text-gray-800 placeholder-gray-300"
                                    required
                                />
                            </div>
                        </div>

                        {/* Submit Button */}
                        <button
                            type="submit"
                            disabled={status === 'PROCESSING'}
                            className={`w-full py-4 rounded-xl text-white font-bold text-lg shadow-lg transition transform active:scale-95
                                ${status === 'PROCESSING' ? 'bg-gray-400 cursor-not-allowed' : 'bg-[#6739b7] hover:bg-[#5e35b1]'}`}
                        >
                            {status === 'PROCESSING' ? 'Processing Transaction...' : 'Pay Now'}
                        </button>
                    </form>

                    {/* Status Messages */}
                    {status && status !== 'PROCESSING' && (
                        <div className={`mt-8 p-6 rounded-xl flex flex-col items-center justify-center text-center animate-fade-in ${status === 'SUCCESS' ? 'bg-green-50' : 'bg-red-50'}`}>
                            {status === 'SUCCESS' ? (
                                <>
                                    <CheckCircle size={48} className="text-green-500 mb-2" />
                                    <h3 className="text-xl font-bold text-green-800">Payment Successful!</h3>
                                    <p className="text-green-600">Redirecting to dashboard...</p>
                                </>
                            ) : (
                                <>
                                    <XCircle size={48} className="text-red-500 mb-2" />
                                    <h3 className="text-xl font-bold text-red-800">Payment Failed</h3>
                                    <p className="text-red-600">{status}</p>
                                </>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default SendMoney;
