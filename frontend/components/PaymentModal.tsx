'use client'

import { useState } from 'react'
import { AlertCircle } from 'lucide-react'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { useTaskStore } from '@/store/taskStore'
import { handlePaymentChallenge } from '@/lib/api'

export function PaymentModal() {
  const { paymentDetails, selectedAgent, taskId, setStatus, setPaymentDetails } = useTaskStore()
  const [error, setError] = useState<string | null>(null)
  const [isPending, setIsPending] = useState(false)

  if (!paymentDetails || !selectedAgent || !taskId) {
    return null
  }

  const handleApprove = async () => {
    try {
      setError(null)
      setIsPending(true)

      // Update status and forward payment details to backend for Hedera testnet processing
      setStatus('PAYING')

      // Backend handles Hedera transaction using its own testnet credentials
      await handlePaymentChallenge(
        taskId,
        {
          ...paymentDetails,
          description: paymentDetails.description ?? 'ProvidAI task payment',
        },
        'hedera-backend'
      )

      // Close modal
      setPaymentDetails(null)
    } catch (err: any) {
      setError(err.message || 'Failed to process payment')
      console.error('Payment processing error:', err)
    } finally {
      setIsPending(false)
    }
  }

  const handleCancel = () => {
    setPaymentDetails(null)
    setStatus('FAILED')
    setError('Payment cancelled by user')
  }

  const approveButtonLabel = isPending
    ? 'Processing...'
    : `Approve & Pay $${paymentDetails.amount.toFixed(2)}`

  return (
    <Dialog open={paymentDetails !== null} onOpenChange={(open) => !open && handleCancel()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Agent Found & Ready to Work</DialogTitle>
          <DialogDescription>
            To begin execution, you must approve payment for this amount. The payment will be processed on Hedera Testnet and funds will be held by the Verifier Agent until the work is successfully completed.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="p-4 bg-muted rounded-lg">
            <div className="space-y-2">
              <div>
                <span className="font-semibold">Agent:</span> {selectedAgent.name}
              </div>
              <div>
                <span className="font-semibold">Reputation:</span> {selectedAgent.reputation.toFixed(1)} stars
              </div>
              <div>
                <span className="font-semibold">Cost:</span> ${paymentDetails.amount.toFixed(2)} {paymentDetails.currency}
              </div>
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
              <AlertCircle className="h-4 w-4" />
              {error}
            </div>
          )}

        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleCancel} disabled={isPending}>
            Cancel
          </Button>
          <Button onClick={handleApprove} disabled={isPending}>
            {approveButtonLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
