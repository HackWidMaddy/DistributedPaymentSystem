import { useEffect, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Activity, Server, Shield, AlertTriangle, ArrowLeft, RefreshCw, Power, Zap, RotateCcw } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const AdminPanel = () => {
    const [lbStats, setLbStats] = useState<any>(null);
    const [systemStatus, setSystemStatus] = useState<any>(null);
    const [actionStatus, setActionStatus] = useState<string | null>(null);
    const navigate = useNavigate();
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

    useEffect(() => {
        const fetchData = async () => {
            try {
                const lbRes = await axios.get(`${API_URL}/admin/lb-stats`);
                setLbStats(lbRes.data);

                const statusRes = await axios.get(`${API_URL}/admin/system-status`);
                setSystemStatus(statusRes.data);
            } catch (error) {
                console.error("Error fetching admin data", error);
            }
        };

        fetchData();
        const interval = setInterval(fetchData, 2000); // Poll every 2s
        return () => clearInterval(interval);
    }, []);

    const handleAction = async (endpoint: string, message: string) => {
        try {
            setActionStatus("Processing...");
            await axios.post(`${API_URL}/admin/${endpoint}`);
            setActionStatus(message);
            setTimeout(() => setActionStatus(null), 3000);
        } catch (error) {
            setActionStatus("Action Failed!");
            setTimeout(() => setActionStatus(null), 3000);
        }
    };

    const getStatusColor = (status: string) => {
        if (status?.includes('ONLINE')) return 'text-green-600 bg-green-100 border-green-200';
        return 'text-red-600 bg-red-100 border-red-200';
    };

    const chartData = lbStats ? [
        { name: 'API-1', requests: lbStats.api_server_1.requests },
        { name: 'API-2', requests: lbStats.api_server_2.requests },
    ] : [];

    return (
        <div className="min-h-screen bg-gray-100 font-sans">
            <nav className="bg-gray-900 text-white p-4 shadow-lg sticky top-0 z-50">
                <div className="container mx-auto flex justify-between items-center">
                    <div className="flex items-center space-x-4">
                        <button onClick={() => navigate('/dashboard')} className="text-gray-400 hover:text-white transition">
                            <ArrowLeft size={24} />
                        </button>
                        <h1 className="text-xl font-bold tracking-wide">System Administration</h1>
                    </div>
                    <div className="flex items-center space-x-2 text-sm text-gray-400">
                        <RefreshCw size={16} className="animate-spin" />
                        <span>Live Monitoring</span>
                    </div>
                </div>
            </nav>

            <div className="container mx-auto p-6 max-w-7xl">

                {actionStatus && (
                    <div className="mb-6 bg-blue-600 text-white p-4 rounded-lg shadow-lg text-center font-bold animate-pulse">
                        {actionStatus}
                    </div>
                )}

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

                    {/* Load Balancer Stats */}
                    <div className="bg-white p-6 rounded-2xl shadow-lg border border-gray-200">
                        <div className="flex items-center justify-between mb-6">
                            <div>
                                <h2 className="text-xl font-bold text-gray-800">Load Balancer</h2>
                                <p className="text-sm text-gray-500">Request distribution across API nodes</p>
                            </div>
                            <div className="bg-blue-100 p-3 rounded-full text-blue-600">
                                <Activity size={24} />
                            </div>
                        </div>
                        <div className="h-64">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={chartData}>
                                    <XAxis dataKey="name" axisLine={false} tickLine={false} />
                                    <YAxis axisLine={false} tickLine={false} />
                                    <Tooltip cursor={{ fill: '#f3f4f6' }} contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }} />
                                    <Bar dataKey="requests" radius={[8, 8, 0, 0]}>
                                        {chartData.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={index === 0 ? '#6739b7' : '#9575cd'} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                        <div className="mt-6 grid grid-cols-2 gap-4 text-center">
                            <div className="bg-gray-50 p-4 rounded-xl border border-gray-100">
                                <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">API Server 1</p>
                                <p className="text-2xl font-bold text-[#6739b7]">{lbStats?.api_server_1.requests || 0}</p>
                            </div>
                            <div className="bg-gray-50 p-4 rounded-xl border border-gray-100">
                                <p className="text-xs font-bold text-gray-500 uppercase tracking-wider">API Server 2</p>
                                <p className="text-2xl font-bold text-[#9575cd]">{lbStats?.api_server_2.requests || 0}</p>
                            </div>
                        </div>
                    </div>

                    {/* System Health */}
                    <div className="bg-white p-6 rounded-2xl shadow-lg border border-gray-200">
                        <div className="flex items-center justify-between mb-6">
                            <div>
                                <h2 className="text-xl font-bold text-gray-800">Service Health</h2>
                                <p className="text-sm text-gray-500">Real-time status of microservices</p>
                            </div>
                            <div className="bg-green-100 p-3 rounded-full text-green-600">
                                <Server size={24} />
                            </div>
                        </div>
                        <div className="space-y-3">
                            {systemStatus && Object.entries(systemStatus).map(([service, status]: [string, any]) => (
                                <div key={service} className="flex justify-between items-center p-3 hover:bg-gray-50 rounded-lg transition">
                                    <span className="font-medium text-gray-700 capitalize">{service.replace(/_/g, ' ')}</span>
                                    <span className={`px-3 py-1 rounded-full text-xs font-bold border ${getStatusColor(status)}`}>
                                        {status}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Fraud Alerts (Mock) */}
                    <div className="bg-white p-6 rounded-2xl shadow-lg border border-gray-200">
                        <div className="flex items-center justify-between mb-6">
                            <div>
                                <h2 className="text-xl font-bold text-gray-800">Fraud Detection</h2>
                                <p className="text-sm text-gray-500">Recent security alerts</p>
                            </div>
                            <div className="bg-red-100 p-3 rounded-full text-red-600">
                                <Shield size={24} />
                            </div>
                        </div>
                        <div className="space-y-4">
                            <div className="bg-red-50 p-4 rounded-xl border border-red-100 flex items-start space-x-3">
                                <Shield size={20} className="text-red-600 mt-1" />
                                <div>
                                    <p className="font-bold text-red-800">High Value Transaction Blocked</p>
                                    <p className="text-sm text-red-600">User: USR999 attempted ₹ 50,000</p>
                                </div>
                            </div>
                            <div className="bg-yellow-50 p-4 rounded-xl border border-yellow-100 flex items-start space-x-3">
                                <AlertTriangle size={20} className="text-yellow-600 mt-1" />
                                <div>
                                    <p className="font-bold text-yellow-800">Suspicious Login Location</p>
                                    <p className="text-sm text-yellow-600">User: USR123 from Russia</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Control Panel */}
                    <div className="bg-white p-6 rounded-2xl shadow-lg border border-gray-200">
                        <div className="flex items-center justify-between mb-6">
                            <div>
                                <h2 className="text-xl font-bold text-gray-800">Chaos Engineering</h2>
                                <p className="text-sm text-gray-500">Simulate failures & latency</p>
                            </div>
                            <div className="bg-orange-100 p-3 rounded-full text-orange-600">
                                <AlertTriangle size={24} />
                            </div>
                        </div>
                        <div className="space-y-4">
                            <button
                                onClick={() => handleAction('kill-coordinator', 'Primary Coordinator Killed!')}
                                className="w-full bg-red-600 text-white p-4 rounded-xl hover:bg-red-700 transition font-bold shadow-md hover:shadow-lg flex items-center justify-center space-x-2"
                            >
                                <Power size={20} />
                                <span>KILL PRIMARY COORDINATOR</span>
                            </button>
                            <button
                                onClick={() => handleAction('simulate-lag', 'Network Lag Simulated (2s)')}
                                className="w-full bg-orange-500 text-white p-4 rounded-xl hover:bg-orange-600 transition font-bold shadow-md hover:shadow-lg flex items-center justify-center space-x-2"
                            >
                                <Zap size={20} />
                                <span>SIMULATE NETWORK LAG</span>
                            </button>
                            <button
                                onClick={() => handleAction('reset-system', 'System Restored to Normal')}
                                className="w-full bg-green-600 text-white p-4 rounded-xl hover:bg-green-700 transition font-bold shadow-md hover:shadow-lg flex items-center justify-center space-x-2"
                            >
                                <RotateCcw size={20} />
                                <span>RESET SYSTEM</span>
                            </button>
                        </div>
                    </div>

                </div>
            </div>
        </div>
    );
};

export default AdminPanel;
