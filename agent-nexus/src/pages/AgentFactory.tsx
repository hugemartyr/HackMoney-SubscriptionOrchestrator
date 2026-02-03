import { useState, useRef, useEffect } from "react";
import { addDays, format } from "date-fns";
import { Send, Sparkles, CreditCard, Crown, TrendingUp } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { saveAgent, addActivityLog, type Agent } from "@/lib/storage";
import { prepareSubscriptionChannelPlan, signOffchainUpdate, type SubscriptionChannelPlan } from "@/lib/nitrolite";

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  card?: {
    type: 'subscription';
    data: SubscriptionCardData;
  };
}

interface Template {
  id: string;
  name: string;
  description: string;
  icon: React.ElementType;
  prompt: string;
  type: Agent['type'];
}

interface SubscriptionPaymentPreview {
  label: string;
  date: string;
  signature: string;
}

interface SubscriptionCardData {
  durationDays: number;
  startDate: string;
  endDate: string;
  schedulePreview: SubscriptionPaymentPreview[];
  finalPayment: SubscriptionPaymentPreview;
  channelPlan: SubscriptionChannelPlan;
}

const templates: Template[] = [
  {
    id: 'subscription',
    name: 'Subscription Protocol Agent',
    description: 'Manages recurring payments and subscription lifecycles automatically',
    icon: CreditCard,
    prompt: 'Create a subscription agent that manages recurring payments. It should handle monthly billing cycles, retry failed payments, and send notifications before charges.',
    type: 'subscription',
  },
  {
    id: 'chess',
    name: 'Chess Settlement Agent',
    description: 'Automatically settles wagers from rated chess matches',
    icon: Crown,
    prompt: 'Create a chess settlement agent that monitors rated games on Chess.com, verifies outcomes, and automatically settles wagers between players based on match results.',
    type: 'chess',
  },
  {
    id: 'dca',
    name: 'DCA Trading Agent',
    description: 'Dollar-cost averaging automation for crypto assets',
    icon: TrendingUp,
    prompt: 'Create a DCA trading agent that performs weekly purchases of ETH at optimal times, managing a fixed dollar amount investment strategy with automatic execution.',
    type: 'dca',
  },
];

const mockResponses = [
  "I understand you want to create a new agent. Let me analyze your requirements...",
  "Based on your description, I'll configure the following:\n\n✓ **Agent Type**: Custom automation\n✓ **Triggers**: Event-based execution\n✓ **Settlement Logic**: Smart contract interactions\n\nShall I proceed with this configuration?",
  "Your agent has been created successfully! 🎉\n\nIt's now available in your **My Agents** dashboard. You can start, pause, or configure it at any time.",
];

const THREE_MONTH_DURATION_DAYS = 90;

const isThreeMonthSubscriptionRequest = (message: string) => {
  const normalized = message.toLowerCase();
  const hasSubscription = /subscription|sub\b/.test(normalized);
  const hasThreeMonth = /3\\s*-?\\s*month|three\\s*month|90\\s*day/.test(normalized);
  return hasSubscription && hasThreeMonth;
};

const buildSubscriptionCardData = async (): Promise<SubscriptionCardData> => {
  const startDate = new Date();
  const durationDays = THREE_MONTH_DURATION_DAYS;
  const endDate = addDays(startDate, durationDays);
  const channelPlan = await prepareSubscriptionChannelPlan(durationDays);

  const schedulePreview: SubscriptionPaymentPreview[] = [];
  for (let dayIndex = 0; dayIndex < 7; dayIndex += 1) {
    const date = addDays(startDate, dayIndex + 1);
    const label = `Day ${dayIndex + 1}`;
    const payload = `${label}_${format(date, "yyyy-MM-dd")}`;
    schedulePreview.push({
      label,
      date: format(date, "MMM d, yyyy"),
      signature: signOffchainUpdate(channelPlan.sessionKey, payload),
    });
  }

  const finalLabel = `Day ${durationDays}`;
  const finalPayload = `${finalLabel}_${format(endDate, "yyyy-MM-dd")}`;
  const finalPayment: SubscriptionPaymentPreview = {
    label: finalLabel,
    date: format(endDate, "MMM d, yyyy"),
    signature: signOffchainUpdate(channelPlan.sessionKey, finalPayload),
  };

  return {
    durationDays,
    startDate: format(startDate, "MMM d, yyyy"),
    endDate: format(endDate, "MMM d, yyyy"),
    schedulePreview,
    finalPayment,
    channelPlan,
  };
};

const getResponsesForRequest = (userMessage: string) => {
  if (isThreeMonthSubscriptionRequest(userMessage)) {
    return [
      "Got it. I'll generate a Subscription Protocol agent tailored for a 3-month plan.",
      "Configuration preview:\n\n✓ **Agent Type**: Subscription Protocol\n✓ **Settlement Logic**: Nitrolite State Channels (ERC-7824)\n✓ **Off-chain cadence**: Daily micropayments\n✓ **On-chain close**: Day 90\n\nProceeding with the channel plan now.",
      "Your subscription agent is ready! 🎉\n\nYou can review the schedule card below or manage it from **My Agents**.",
    ];
  }
  return mockResponses;
};

export default function AgentFactory() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleTemplateClick = (template: Template) => {
    setInput(template.prompt);
  };

  const simulateResponse = async (userMessage: string, template?: Template) => {
    setIsTyping(true);
    
    // Simulate typing delay
    const responses = getResponsesForRequest(userMessage);
    for (let i = 0; i < responses.length; i++) {
      await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 500));
      
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: responses[i],
      }]);
    }

    const needsThreeMonthSubscription = isThreeMonthSubscriptionRequest(userMessage);
    if (needsThreeMonthSubscription) {
      const subscriptionCard = await buildSubscriptionCardData();
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: "Here is the 3-month subscription payment schedule. A Nitrolite state channel is prepared for daily off-chain micropayments, with on-chain settlement after 90 days.",
        card: { type: 'subscription', data: subscriptionCard },
      }]);
    }

    // Create the agent
    const newAgent: Agent = {
      id: crypto.randomUUID(),
      name: template ? template.name : `Custom Agent ${Date.now()}`,
      type: template?.type || 'custom',
      status: 'active',
      description: userMessage.slice(0, 100),
      createdAt: new Date().toISOString(),
      config: {},
      stats: { transactions: 0, successRate: 100, totalValue: 0 },
    };

    saveAgent(newAgent);
    addActivityLog({
      agentId: newAgent.id,
      agentName: newAgent.name,
      action: 'Agent created',
      status: 'success',
      details: 'New agent deployed successfully',
    });

    setIsTyping(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isTyping) return;

    const userMessage = input.trim();
    const matchedTemplate = templates.find(t => t.prompt === userMessage);

    setMessages(prev => [...prev, {
      id: crypto.randomUUID(),
      role: 'user',
      content: userMessage,
    }]);
    setInput('');

    await simulateResponse(userMessage, matchedTemplate);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] md:h-[calc(100vh-6rem)] animate-fade-in">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Agent Factory</h1>
        <p className="text-muted-foreground mt-1">Describe what you need, and I'll create an agent for you</p>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-h-0">
        {messages.length === 0 ? (
          /* Empty State with Templates */
          <div className="flex-1 flex flex-col items-center justify-center">
            <div className="text-center mb-8">
              <div className="w-16 h-16 rounded-2xl gradient-emerald flex items-center justify-center mx-auto mb-4 glow-emerald">
                <Sparkles className="w-8 h-8 text-primary-foreground" />
              </div>
              <h2 className="text-xl font-semibold mb-2">Create a New Agent</h2>
              <p className="text-muted-foreground max-w-md">
                Describe what you want your agent to do, or pick a template below
              </p>
            </div>

            {/* Templates Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full max-w-4xl">
              {templates.map((template) => (
                <Card
                  key={template.id}
                  className="glass-card cursor-pointer hover:border-primary/50 hover:glow-emerald transition-all duration-300"
                  onClick={() => handleTemplateClick(template)}
                >
                  <CardHeader className="pb-3">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-primary/10">
                        <template.icon className="w-5 h-5 text-primary" />
                      </div>
                      <CardTitle className="text-base">{template.name}</CardTitle>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <CardDescription>{template.description}</CardDescription>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        ) : (
          /* Chat Messages */
          <div className="flex-1 overflow-y-auto space-y-4 pr-2">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] p-4 rounded-2xl ${
                    message.role === 'user'
                      ? 'bg-primary text-primary-foreground rounded-br-md'
                      : 'glass-card rounded-bl-md'
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  {message.card?.type === 'subscription' && (
                    <Card className="mt-3 border-primary/30 bg-background/80">
                      <CardHeader className="pb-2">
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-base">3-Month Subscription Schedule</CardTitle>
                          <Badge className="bg-primary/10 text-primary">Nitrolite</Badge>
                        </div>
                        <CardDescription>
                          Daily off-chain micropayments via ERC-7824 state channels, closing on day {message.card.data.durationDays}.
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                          <span>Start: {message.card.data.startDate}</span>
                          <span>End: {message.card.data.endDate}</span>
                          <span>Endpoint: {message.card.data.channelPlan.wsUrl}</span>
                        </div>
                        <div className="text-xs">
                          <div className="font-medium text-foreground">Session Key</div>
                          <div className="text-muted-foreground">
                            {message.card.data.channelPlan.sessionKey.id} (child agents sign off-chain updates automatically)
                          </div>
                        </div>
                        <div className="space-y-2 text-xs">
                          <div className="font-medium text-foreground">Payment Schedule Preview</div>
                          {message.card.data.schedulePreview.map((payment) => (
                            <div key={payment.label} className="flex items-center justify-between gap-4">
                              <div>{payment.label} · {payment.date}</div>
                              <div className="text-muted-foreground truncate max-w-[180px]">{payment.signature}</div>
                            </div>
                          ))}
                          <div className="flex items-center justify-between gap-4 border-t border-border pt-2">
                            <div>{message.card.data.finalPayment.label} · {message.card.data.finalPayment.date}</div>
                            <div className="text-muted-foreground truncate max-w-[180px]">{message.card.data.finalPayment.signature}</div>
                          </div>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Channel ready: {message.card.data.channelPlan.clientReady ? "Connected to Nitrolite client" : "Awaiting client connection"}.
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              </div>
            ))}
            {isTyping && (
              <div className="flex justify-start">
                <div className="glass-card p-4 rounded-2xl rounded-bl-md">
                  <div className="flex gap-1">
                    <div className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}

        {/* Input Area */}
        <form onSubmit={handleSubmit} className="mt-4">
          <div className="glass-card p-2 rounded-2xl">
            <div className="flex gap-2">
              <Textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Describe the agent you want to create..."
                className="min-h-[60px] max-h-[150px] resize-none border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit(e);
                  }
                }}
              />
              <Button
                type="submit"
                size="icon"
                className="self-end gradient-emerald hover:opacity-90 glow-emerald"
                disabled={!input.trim() || isTyping}
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
