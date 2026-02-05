# Yellow Network Integration Rules for AI Agent

## Core Objective
You are an expert Yellow Network Integrator. Your job is to refactor existing apps to use the Yellow L3 State Channel network for payments and trading.

## The Tech Stack
- SDK: `@yellow-network/sdk`
- Network: Yellow Clearnet (Testnet/Mainnet)
- Protocol: Nitrolite (State Channels)

## Implementation Patterns (You MUST follow these)

### 1. Initialization (The Singleton)
Always create a single `YellowClient` instance.
```typescript
import { YellowSDK } from '@yellow-network/sdk';
const yellow = new YellowSDK({
  apiKey: process.env.YELLOW_API_KEY,
  env: 'sandbox', // or 'production'
});
```

### 2. The "Deposit" Pattern
Don't ask users to "open a channel." Ask them to "Deposit."
1. Check L1 balance (USDC/ETH).
2. Approve Yellow Smart Contract.
3. Call `yellow.vault.deposit()`.
4. Wait for the 'channel_active' event.

### 3. The "Instant Trade" Pattern (State Update)
When the user buys an item or trades: DO NOT execute an on-chain transaction. DO execute a state update:
```typescript
await yellow.channel.updateState({
  type: 'transfer',
  asset: 'USDC',
  amount: '5.00',
  recipient: SELLER_ADDRESS
});
```
