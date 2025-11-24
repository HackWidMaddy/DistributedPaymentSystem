import { useEffect, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { Activity, Server, Shield, AlertTriangle, ArrowLeft, RefreshCw, Power, Zap, RotateCcw, Clock } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LineChart, Line, CartesianGrid, Legend } from 'recharts';

const AdminPanel = () => {
    const [lbStats, setLbStats] = useState<any>(null);
    const [systemStatus, setSystemStatus] = useState<any>(null);
    const [actionStatus, setActionStatus] = useState<string | null>(null);
    const [latencyHistory, setLatencyHistory] = useState<any[]>([]);
    const [gatewayNodes, setGatewayNodes] = useState<any[]>([]);
    const navigate = useNavigate();
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

    useEffect(() => {
        const fetchData = async () => {
            try {
                const lbRes = await axios.get(`${API_URL}/admin/lb-stats`);
                setLbStats(lbRes.data);

                const statusRes = await axios.get(`${API_URL}/admin/system-status`);
                setSystemStatus(statusRes.data);

                const clusterRes = await axios.get(`${API_URL}/admin/gateway-cluster`);
                setGatewayNodes(clusterRes.data);

                // Update Latency History
                const now = new Date().toLocaleTimeString();
                setLatencyHistory(prev => {
                    const newPoint = {
                        time: now,
                        api1: lbRes.data.api_server_1.avg_latency || 0,
                        api2: lbRes.data.api_server_2.avg_latency || 0
                    };
                    const newHistory = [...prev, newPoint];
                    if (newHistory.length > 20) newHistory.shift(); // Keep last 20 points
                    return newHistory;
                });

            } catch (error) {
                console.error("Error fetching admin data", error);
            }
        };

        fetchData();
        const interval = setInterval(fetchData, 1000); // Poll every 1s
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

    const toggleNode = async (nodeId: string) => {
        try {
            await axios.post(`${API_URL}/admin/toggle-node`, { node_id: nodeId });
            // Optimistic update or wait for poll
        } catch (error) {
            console.error("Failed to toggle node");
        }
    };

    const switchLeader = async () => {
        handleAction('switch-leader', 'Leader Election Triggered!');
    };

    const getStatusColor = (status: string) => {
        if (status?.includes('LAGGING')) return 'text-orange-600 bg-orange-100 border-orange-200 animate-pulse';
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

                    {/* Load Balancer Stats & Latency Graph */}
                    <div className="bg-white p-6 rounded-2xl shadow-lg border border-gray-200">
                        <div className="flex items-center justify-between mb-6">
                            <div>
                                <h2 className="text-xl font-bold text-gray-800">Traffic & Latency</h2>
                                <p className="text-sm text-gray-500">Real-time request metrics</p>
                            </div>
                            <div className="bg-blue-100 p-3 rounded-full text-blue-600">
                                <Activity size={24} />
                            </div>
                        </div>

                        <div className="space-y-6">
                            <div className="h-40">
                                <p className="text-xs font-bold text-gray-500 mb-2 text-center">Request Distribution</p>
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={chartData}>
                                        <XAxis dataKey="name" axisLine={false} tickLine={false} />
                                        <Tooltip cursor={{ fill: '#f3f4f6' }} />
                                        <Bar dataKey="requests" radius={[4, 4, 0, 0]}>
                                            {chartData.map((entry, index) => (
                                                <Cell key={`cell-${index}`} fill={index === 0 ? '#6739b7' : '#9575cd'} />
                                            ))}
                                        </Bar>
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>

                            <div className="h-48">
                                <p className="text-xs font-bold text-gray-500 mb-2 text-center">Real-time Latency (ms)</p>
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={latencyHistory}>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                        <XAxis dataKey="time" hide />
                                        <YAxis />
                                        <Tooltip />
                                        <Legend />
                                        <Line type="monotone" dataKey="api1" stroke="#6739b7" strokeWidth={2} dot={false} name="API-1" />
                                        <Line type="monotone" dataKey="api2" stroke="#9575cd" strokeWidth={2} dot={false} name="API-2" />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4 text-center mt-4">
                            <div className="bg-gray-50 p-3 rounded-xl border border-gray-100">
                                <p className="text-xs font-bold text-gray-500 uppercase">API-1 Latency</p>
                                <p className={`text-xl font-bold ${lbStats?.api_server_1.avg_latency > 1000 ? 'text-red-600' : 'text-green-600'}`}>
                                    {lbStats?.api_server_1.avg_latency.toFixed(0) || 0} ms
                                </p>
                            </div>
                            <div className="bg-gray-50 p-3 rounded-xl border border-gray-100">
                                <p className="text-xs font-bold text-gray-500 uppercase">API-2 Latency</p>
                                <p className={`text-xl font-bold ${lbStats?.api_server_2.avg_latency > 1000 ? 'text-red-600' : 'text-green-600'}`}>
                                    {lbStats?.api_server_2.avg_latency.toFixed(0) || 0} ms
                                </p>
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
                                    <span className={`px-3 py-1 rounded-full text-xs font-bold border flex items-center gap-1 ${getStatusColor(status)}`}>
                                        {status?.includes('LAGGING') && <Clock size={12} />}
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
                                onClick={() => handleAction('kill-backup-coordinator', 'Backup Coordinator Killed!')}
                                className="w-full bg-red-800 text-white p-4 rounded-xl hover:bg-red-900 transition font-bold shadow-md hover:shadow-lg flex items-center justify-center space-x-2"
                            >
                                <Power size={20} />
                                <span>KILL BACKUP COORDINATOR</span>
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

                    {/* Gateway Cluster & Routing (New) */}
                    <div className="bg-white p-6 rounded-2xl shadow-lg border border-gray-200 lg:col-span-2">
                        <div className="flex items-center justify-between mb-6">
                            <div>
                                <h2 className="text-xl font-bold text-gray-800">Gateway Cluster & Routing</h2>
                                <p className="text-sm text-gray-500">Dynamic Leader Election & Traffic Distribution</p>
                            </div>
                            <div className="bg-purple-100 p-3 rounded-full text-purple-600">
                                <Activity size={24} />
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                            {gatewayNodes.map((node: any) => (
                                <div key={node.id} className={`relative p-6 rounded-xl border-2 transition-all duration-300 ${node.role === 'LEADER' ? 'border-purple-500 bg-purple-50 shadow-md transform scale-105' : 'border-gray-200 bg-white'}`}>
                                    {node.role === 'LEADER' && (
                                        <div className="absolute -top-3 left-1/2 transform -translate-x-1/2 bg-purple-600 text-white text-xs font-bold px-3 py-1 rounded-full shadow-sm flex items-center gap-1">
                                            <Shield size={12} /> LEADER
                                        </div>
                                    )}
                                    <div className="flex justify-between items-start mb-4">
                                        <div>
                                            <h3 className="font-bold text-lg text-gray-800">{node.id}</h3>
                                            <p className="text-xs text-gray-500">{node.ip}</p>
                                        </div>
                                        <div className={`h-3 w-3 rounded-full ${node.status === 'ONLINE' ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                                    </div>

                                    <div className="space-y-3">
                                        <div>
                                            <div className="flex justify-between text-xs mb-1">
                                                <span className="text-gray-500">Traffic Load</span>
                                                <span className="font-bold text-gray-700">{node.status === 'ONLINE' ? node.load : 0}%</span>
                                            </div>
                                            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                                                <div
                                                    className={`h-full rounded-full transition-all duration-500 ${node.role === 'LEADER' ? 'bg-purple-500' : 'bg-gray-400'}`}
                                                    style={{ width: `${node.status === 'ONLINE' ? node.load : 0}%` }}
                                                />
                                            </div>
                                        </div>

                                        <button
                                            onClick={() => toggleNode(node.id)}
                                            className={`w-full py-2 rounded-lg text-xs font-bold transition ${node.status === 'ONLINE' ? 'bg-red-100 text-red-600 hover:bg-red-200' : 'bg-green-100 text-green-600 hover:bg-green-200'}`}
                                        >
                                            {node.status === 'ONLINE' ? 'STOP NODE' : 'START NODE'}
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>

                        <div className="flex justify-center">
                            <button
                                onClick={switchLeader}
                                className="bg-purple-600 text-white px-6 py-3 rounded-xl font-bold hover:bg-purple-700 transition shadow-lg flex items-center gap-2"
                            >
                                <RefreshCw size={20} />
                                FORCE LEADER ELECTION
                            </button>
                        </div>
                    </div>

                </div>
            </div>
        </div>
    );
};

export default AdminPanel;
