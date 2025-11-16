/**
 * API client for ProvidAI backend
 */

const API_BASE_URL = '/api';

export interface AgentSummary {
  agent_id: string;
  name: string;
  agent_type: string;
  description: string;
  capabilities: string[];
  status: string;
}

export interface CreateTaskRequest {
  description: string;
  attachments?: string[];
  budget_limit?: number;
  min_reputation?: number;
}

export interface TaskResponse {
  task_id: string;
  status: string;
  message?: string;
  error?: string;
}

export interface TaskStatusResponse {
  task_id: string;
  status: string;
  current_step?: string;
  progress?: Array<{
    step: string;
    status: string;
    timestamp: string;
    data?: any;
  }>;
  plan?: {
    capabilities?: string[];
    budgetLimit?: number;
    minReputation?: number;
    estimatedCost?: number;
  };
  selected_agent?: {
    agentId: string;
    name: string;
    description?: string;
    reputation: number;
    price: number;
    currency: string;
    capabilities: string[];
  };
  payment_details?: {
    paymentId: string;
    amount: number;
    currency: string;
    fromAccount: string;
    toAccount: string;
    agentName: string;
    description?: string;
  };
  execution_logs?: Array<{
    timestamp: string;
    message: string;
    source: string;
  }>;
  result?: {
    success: boolean;
    data?: any;
    error?: string;
    report?: string;
  };
  error?: string;
}

/**
 * Create a new task
 */
export async function createTask(request: CreateTaskRequest): Promise<TaskResponse> {
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
  const response = await fetch(`${backendUrl}/execute`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to create task' }));
    throw new Error(error.error || 'Failed to create task');
  }

  return response.json();
}

/**
 * List available agents from registry
 */
export async function getAgents(): Promise<AgentSummary[]> {
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
  const response = await fetch(`${backendUrl}/api/agents`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    cache: 'no-store',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to fetch agents' }));
    throw new Error(error.error || 'Failed to fetch agents');
  }

  return response.json();
}

/**
 * Get task status
 */
export async function getTask(taskId: string): Promise<TaskStatusResponse> {
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
  const response = await fetch(`${backendUrl}/api/tasks/${taskId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Task not found' }));
    throw new Error(error.error || 'Task not found');
  }

  return response.json();
}

/**
 * Poll task status until completion or error
 */
export async function pollTaskStatus(
  taskId: string,
  onStatusUpdate?: (status: TaskStatusResponse) => void,
  pollInterval: number = 2000,
  maxAttempts: number = 150 // 5 minutes with 2s interval
): Promise<TaskStatusResponse> {
  let attempts = 0;

  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        attempts++;
        const status = await getTask(taskId);

        // Notify caller of status update
        if (onStatusUpdate) {
          onStatusUpdate(status);
        }

        // Check if task is complete
        const normalizedStatus = status.status?.toLowerCase();
        if (normalizedStatus === 'completed' || normalizedStatus === 'failed') {
          resolve(status);
          return;
        }

        // Check if max attempts reached
        if (attempts >= maxAttempts) {
          reject(new Error('Polling timeout: task did not complete'));
          return;
        }

        // Continue polling
        setTimeout(poll, pollInterval);
      } catch (error) {
        reject(error);
      }
    };

    poll();
  });
}

/**
 * Approve a payment
 */
export async function approvePayment(paymentId: string): Promise<{ success: boolean; message?: string; error?: string }> {
  const response = await fetch(`${API_BASE_URL}/payments/${paymentId}/approve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to approve payment' }));
    throw new Error(error.error || 'Failed to approve payment');
  }

  return response.json();
}

/**
 * Reject a payment
 */
export async function rejectPayment(paymentId: string, reason?: string): Promise<{ success: boolean; message?: string; error?: string }> {
  const response = await fetch(`${API_BASE_URL}/payments/${paymentId}/reject`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ reason }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to reject payment' }));
    throw new Error(error.error || 'Failed to reject payment');
  }

  return response.json();
}
