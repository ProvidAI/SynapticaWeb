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
  | 'FAILED';

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
  result: null,
  error: null,
};

export const useTaskStore = create<TaskState>((set) => ({
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
  setResult: (result) => set({ result }),
  setError: (error) => set({ error }),
  reset: () => set(initialState),
}));
