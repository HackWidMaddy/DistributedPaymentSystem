import { useEffect, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Activity, Server, Shield, AlertTriangle, ArrowLeft } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

const AdminPanel = () => {
    const [lbStats, setLbStats] = useState<any>(null);
    const [systemStatus, setSystemStatus] = useState<any>(null);
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

    const getStatusColor = (status: string) => {
        if (status?.includes('ONLINE')) return 'text-green-600 bg-green-100';
        return 'text-red-600 bg-red-100';
    };

    const chartData = lbStats ? [
        { name: 'API-1', requests: lbStats.api_server_1.requests },
        { name: 'API-2', requests: lbStats.api_server_2.requests },
    ] : [];

    return (
        <div className="min-h-screen bg-gray-100 p-6">
            <button onClick={() => navigate('/dashboard')} className="flex items-center text-gray-600 mb-6 hover:text-gray-900">
                <ArrowLeft size={20} className="mr-2" /> Back to Dashboard
            </button>

            <h1 className="text-3xl font-bold text-gray-800 mb-8">System Administration</h1>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

                {/* Load Balancer Stats */}
                <div className="bg-white p-6 rounded-xl shadow-md">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-xl font-bold text-gray-800">Load Balancer Distribution</h2>
                        <Activity className="text-blue-500" />
                    </div>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={chartData}>
                                <XAxis dataKey="name" />
                                <YAxis />
                                <Tooltip />
                                <Bar dataKey="requests" fill="#8884d8" />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                    <div className="mt-4 grid grid-cols-2 gap-4 text-center">
                        <div className="bg-blue-50 p-2 rounded">
                            <p className="text-sm text-gray-500">API Server 1</p>
                            <p className="text-xl font-bold">{lbStats?.api_server_1.requests || 0}</p>
                        </div>
                        <div className="bg-blue-50 p-2 rounded">
                            <p className="text-sm text-gray-500">API Server 2</p>
                            <p className="text-xl font-bold">{lbStats?.api_server_2.requests || 0}</p>
                        </div>
                    </div>
                </div>

                {/* System Health */}
                <div className="bg-white p-6 rounded-xl shadow-md">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-xl font-bold text-gray-800">Service Health</h2>
                        <Server className="text-green-500" />
                    </div>
                    <div className="space-y-3">
                        {systemStatus && Object.entries(systemStatus).map(([service, status]: [string, any]) => (
                            <div key={service} className="flex justify-between items-center p-2 border-b last:border-0">
                                <span className="font-medium text-gray-700 capitalize">{service.replace(/_/g, ' ')}</span>
                                <span className={`px-3 py-1 rounded-full text-xs font-bold ${getStatusColor(status)}`}>
                                    {status}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Fraud Alerts (Mock) */}
                <div className="bg-white p-6 rounded-xl shadow-md">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-xl font-bold text-gray-800">Recent Fraud Alerts</h2>
                        <Shield className="text-red-500" />
                    </div>
                    <div className="space-y-2">
                        <div className="bg-red-50 p-3 rounded border-l-4 border-red-500">
                            <p className="font-bold text-red-800">High Value Transaction Blocked</p>
                            <p className="text-sm text-red-600">User: USR999 attempted ₹ 50,000</p>
                        </div>
                        <div className="bg-yellow-50 p-3 rounded border-l-4 border-yellow-500">
                            <p className="font-bold text-yellow-800">Suspicious Login Location</p>
                            <p className="text-sm text-yellow-600">User: USR123 from Russia</p>
                        </div>
                    </div>
                </div>

                {/* Control Panel */}
                <div className="bg-white p-6 rounded-xl shadow-md">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-xl font-bold text-gray-800">Failover Simulation</h2>
                        <AlertTriangle className="text-orange-500" />
                    </div>
                    <p className="text-gray-600 mb-4">Simulate failures to test system resilience.</p>
                    <div className="space-y-3">
                        <button className="w-full bg-red-600 text-white p-3 rounded hover:bg-red-700 transition font-bold">
                            KILL PRIMARY COORDINATOR
                        </button>
                        <button className="w-full bg-orange-500 text-white p-3 rounded hover:bg-orange-600 transition font-bold">
                            SIMULATE NETWORK LAG
                        </button>
                    </div>
                </div>

            </div>
        </div>
    );
};

export default AdminPanel;
