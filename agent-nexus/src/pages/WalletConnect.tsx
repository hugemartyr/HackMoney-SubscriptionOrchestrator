import { useEffect, useMemo, useState } from "react";
import { Wallet, ExternalLink, Copy, Check, LogOut } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { getWalletState, saveWalletState, type WalletState } from "@/lib/storage";
import { ConnectButton } from "@rainbow-me/rainbowkit";
import { useAccount, useBalance, useChainId, useDisconnect } from "wagmi";
import { mainnet, sepolia, polygon, base } from "wagmi/chains";

const supportedChains = [mainnet, sepolia, polygon, base];
const chainById = new Map(supportedChains.map(chain => [chain.id, chain]));

const truncateAddress = (address: string) => {
  if (address.length <= 10) return address;
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
};

const getExplorerBaseUrl = (chainId: number) => {
  const chain = chainById.get(chainId);
  return chain?.blockExplorers?.default.url ?? "https://etherscan.io";
};

const mockTransactions = [
  { id: '1', type: 'Agent Deploy', amount: '-0.012 ETH', time: '2 hours ago', status: 'success' },
  { id: '2', type: 'Settlement', amount: '+0.25 ETH', time: '5 hours ago', status: 'success' },
  { id: '3', type: 'DCA Purchase', amount: '-0.1 ETH', time: '1 day ago', status: 'success' },
  { id: '4', type: 'Subscription', amount: '-0.008 ETH', time: '3 days ago', status: 'success' },
];

export default function WalletConnect() {
  const [wallet, setWallet] = useState<WalletState>(getWalletState);
  const [copied, setCopied] = useState(false);
  const { address, isConnected } = useAccount();
  const chainId = useChainId();
  const { disconnect } = useDisconnect();
  const { data: balanceData } = useBalance({
    address,
    query: { enabled: !!address },
  });

  const handleDisconnect = () => {
    const newState: WalletState = {
      connected: false,
      address: null,
      balance: null,
      network: null,
    };
    saveWalletState(newState);
    setWallet(newState);
    disconnect();
  };

  const handleCopy = () => {
    if (!wallet.address) return;
    navigator.clipboard.writeText(wallet.address);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formattedBalance = useMemo(() => {
    if (!balanceData) return null;
    const amount = Number(balanceData.formatted);
    return `${amount.toFixed(4)} ${balanceData.symbol}`;
  }, [balanceData]);

  useEffect(() => {
    if (isConnected && address) {
      const chainName = chainById.get(chainId)?.name ?? "Unknown";
      const newState: WalletState = {
        connected: true,
        address,
        balance: formattedBalance,
        network: chainName,
      };
      saveWalletState(newState);
      setWallet(newState);
    } else {
      const newState: WalletState = {
        connected: false,
        address: null,
        balance: null,
        network: null,
      };
      saveWalletState(newState);
      setWallet(newState);
    }
  }, [isConnected, address, chainId, formattedBalance]);

  const explorerUrl = wallet.address && chainId
    ? `${getExplorerBaseUrl(chainId)}/address/${wallet.address}`
    : null;

  if (!wallet.connected) {
    return (
      <div className="space-y-6 animate-fade-in">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold">Wallet Connect</h1>
          <p className="text-muted-foreground mt-1">Connect your wallet to interact with agents</p>
        </div>

        {/* Connect Card */}
        <Card className="glass-card max-w-lg mx-auto">
          <CardContent className="flex flex-col items-center py-16">
            <div className="w-20 h-20 rounded-2xl gradient-emerald flex items-center justify-center mb-6 glow-emerald">
              <Wallet className="w-10 h-10 text-primary-foreground" />
            </div>
            <h2 className="text-xl font-semibold mb-2">Connect Your Wallet</h2>
            <p className="text-muted-foreground text-center max-w-sm mb-8">
              Connect your Web3 wallet to deploy agents, manage funds, and track settlements
            </p>
            <ConnectButton />
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Wallet</h1>
          <p className="text-muted-foreground mt-1">Manage your connected wallet</p>
        </div>
        <Badge variant="secondary" className="bg-primary/20 text-primary w-fit">
          Connected
        </Badge>
      </div>

      {/* Wallet Info */}
      <Card className="glass-card">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl gradient-emerald flex items-center justify-center">
                <Wallet className="w-6 h-6 text-primary-foreground" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <CardTitle className="text-lg">{wallet.address ? truncateAddress(wallet.address) : ""}</CardTitle>
                  <button
                    onClick={handleCopy}
                    className="p-1 hover:bg-secondary/50 rounded transition-colors"
                  >
                    {copied ? (
                      <Check className="w-4 h-4 text-primary" />
                    ) : (
                      <Copy className="w-4 h-4 text-muted-foreground" />
                    )}
                  </button>
                  {explorerUrl && (
                    <a
                      href={explorerUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="p-1 hover:bg-secondary/50 rounded transition-colors"
                    >
                  <ExternalLink className="w-4 h-4 text-muted-foreground" />
                </a>
              )}
            </div>
            <CardDescription>{wallet.network}</CardDescription>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDisconnect}
              className="hover:bg-destructive/20 hover:text-destructive hover:border-destructive/30"
            >
              <LogOut className="w-4 h-4 mr-2" />
              Disconnect
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-secondary/30">
              <p className="text-sm text-muted-foreground mb-1">Balance</p>
              <p className="text-2xl font-bold">{wallet.balance ?? "—"}</p>
              <p className="text-sm text-muted-foreground">≈ $8,541.00</p>
            </div>
            <div className="p-4 rounded-xl bg-secondary/30">
              <p className="text-sm text-muted-foreground mb-1">Agent Deposits</p>
              <p className="text-2xl font-bold">0.45 ETH</p>
              <p className="text-sm text-muted-foreground">Across 3 agents</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Transaction History */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="text-lg">Recent Transactions</CardTitle>
          <CardDescription>Your agent-related transactions</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockTransactions.map((tx) => (
              <div
                key={tx.id}
                className="flex items-center justify-between p-3 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors"
              >
                <div>
                  <p className="font-medium">{tx.type}</p>
                  <p className="text-xs text-muted-foreground">{tx.time}</p>
                </div>
                <div className="text-right">
                  <p className={`font-medium ${tx.amount.startsWith('+') ? 'text-primary' : ''}`}>
                    {tx.amount}
                  </p>
                  <Badge variant="secondary" className="bg-primary/20 text-primary text-xs">
                    {tx.status}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
