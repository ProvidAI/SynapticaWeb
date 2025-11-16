import React from 'react';
import { RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';

interface RetryProgressIndicatorProps {
  currentAttempt: number;
  maxAttempts: number;
  status?: 'running' | 'failed' | 'success';
  className?: string;
}

export function RetryProgressIndicator({
  currentAttempt,
  maxAttempts,
  status = 'running',
  className = '',
}: RetryProgressIndicatorProps) {
  const percentage = (currentAttempt / maxAttempts) * 100;

  return (
    <div className={cn('flex items-center gap-3', className)}>
      <div className="relative w-12 h-12">
        {/* Background circle */}
        <svg className="w-12 h-12 transform -rotate-90">
          <circle
            cx="24"
            cy="24"
            r="20"
            stroke="currentColor"
            strokeWidth="4"
            fill="none"
            className="text-gray-200"
          />
          {/* Progress circle */}
          <circle
            cx="24"
            cy="24"
            r="20"
            stroke="currentColor"
            strokeWidth="4"
            fill="none"
            strokeDasharray={`${2 * Math.PI * 20}`}
            strokeDashoffset={`${2 * Math.PI * 20 * (1 - percentage / 100)}`}
            className={cn(
              'transition-all duration-300',
              status === 'running' && 'text-blue-500',
              status === 'failed' && 'text-red-500',
              status === 'success' && 'text-green-500'
            )}
            strokeLinecap="round"
          />
        </svg>

        {/* Center icon/text */}
        <div className="absolute inset-0 flex items-center justify-center">
          {status === 'running' ? (
            <RefreshCw className={cn('w-5 h-5 text-blue-600 animate-spin')} />
          ) : (
            <span className={cn(
              'text-xs font-bold',
              status === 'failed' && 'text-red-600',
              status === 'success' && 'text-green-600'
            )}>
              {currentAttempt}/{maxAttempts}
            </span>
          )}
        </div>
      </div>

      <div className="flex flex-col">
        <span className={cn(
          'text-sm font-semibold',
          status === 'running' && 'text-blue-700',
          status === 'failed' && 'text-red-700',
          status === 'success' && 'text-green-700'
        )}>
          {status === 'running' && `Retry ${currentAttempt} of ${maxAttempts}`}
          {status === 'failed' && `Failed after ${currentAttempt} attempts`}
          {status === 'success' && `Succeeded on attempt ${currentAttempt}`}
        </span>
        <span className="text-xs text-gray-600">
          {status === 'running' && 'Attempting alternative approach...'}
          {status === 'failed' && 'Maximum retries reached'}
          {status === 'success' && 'Task completed successfully'}
        </span>
      </div>
    </div>
  );
}

interface RetryDotsProps {
  currentAttempt: number;
  maxAttempts: number;
  className?: string;
}

export function RetryDots({
  currentAttempt,
  maxAttempts,
  className = '',
}: RetryDotsProps) {
  return (
    <div className={cn('flex items-center gap-1.5', className)}>
      {Array.from({ length: maxAttempts }).map((_, index) => (
        <div
          key={index}
          className={cn(
            'w-2 h-2 rounded-full transition-all duration-300',
            index < currentAttempt
              ? 'bg-blue-500 scale-100'
              : 'bg-gray-300 scale-75'
          )}
        />
      ))}
    </div>
  );
}
