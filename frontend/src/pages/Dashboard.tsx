import { useEffect, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Wallet, Send, History, LogOut, ArrowUpRight, ArrowDownLeft, CreditCard } from 'lucide-react';

const Dashboard = () => {
    const [balance, setBalance] = useState(0);
    const [transactions, setTransactions] = useState([]);
    const navigate = useNavigate();
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

    useEffect(() => {
        if (!user.user_id) {
            navigate('/login');
            return;
        }
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const token = localStorage.getItem('token');
            const config = { headers: { Authorization: `Bearer ${token}` } };

            const balRes = await axios.get(`${API_URL}/api/wallet/balance?user_id=${user.user_id}`, config);
            setBalance(balRes.data.balance);

            const histRes = await axios.get(`${API_URL}/api/transactions/history?user_id=${user.user_id}`, config);
            setTransactions(histRes.data);
        } catch (error) {
            console.error("Error fetching data", error);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 font-sans">
            {/* Header */}
            <nav className="bg-[#6739b7] text-white p-4 shadow-lg sticky top-0 z-50">
                <div className="container mx-auto flex justify-between items-center">
                    <div className="flex items-center space-x-2">
                        <Wallet className="text-white" size={28} />
                        <h1 className="text-2xl font-bold tracking-tight">PhonePay</h1>
                    </div>
                    <div className="flex items-center space-x-6">
                        <span className="font-medium hidden md:block">Welcome, {user.name}</span>
                        <button
                            onClick={() => { localStorage.clear(); navigate('/login'); }}
                            className="flex items-center space-x-1 bg-[#5e35b1] hover:bg-[#512da8] px-4 py-2 rounded-full transition duration-300"
                        >
                            <LogOut size={18} />
                            <span className="text-sm">Logout</span>
                        </button>
                    </div>
                </div>
            </nav>

            <div className="container mx-auto mt-8 p-4 max-w-5xl">
                {/* Balance Card */}
                <div className="bg-gradient-to-r from-[#6739b7] to-[#9575cd] rounded-2xl shadow-xl p-8 mb-10 text-white relative overflow-hidden">
                    <div className="absolute top-0 right-0 -mt-10 -mr-10 w-40 h-40 bg-white opacity-10 rounded-full blur-2xl"></div>
                    <div className="relative z-10">
                        <p className="text-purple-100 text-sm font-medium uppercase tracking-wider mb-1">Total Balance</p>
                        <h2 className="text-5xl font-bold mb-6">₹ {balance.toFixed(2)}</h2>
                        <div className="flex space-x-4">
                            <button onClick={() => navigate('/send')} className="flex items-center space-x-2 bg-white text-[#6739b7] px-6 py-3 rounded-xl font-bold shadow-lg hover:bg-gray-100 transition transform hover:-translate-y-1">
                                <Send size={20} />
                                <span>Send Money</span>
                            </button>
                            <button onClick={() => navigate('/admin')} className="flex items-center space-x-2 bg-[#512da8] text-white px-6 py-3 rounded-xl font-bold shadow-lg hover:bg-[#4527a0] transition transform hover:-translate-y-1 border border-purple-400">
                                <History size={20} />
                                <span>Admin Panel</span>
                            </button>
                        </div>
                    </div>
                </div>

                {/* Quick Actions Grid (Optional expansion) */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
                    {['To Mobile', 'To Bank', 'To Self', 'Check Balance'].map((action, idx) => (
                        <div key={idx} className="bg-white p-4 rounded-xl shadow-sm hover:shadow-md transition cursor-pointer flex flex-col items-center justify-center space-y-2 border border-gray-100">
                            <div className="bg-purple-50 p-3 rounded-full text-[#6739b7]">
                                <CreditCard size={24} />
                            </div>
                            <span className="text-sm font-medium text-gray-700">{action}</span>
                        </div>
                    ))}
                </div>

                {/* Recent Transactions */}
                <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden">
                    <div className="p-6 border-b border-gray-100 flex justify-between items-center">
                        <h3 className="text-xl font-bold text-gray-800">Recent Transactions</h3>
                        <button className="text-[#6739b7] text-sm font-bold hover:underline">View All</button>
                    </div>
                    <div className="divide-y divide-gray-100">
                        {transactions.map((txn: any) => (
                            <div key={txn.transaction_id || Math.random()} className="p-6 flex justify-between items-center hover:bg-gray-50 transition">
                                <div className="flex items-center space-x-4">
                                    <div className={`p-3 rounded-full ${txn.type === 'CREDIT' ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'}`}>
                                        {txn.type === 'CREDIT' ? <ArrowDownLeft size={24} /> : <ArrowUpRight size={24} />}
                                    </div>
                                    <div>
                                        <p className="font-bold text-gray-800 text-lg">{txn.type === 'CREDIT' ? 'Received from' : 'Paid to'} {txn.type === 'CREDIT' ? txn.sender_id : txn.receiver_id}</p>
                                        <p className="text-sm text-gray-500">{new Date(txn.timestamp * 1000).toLocaleString()}</p>
                                    </div>
                                </div>
                                <span className={`text-lg font-bold ${txn.type === 'CREDIT' ? 'text-green-600' : 'text-gray-900'}`}>
                                    {txn.type === 'CREDIT' ? '+' : '-'} ₹ {txn.amount}
                                </span>
                            </div>
                        ))}
                        {transactions.length === 0 && (
                            <div className="p-10 text-center text-gray-500">
                                <History size={48} className="mx-auto mb-4 text-gray-300" />
                                <p>No transactions yet. Start by sending money!</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
