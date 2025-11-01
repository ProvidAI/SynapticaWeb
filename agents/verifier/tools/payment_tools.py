"""Payment release tools for Verifier agent."""

import os
from typing import Any, Dict, cast
from datetime import datetime
from decimal import Decimal

from shared.hedera import get_hedera_client
from shared.protocols import (
    X402Payment,
    PaymentRequest,
    PaymentStatus,
    build_payment_refund_message,
    build_payment_release_message,
    new_thread_id,
    publish_message,
)
from shared.database import SessionLocal, Payment
from shared.database.models import PaymentStatus as DBPaymentStatus


async def release_payment(payment_id: str, verification_notes: str = "") -> Dict[str, Any]:
    """
    Release an authorized payment after successful verification.

    Args:
        payment_id: Payment ID to release
        verification_notes: Optional notes about verification

    Returns:
        Payment release result
    """
    db = SessionLocal()
    try:
        payment = db.query(Payment).filter(Payment.id == payment_id).first()

        if not payment:
            return {"success": False, "error": f"Payment {payment_id} not found"}

        payment_row: Any = payment

        if payment_row.status != DBPaymentStatus.AUTHORIZED:
            return {
                "success": False,
                "error": f"Payment not authorized. Current status: {payment_row.status.value}",
            }

        # Get x402 payment handler
        hedera_client = get_hedera_client()
        x402 = X402Payment(hedera_client)

        metadata = dict(cast(Dict[str, Any], payment_row.metadata or {}))
        thread_id = metadata.get("a2a_thread_id") or new_thread_id(
            str(payment_row.task_id),
            payment_id,
        )
        verifier_agent_id = metadata.get("verifier_agent_id") or os.getenv(
            "VERIFIER_AGENT_ID",
            "verifier-agent",
        )
        verifier_private_key = (
            os.getenv("VERIFIER_PRIVATE_KEY")
            or os.getenv("TASK_ESCROW_OPERATOR_PRIVATE_KEY")
        )
        if verifier_private_key:
            metadata["verifier_private_key"] = verifier_private_key

        # Create payment request
        payment_request = PaymentRequest(
            payment_id=payment_id,
            from_account=os.getenv("HEDERA_ACCOUNT_ID", ""),
            to_account=metadata.get("to_hedera_account", ""),
            amount=Decimal(str(payment_row.amount)),
            description=metadata.get("description", ""),
            metadata=metadata,
        )

        authorization_id = cast(str, payment_row.authorization_id)

        # Release payment
        receipt = await x402.release_payment(authorization_id, payment_request)

        # Update payment record
        payment_row.status = DBPaymentStatus(receipt.status.value)
        payment_row.transaction_id = receipt.transaction_id
        payment_row.completed_at = datetime.utcnow()

        updated_metadata = dict(metadata)
        updated_metadata["verification_notes"] = verification_notes
        updated_metadata["receipt"] = {
            "transaction_id": receipt.transaction_id,
            "timestamp": receipt.timestamp,
            "details": receipt.metadata,
        }

        release_message = build_payment_release_message(
            payment_id=payment_id,
            task_id=str(payment_row.task_id),
            amount=Decimal(str(payment_row.amount)),
            currency=str(payment_row.currency),
            from_agent=str(verifier_agent_id),
            to_agent=str(payment_row.from_agent_id),
            transaction_id=receipt.transaction_id,
            status=payment_row.status.value,
            verification_notes=verification_notes,
            thread_id=thread_id,
        )

        release_payload = release_message.to_dict()
        messages = dict(cast(Dict[str, Any], updated_metadata.get("a2a_messages") or {}))
        messages[release_message.type] = release_payload
        updated_metadata["a2a_thread_id"] = thread_id
        updated_metadata["a2a_messages"] = messages
        updated_metadata.setdefault("verifier_agent_id", verifier_agent_id)
        payment_row.metadata = updated_metadata

        publish_message(release_message, tags=("payment", "released"))

        db.commit()
        db.refresh(payment)

        return {
            "success": True,
            "payment_id": payment_id,
            "transaction_id": receipt.transaction_id,
            "status": payment_row.status.value,
            "amount": payment_row.amount,
            "currency": payment_row.currency,
            "message": "Payment released successfully",
            "a2a": {
                "thread_id": thread_id,
                "release_message": release_message.to_dict(),
            },
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to release payment: {str(e)}",
        }
    finally:
        db.close()


async def reject_and_refund(
    payment_id: str, rejection_reason: str
) -> Dict[str, Any]:
    """
    Reject task results and mark payment for refund.

    Args:
        payment_id: Payment ID
        rejection_reason: Reason for rejection

    Returns:
        Rejection result
    """
    db = SessionLocal()
    try:
        payment = db.query(Payment).filter(Payment.id == payment_id).first()

        if not payment:
            return {"success": False, "error": f"Payment {payment_id} not found"}

        payment_row: Any = payment
        metadata = dict(cast(Dict[str, Any], payment_row.metadata or {}))
        thread_id = metadata.get("a2a_thread_id") or new_thread_id(
            str(payment_row.task_id),
            payment_id,
        )
        verifier_agent_id = metadata.get("verifier_agent_id") or os.getenv(
            "VERIFIER_AGENT_ID",
            "verifier-agent",
        )
        verifier_private_key = (
            os.getenv("VERIFIER_PRIVATE_KEY")
            or os.getenv("TASK_ESCROW_OPERATOR_PRIVATE_KEY")
        )
        if verifier_private_key:
            metadata["verifier_private_key"] = verifier_private_key

        payment_request = PaymentRequest(
            payment_id=payment_id,
            from_account=os.getenv("HEDERA_ACCOUNT_ID", ""),
            to_account=metadata.get("to_hedera_account", ""),
            amount=Decimal(str(payment_row.amount)),
            description=metadata.get("description", ""),
            metadata=metadata,
        )

        hedera_client = get_hedera_client()
        x402 = X402Payment(hedera_client)

        receipt = await x402.approve_refund(payment_request)

        payment_row.status = DBPaymentStatus(receipt.status.value)
        payment_row.transaction_id = receipt.transaction_id
        payment_row.completed_at = datetime.utcnow()

        updated_metadata = dict(metadata)
        updated_metadata["rejection_reason"] = rejection_reason
        updated_metadata["rejected_at"] = datetime.utcnow().isoformat()
        updated_metadata["refund_receipt"] = {
            "transaction_id": receipt.transaction_id,
            "timestamp": receipt.timestamp,
            "details": receipt.metadata,
        }

        refund_message = build_payment_refund_message(
            payment_id=payment_id,
            task_id=str(payment_row.task_id),
            amount=Decimal(str(payment_row.amount)),
            currency=str(payment_row.currency),
            from_agent=str(verifier_agent_id),
            to_agent=str(payment_row.from_agent_id),
            transaction_id=receipt.transaction_id,
            status=payment_row.status.value,
            rejection_reason=rejection_reason,
            thread_id=thread_id,
        )

        refund_payload = refund_message.to_dict()
        messages = dict(cast(Dict[str, Any], updated_metadata.get("a2a_messages") or {}))
        messages[refund_message.type] = refund_payload
        updated_metadata["a2a_thread_id"] = thread_id
        updated_metadata["a2a_messages"] = messages
        updated_metadata.setdefault("verifier_agent_id", verifier_agent_id)
        payment_row.metadata = updated_metadata

        publish_message(refund_message, tags=("payment", "refunded"))

        db.commit()
        db.refresh(payment)

        return {
            "success": receipt.status == PaymentStatus.REFUNDED,
            "payment_id": payment_id,
            "status": payment_row.status.value,
            "rejection_reason": rejection_reason,
            "message": "Refund approved on-chain" if receipt.status == PaymentStatus.REFUNDED else "Refund approval recorded",
            "a2a": {
                "thread_id": thread_id,
                "refund_message": refund_message.to_dict(),
            },
        }

    finally:
        db.close()
