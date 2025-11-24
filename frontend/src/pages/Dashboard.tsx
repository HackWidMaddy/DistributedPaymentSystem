import { useEffect, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Wallet, Send, History, LogOut } from 'lucide-react';

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
        <div className="min-h-screen bg-gray-50">
            <nav className="bg-purple-700 text-white p-4 shadow-lg">
                <div className="container mx-auto flex justify-between items-center">
                    <h1 className="text-2xl font-bold">PhonePay</h1>
                    <div className="flex items-center space-x-4">
                        <span>Welcome, {user.name}</span>
                        <button onClick={() => { localStorage.clear(); navigate('/login'); }} className="p-2 hover:bg-purple-600 rounded-full">
                            <LogOut size={20} />
                        </button>
                    </div>
                </div>
            </nav>

            <div className="container mx-auto mt-8 p-4">
                {/* Balance Card */}
                <div className="bg-white rounded-xl shadow-md p-6 mb-8 flex items-center justify-between">
                    <div>
                        <p className="text-gray-500 text-sm font-medium">Wallet Balance</p>
                        <h2 className="text-4xl font-bold text-gray-800">₹ {balance.toFixed(2)}</h2>
                    </div>
                    <div className="bg-purple-100 p-4 rounded-full text-purple-600">
                        <Wallet size={40} />
                    </div>
                </div>

                {/* Actions */}
                <div className="grid grid-cols-2 gap-4 mb-8">
                    <button onClick={() => navigate('/send')} className="flex items-center justify-center space-x-2 bg-purple-600 text-white p-4 rounded-lg shadow hover:bg-purple-700 transition">
                        <Send size={20} />
                        <span className="font-medium">Send Money</span>
                    </button>
                    <button onClick={() => navigate('/admin')} className="flex items-center justify-center space-x-2 bg-gray-800 text-white p-4 rounded-lg shadow hover:bg-gray-900 transition">
                        <History size={20} />
                        <span className="font-medium">Admin Panel</span>
                    </button>
                </div>

                {/* Recent Transactions */}
                <div className="bg-white rounded-xl shadow-md p-6">
                    <h3 className="text-xl font-bold text-gray-800 mb-4">Recent Transactions</h3>
                    <div className="space-y-4">
                        {transactions.map((txn: any) => (
                            <div key={txn.transaction_id || Math.random()} className="flex justify-between items-center border-b pb-4 last:border-0">
                                <div className="flex items-center space-x-4">
                                    <div className={`p-2 rounded-full ${txn.type === 'CREDIT' ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'}`}>
                                        {txn.type === 'CREDIT' ? '+' : '-'}
                                    </div>
                                    <div>
                                        <p className="font-medium text-gray-800">{txn.type === 'CREDIT' ? 'Received' : 'Paid'}</p>
                                        <p className="text-xs text-gray-500">{new Date(txn.timestamp * 1000).toLocaleString()}</p>
                                    </div>
                                </div>
                                <span className={`font-bold ${txn.type === 'CREDIT' ? 'text-green-600' : 'text-red-600'}`}>
                                    {txn.type === 'CREDIT' ? '+' : '-'} ₹ {txn.amount}
                                </span>
                            </div>
                        ))}
                        {transactions.length === 0 && <p className="text-gray-500 text-center">No transactions yet.</p>}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
