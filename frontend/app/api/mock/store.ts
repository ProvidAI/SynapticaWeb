export interface MockTask {
  id: string;
  title: string;
  description: string;
  status: string;
  created_by: string;
  assigned_to?: string;
  created_at: string;
  updated_at: string;
  result?: any;
}

// Simple in-memory task store for mock API routes.
export const mockTasks = new Map<string, MockTask>();
