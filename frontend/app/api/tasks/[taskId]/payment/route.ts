import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

// POST /api/tasks/[taskId]/payment - Handle x402 payment with signed transaction
export async function POST(
  request: NextRequest,
  { params }: { params: { taskId: string } }
) {
  try {
    const taskId = params.taskId;
    const signedPayment = request.headers.get('X-Payment');

    if (!signedPayment) {
      return NextResponse.json(
        { error: 'Signed payment header (X-Payment) is required' },
        { status: 400 }
      );
    }

    const paymentChallenge = await request.json();

    // Forward payment to backend executor with signed transaction
    // This would typically be forwarded to the executor_agent which received the 402
    const response = await fetch(`${BACKEND_URL}/api/tasks/${taskId}/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Payment': signedPayment,
      },
      body: JSON.stringify({
        payment_challenge: paymentChallenge,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { error: data.error || 'Payment processing failed' },
        { status: response.status }
      );
    }

    return NextResponse.json(data);
  } catch (error: any) {
    console.error('Error processing payment:', error);
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}

