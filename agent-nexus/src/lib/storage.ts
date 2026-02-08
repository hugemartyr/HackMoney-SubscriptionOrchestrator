// LocalStorage-based persistence for agents and settings

export interface Agent {
  id: string;
  name: string;
  type: 'subscription' | 'chess' | 'dca' | 'custom';
  status: 'active' | 'paused' | 'stopped';
  description: string;
  createdAt: string;
  config: Record<string, unknown>;
  stats: {
    transactions: number;
    successRate: number;
    totalValue: number;
  };
}

export interface ActivityLog {
  id: string;
  agentId: string;
  agentName: string;
  action: string;
  timestamp: string;
  status: 'success' | 'pending' | 'failed';
  details?: string;
}

const AGENTS_KEY = 'meta-agent-factory-agents';
const ACTIVITY_KEY = 'meta-agent-factory-activity';
const WALLET_KEY = 'meta-agent-factory-wallet';

// Agent operations
export function getAgents(): Agent[] {
  const stored = localStorage.getItem(AGENTS_KEY);
  return stored ? JSON.parse(stored) : [];
}

export function saveAgent(agent: Agent): void {
  const agents = getAgents();
  const existingIndex = agents.findIndex(a => a.id === agent.id);
  if (existingIndex >= 0) {
    agents[existingIndex] = agent;
  } else {
    agents.push(agent);
  }
  localStorage.setItem(AGENTS_KEY, JSON.stringify(agents));
}

export function deleteAgent(agentId: string): void {
  const agents = getAgents().filter(a => a.id !== agentId);
  localStorage.setItem(AGENTS_KEY, JSON.stringify(agents));
}

export function updateAgentStatus(agentId: string, status: Agent['status']): void {
  const agents = getAgents();
  const agent = agents.find(a => a.id === agentId);
  if (agent) {
    agent.status = status;
    localStorage.setItem(AGENTS_KEY, JSON.stringify(agents));
  }
}

// Activity log operations
export function getActivityLogs(): ActivityLog[] {
  const stored = localStorage.getItem(ACTIVITY_KEY);
  return stored ? JSON.parse(stored) : [];
}

export function addActivityLog(log: Omit<ActivityLog, 'id' | 'timestamp'>): void {
  const logs = getActivityLogs();
  logs.unshift({
    ...log,
    id: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
  });
  // Keep only last 100 logs
  localStorage.setItem(ACTIVITY_KEY, JSON.stringify(logs.slice(0, 100)));
}

// Wallet operations
export interface WalletState {
  connected: boolean;
  address: string | null;
  balance: string | null;
  network: string | null;
}

export function getWalletState(): WalletState {
  const stored = localStorage.getItem(WALLET_KEY);
  return stored ? JSON.parse(stored) : {
    connected: false,
    address: null,
    balance: null,
    network: null,
  };
}

export function saveWalletState(state: WalletState): void {
  localStorage.setItem(WALLET_KEY, JSON.stringify(state));
}

// Generate mock data for demo
export function seedDemoData(): void {
  if (getAgents().length > 0) return;

  const demoAgents: Agent[] = [
    {
      id: crypto.randomUUID(),
      name: 'Netflix Subscription Bot',
      type: 'subscription',
      status: 'active',
      description: 'Manages recurring subscription payments for streaming services',
      createdAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
      config: { interval: 'monthly', amount: 15.99 },
      stats: { transactions: 24, successRate: 100, totalValue: 383.76 },
    },
    {
      id: crypto.randomUUID(),
      name: 'Chess.com Settlement',
      type: 'chess',
      status: 'active',
      description: 'Automatically settles wagers from rated chess matches',
      createdAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
      config: { platform: 'chess.com', minRating: 1200 },
      stats: { transactions: 156, successRate: 98.7, totalValue: 2340.50 },
    },
    {
      id: crypto.randomUUID(),
      name: 'ETH DCA Strategy',
      type: 'dca',
      status: 'paused',
      description: 'Weekly dollar-cost averaging into Ethereum',
      createdAt: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(),
      config: { asset: 'ETH', frequency: 'weekly', amount: 100 },
      stats: { transactions: 8, successRate: 100, totalValue: 800 },
    },
  ];

  demoAgents.forEach(saveAgent);

  const demoLogs: Omit<ActivityLog, 'id' | 'timestamp'>[] = [
    { agentId: demoAgents[0].id, agentName: 'Netflix Subscription Bot', action: 'Payment processed', status: 'success', details: '$15.99 transferred' },
    { agentId: demoAgents[1].id, agentName: 'Chess.com Settlement', action: 'Match settled', status: 'success', details: 'Won: +$25.00' },
    { agentId: demoAgents[1].id, agentName: 'Chess.com Settlement', action: 'Match settled', status: 'success', details: 'Lost: -$15.00' },
    { agentId: demoAgents[2].id, agentName: 'ETH DCA Strategy', action: 'Agent paused', status: 'pending', details: 'User initiated pause' },
  ];

  demoLogs.forEach(addActivityLog);
}
