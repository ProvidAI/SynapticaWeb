# ProvidAI Frontend

Modern Next.js frontend for the ProvidAI AI Agent Marketplace, built with React, Zustand, and shadcn/ui.

## Features

- 📊 **State Management**: Zustand store for managing complex multi-step task workflow
- 🎨 **Modern UI**: Built with shadcn/ui components and Tailwind CSS
- 🔄 **BFF Pattern**: Next.js API routes act as Backend-for-Frontend proxy
- 🚀 **Real-time Updates**: Polling-based task status updates with execution logs
- 💰 **x402 Payment Flow**: Integrated payment modal that delegates Hedera Testnet payments to the backend

## Tech Stack

- **Framework**: Next.js 14+ (App Router)
- **UI**: React 18, shadcn/ui, Tailwind CSS
- **State**: Zustand
- **Type Safety**: TypeScript

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn
- Backend API running on `http://localhost:8000` (or configure `NEXT_PUBLIC_BACKEND_URL`)

### Installation

```bash
cd frontend
npm install
```

### Configuration

Create a `.env.local` file:

```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### Building

```bash
npm run build
npm start
```

## Architecture

### State Management

The application uses Zustand for global state management. The `taskStore` manages:

- **Task Status**: IDLE → PLANNING → APPROVING_PLAN → NEGOTIATING → PAYING → EXECUTING → VERIFYING → COMPLETE/FAILED
- **Task Details**: Description, uploaded files, plan, selected agent
- **Payment**: Payment details and challenges
- **Execution**: Logs, progress, results

### API Routes (BFF)

Next.js API routes act as a Backend-for-Frontend layer:

- `POST /api/tasks` - Create new task and start orchestration
- `GET /api/tasks/[taskId]` - Get task status
- `POST /api/tasks/[taskId]/payment` - Proxy x402 payment authorization to backend Hedera handler

### Component Structure

```
app/
  layout.tsx          # Root layout with providers
  page.tsx            # Main application page
  providers.tsx       # React Query provider setup
  api/                # BFF API routes
    tasks/
      route.ts
      [taskId]/
        route.ts
        payment/
          route.ts

components/
  ui/                 # shadcn/ui components
  TaskForm.tsx        # Task creation form
  TaskStatusCard.tsx  # Status display with progress
  PaymentModal.tsx    # x402 payment modal
  TaskResults.tsx     # Results display

store/
  taskStore.ts        # Zustand state management

lib/
  api.ts              # API client functions
  utils.ts           # Utility functions
```

## User Flow

1. **Submit Task**: User enters task description and uploads file (optional)
2. **Planning**: Backend analyzes request and creates plan
3. **Approve Plan**: User reviews and approves the plan
4. **Negotiation**: Backend finds suitable agent from ERC-8004 registry
5. **Payment**: Payment modal appears and, once approved, the backend runs the Hedera Testnet transfer
6. **Execution**: Agent executes task, real-time logs displayed
7. **Verification**: Verifier validates results
8. **Complete**: Results displayed, user can rate agent

## Hedera Integration

- Payments use Hedera Testnet via backend-held credentials—no user wallet or signing flow is required.
- Frontend simply relays payment details to the backend once the user approves, keeping funds on the test network.
- Hedera network metadata is still surfaced in the UI (`HederaInfo` component) to highlight provenance.

### Payment Flow

1. Backend negotiator finds an agent and returns a payment challenge (amount, accounts, etc.).
2. Frontend displays the challenge and, on approval, forwards it to `/api/tasks/[taskId]/payment`.
3. Backend processes the Hedera Testnet transfer and continues the task execution.

## Development Notes

### Backend Integration

The frontend expects the backend to:

1. Return structured responses from `/execute` endpoint
2. Support task status polling via `/api/tasks/[taskId]`
3. Handle x402 payment challenges via `/api/tasks/[taskId]/execute`, with the frontend providing an `X-Payment` header that signals backend-handled Hedera payment authorization

### State Machine

The task workflow follows a strict state machine:

```
IDLE
  ↓ (user submits task)
PLANNING
  ↓ (plan created)
APPROVING_PLAN
  ↓ (user approves)
NEGOTIATING
  ↓ (agent found)
PAYING
  ↓ (payment authorized)
EXECUTING
  ↓ (execution complete)
VERIFYING
  ↓
COMPLETE / FAILED
```

### Error Handling

- Network errors are caught and displayed in the status card
- Payment errors show in the payment modal
- Task errors display in the results card

## Future Improvements

- [ ] WebSocket/SSE for real-time updates instead of polling
- [ ] File upload to IPFS or similar storage
- [ ] Enhanced agent selection UI with comparison
- [ ] Reputation visualization
- [ ] Payment history and receipts
- [ ] Task templates and saved configurations

## License

MIT
