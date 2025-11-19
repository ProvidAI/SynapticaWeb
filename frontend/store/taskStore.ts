import { create } from 'zustand';

export type TaskStatus =
  | 'IDLE'
  | 'PLANNING'
  | 'NEGOTIATING'
  | 'APPROVING_PLAN'
  | 'PAYING'
  | 'EXECUTING'
  | 'VERIFYING'
  | 'COMPLETE'
  | 'FAILED'
  | 'CANCELLED';

export interface TaskPlan {
  capabilities: string[];
  budgetLimit?: number;
  minReputation?: number;
  estimatedCost?: number;
}

export interface SelectedAgent {
  agentId: string;
  name: string;
  description?: string;
  reputation: number;
  price: number;
  currency: string;
  capabilities: string[];
}

export interface PaymentDetails {
  paymentId: string;
  amount: number;
  currency: string;
  fromAccount: string;
  toAccount: string;
  agentName: string;
  description?: string;
}

export interface ExecutionLog {
  timestamp: string;
  message: string;
  source: 'orchestrator' | 'negotiator' | 'executor' | 'verifier' | 'agent';
}

export interface TaskResult {
  success: boolean;
  data?: any;
  error?: string;
  report?: string;
}

export interface ProgressLog {
  step: string;
  status: string;
  timestamp: string;
  data?: any;
}

export interface VerificationData {
  todo_id: string;
  payment_id: string;
  quality_score: number;
  dimension_scores: {
    completeness?: number;
    correctness?: number;
    academic_rigor?: number;
    clarity?: number;
    innovation?: number;
    ethics?: number;
  };
  feedback: string;
  task_result: any;
  agent_name: string;
  ethics_passed: boolean;
}

interface TaskState {
  // Status
  status: TaskStatus;
  taskId: string | null;

  // Task details
  description: string;
  uploadedFile: File | null;

  // Planning
  plan: TaskPlan | null;
  todoList: string[];

  // Negotiation
  selectedAgent: SelectedAgent | null;
  paymentDetails: PaymentDetails | null;

  // Execution
  executionLogs: ExecutionLog[];
  progressLogs: ProgressLog[];

  // Verification
  verificationPending: boolean;
  verificationData: VerificationData | null;

  // Results
  result: TaskResult | null;

  // Error
  error: string | null;

  // Actions
  setStatus: (status: TaskStatus) => void;
  setTaskId: (taskId: string) => void;
  setDescription: (description: string) => void;
  setUploadedFile: (file: File | null) => void;
  setPlan: (plan: TaskPlan) => void;
  setTodoList: (todoList: string[]) => void;
  setSelectedAgent: (agent: SelectedAgent | null) => void;
  setPaymentDetails: (payment: PaymentDetails | null) => void;
  addExecutionLog: (log: ExecutionLog) => void;
  setProgressLogs: (logs: ProgressLog[]) => void;
  setVerificationPending: (pending: boolean) => void;
  setVerificationData: (data: VerificationData | null) => void;
  approveVerification: (taskId: string) => Promise<void>;
  rejectVerification: (taskId: string, reason?: string) => Promise<void>;
  setResult: (result: TaskResult) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const initialState = {
  status: 'IDLE' as TaskStatus,
  taskId: null,
  description: '',
  uploadedFile: null,
  plan: null,
  todoList: [],
  selectedAgent: null,
  paymentDetails: null,
  executionLogs: [],
  progressLogs: [],
  verificationPending: false,
  verificationData: null,
  result: null,
  error: null,
};

export const useTaskStore = create<TaskState>((set, get) => ({
  ...initialState,

  setStatus: (status) => set({ status }),
  setTaskId: (taskId) => set({ taskId }),
  setDescription: (description) => set({ description }),
  setUploadedFile: (uploadedFile) => set({ uploadedFile }),
  setPlan: (plan) => set({ plan }),
  setTodoList: (todoList) => set({ todoList }),
  setSelectedAgent: (selectedAgent) => set({ selectedAgent }),
  setPaymentDetails: (paymentDetails) => set({ paymentDetails }),
  addExecutionLog: (log) => set((state) => ({
    executionLogs: [...state.executionLogs, log],
  })),
  setProgressLogs: (progressLogs) => set({ progressLogs }),
  setVerificationPending: (verificationPending) => set({ verificationPending }),
  setVerificationData: (verificationData) => set({ verificationData }),

  approveVerification: async (taskId: string) => {
    try {
      const response = await fetch(`http://localhost:8000/api/tasks/${taskId}/approve_verification`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        throw new Error('Failed to approve verification');
      }

      set({ verificationPending: false, verificationData: null });
    } catch (error) {
      console.error('Error approving verification:', error);
      throw error;
    }
  },

  rejectVerification: async (taskId: string, reason: string = 'Rejected by reviewer') => {
    try {
      const response = await fetch(`http://localhost:8000/api/tasks/${taskId}/reject_verification?reason=${encodeURIComponent(reason)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        throw new Error('Failed to reject verification');
      }

      // Set status to CANCELLED (not FAILED) to show cancellation in UI
      set({ verificationPending: false, verificationData: null, status: 'CANCELLED' });
    } catch (error) {
      console.error('Error rejecting verification:', error);
      throw error;
    }
  },

  setResult: (result) => set({ result }),
  setError: (error) => set({ error }),
  reset: () => set(initialState),
}));
