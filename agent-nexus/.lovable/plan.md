

# 🚀 Web3 Meta-Agent Factory Dashboard

A command center for AI agent orchestration with a "Calm Tech" aesthetic, dark theme, and emerald accents.

---

## 🎨 Design System

**Theme Foundation:**
- Dark-first theme with deep slate backgrounds (#0f172a, #1e293b)
- Trust-focused emerald accents (#10b981, #34d399) for CTAs and success states
- Subtle gradients and glass-morphism effects for depth
- Minimal borders, generous whitespace
- Inter or system fonts for clean readability

---

## 📱 Core Layout

**Responsive Sidebar Navigation:**
- Collapsible sidebar with icons when minimized
- Navigation items: Dashboard, Agent Factory, My Agents, Wallet Connect
- Emerald indicator for active page
- Mobile: Bottom tab bar or hamburger menu

---

## 📊 Page 1: Dashboard

**High-Level Stats Cards:**
- Active Agents (count with status indicators)
- Total Value Locked in unified liquidity pools
- Recent Settlements (24h transaction count)
- Performance metrics with subtle charts

**Activity Feed:**
- Recent agent actions and settlements
- Timestamp and status badges

---

## 🏭 Page 2: Agent Factory

**Intent-Centric Chat Interface:**
- Clean input area at bottom (like modern AI chat UX)
- Example prompts displayed when empty
- Chat history with user/assistant message bubbles
- Mock AI responses showing agent generation flow

**Pre-Built Templates Section:**
- **Subscription Protocol Agent** - Manages recurring payments
- **Chess Settlement Agent** - Handles game result settlements
- **DCA Trading Agent** - Dollar-cost averaging automation

Clicking a template → Fills the chat with a ready-to-customize prompt

---

## 🤖 Page 3: My Agents

**Agent Cards Grid:**
- Agent name, type, and status (Active/Paused/Stopped)
- Performance mini-stats
- Quick actions: Start, Pause, Configure, Delete

**Agent Detail View:**
- Configuration settings
- Activity log
- Performance charts

---

## 💼 Page 4: Wallet Connect

**Connection UI (Mock):**
- "Connect Wallet" prominent CTA
- Wallet selection modal (MetaMask, WalletConnect, etc.)
- Connected state showing mock address and balance
- Transaction history placeholder

---

## 💾 Backend (Supabase)

**Database Tables:**
- `agents` - Agent configurations and status
- `agent_templates` - Pre-built template definitions
- `agent_activity_logs` - Historical actions and settlements
- `user_settings` - User preferences

**Security:**
- Row Level Security policies for user-owned data
- Proper authentication flow

---

## 📱 Responsive Design

- **Desktop**: Full sidebar, multi-column layouts
- **Tablet**: Collapsible sidebar, adaptive grids
- **Mobile**: Bottom navigation, single-column, touch-optimized

