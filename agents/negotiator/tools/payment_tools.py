"""x402 payment tools for Negotiator."""

import os
import uuid
from typing import Any, Dict, List, cast
from decimal import Decimal

from shared.hedera import (
    get_hedera_client,
    hedera_account_to_evm_address,
    HEDERA_SDK_AVAILABLE,
)
from shared.protocols import (
    X402Payment,
    PaymentRequest,
    build_payment_authorized_message,
    build_payment_proposal_message,
    new_thread_id,
    publish_message,
)
from shared.database import SessionLocal, Payment
from shared.database.models import PaymentStatus as DBPaymentStatus


async def create_payment_request(
    task_id: str,
    from_agent_id: str,
    to_agent_id: str,
    to_hedera_account: str,
    amount: float,
    description: str = "",
) -> Dict[str, Any]:
    """
    Create an x402 payment request.

    Args:
        task_id: Associated task ID
        from_agent_id: Paying agent ID
        to_agent_id: Receiving agent ID
        to_hedera_account: Hedera account ID of receiving agent
        amount: Payment amount in HBAR
        description: Payment description

    Returns:
        Payment request details
    """
    db = SessionLocal()
    try:
        payment_id = str(uuid.uuid4())
        from_account = os.getenv("HEDERA_ACCOUNT_ID")

        if not from_account:
            raise ValueError("HEDERA_ACCOUNT_ID not configured")

        marketplace_treasury = os.getenv("TASK_ESCROW_MARKETPLACE_TREASURY", "").strip()
        default_verifiers = os.getenv("TASK_ESCROW_DEFAULT_VERIFIERS", "").strip()

        verifier_addresses: List[str] = []
        for addr in (
            addr.strip()
            for addr in default_verifiers.split(",")
            if addr.strip()
        ):
            verifier_addresses.append(hedera_account_to_evm_address(addr))

        treasury_address: str | None = None
        if marketplace_treasury:
            treasury_address = hedera_account_to_evm_address(marketplace_treasury)

        if not verifier_addresses and treasury_address:
            verifier_addresses.append(treasury_address)

        approvals_required = int(os.getenv("TASK_ESCROW_DEFAULT_APPROVALS", "1") or 1)
        if approvals_required > len(verifier_addresses) and verifier_addresses:
            approvals_required = len(verifier_addresses)

        marketplace_fee_bps = int(os.getenv("TASK_ESCROW_MARKETPLACE_FEE_BPS", "0") or 0)
        verifier_fee_bps = int(os.getenv("TASK_ESCROW_VERIFIER_FEE_BPS", "0") or 0)

        # Create payment record
        thread_id = new_thread_id(task_id, payment_id)
        worker_address = hedera_account_to_evm_address(to_hedera_account)

        metadata: Dict[str, Any] = {
            "task_id": task_id,
            "description": description,
            "to_hedera_account": to_hedera_account,
            "worker_account_id": to_hedera_account,
            "worker_address": worker_address,
            "verifier_addresses": verifier_addresses,
            "approvals_required": approvals_required,
            "marketplace_fee_bps": marketplace_fee_bps,
            "verifier_fee_bps": verifier_fee_bps,
            "a2a_thread_id": thread_id,
        }
        if treasury_address:
            metadata["marketplace_treasury"] = treasury_address

        proposal_message = build_payment_proposal_message(
            payment_id=payment_id,
            task_id=task_id,
            amount=Decimal(str(amount)),
            currency="HBAR",
            from_agent=from_agent_id,
            to_agent=to_agent_id,
            verifier_addresses=verifier_addresses,
            approvals_required=approvals_required or 1,
            marketplace_fee_bps=marketplace_fee_bps,
            verifier_fee_bps=verifier_fee_bps,
            thread_id=thread_id,
        )
        proposal_payload = proposal_message.to_dict()
        metadata["a2a_messages"] = {proposal_message.type: proposal_payload}

        publish_message(proposal_message, tags=("payment", "proposal"))

        payment = Payment(  # type: ignore[call-arg]
            id=payment_id,
            task_id=task_id,
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            amount=amount,
            currency="HBAR",
            status=DBPaymentStatus.PENDING,
            meta=metadata,
        )

        db.add(payment)
        db.commit()
        db.refresh(payment)

        return {
            "payment_id": payment_id,
            "task_id": task_id,
            "from_agent": from_agent_id,
            "to_agent": to_agent_id,
            "amount": amount,
            "currency": "HBAR",
            "status": "pending",
            "description": description,
            "a2a": {
                "thread_id": thread_id,
                "proposal_message": proposal_message.to_dict(),
            },
        }
    finally:
        db.close()


async def authorize_payment(payment_id: str) -> Dict[str, Any]:
    """
    Authorize a payment (escrow pattern).

    This marks the payment as authorized and ready for release pending verification.

    Args:
        payment_id: Payment ID to authorize

    Returns:
        Authorization details
    """
    db = SessionLocal()
    try:
        payment = db.query(Payment).filter(Payment.id == payment_id).first()

        if not payment:
            raise ValueError(f"Payment {payment_id} not found")

        # Create payment request object
        payment_row: Any = payment
        metadata = dict(cast(Dict[str, Any], payment_row.meta or {}))
        thread_id = metadata.get("a2a_thread_id") or new_thread_id(
            str(payment_row.task_id),
            payment_id,
        )

        # Normalize worker and verifier addresses for legacy records.
        try:
            worker_address = metadata.get("worker_address")
            if worker_address:
                metadata["worker_address"] = hedera_account_to_evm_address(worker_address)
            elif metadata.get("to_hedera_account"):
                metadata["worker_address"] = hedera_account_to_evm_address(
                    metadata["to_hedera_account"]
                )
        except ValueError as exc:
            raise ValueError(f"Invalid worker address in payment metadata: {exc}") from exc

        verifiers = metadata.get("verifier_addresses") or []
        if isinstance(verifiers, list) and verifiers:
            try:
                metadata["verifier_addresses"] = [
                    hedera_account_to_evm_address(address) for address in verifiers
                ]
            except ValueError as exc:
                raise ValueError(f"Invalid verifier address in payment metadata: {exc}") from exc
        elif metadata.get("marketplace_treasury"):
            metadata["verifier_addresses"] = [
                hedera_account_to_evm_address(metadata["marketplace_treasury"])
            ]

        payment_request = PaymentRequest(
            payment_id=payment_id,
            from_account=os.getenv("HEDERA_ACCOUNT_ID", ""),
            to_account=metadata.get("worker_address", metadata.get("to_hedera_account", "")),
            amount=Decimal(str(payment.amount)),
            description=metadata.get("description", ""),
            metadata=metadata,
        )

        offline_mode = bool(os.getenv("X402_OFFLINE", "").strip()) or not HEDERA_SDK_AVAILABLE

        if offline_mode:
            auth_id = f"offline-{uuid.uuid4().hex[:12]}"
        else:
            hedera_client = get_hedera_client()
            x402 = X402Payment(hedera_client)
            auth_id = await x402.authorize_payment(payment_request)

        # Update payment record
        payment_row.authorization_id = auth_id
        payment_row.transaction_id = auth_id
        payment_row.status = DBPaymentStatus.AUTHORIZED

        authorized_message = build_payment_authorized_message(
            payment_id=payment_id,
            task_id=str(payment_row.task_id),
            amount=Decimal(str(payment.amount)),
            currency=str(payment_row.currency),
            from_agent=str(payment_row.from_agent_id),
            to_agent=str(payment_row.to_agent_id),
            transaction_id=auth_id,
            thread_id=thread_id,
        )

        authorized_payload = authorized_message.to_dict()
        messages = dict(cast(Dict[str, Any], metadata.get("a2a_messages") or {}))
        messages[authorized_message.type] = authorized_payload
        metadata["a2a_thread_id"] = thread_id
        metadata["a2a_messages"] = messages
        payment_row.meta = metadata

        publish_message(authorized_message, tags=("payment", "authorized"))

        db.commit()
        db.refresh(payment)

        return {
            "payment_id": payment_id,
            "authorization_id": auth_id,
            "status": "authorized",
            "message": "Payment authorized. Waiting for verification to release funds.",
            "a2a": {
                "thread_id": thread_id,
                "authorized_message": authorized_message.to_dict(),
            },
        }
    finally:
        db.close()


async def get_payment_status(payment_id: str) -> Dict[str, Any]:
    """
    Get current payment status.

    Args:
        payment_id: Payment ID

    Returns:
        Payment status and details
    """
    db = SessionLocal()
    try:
        payment = db.query(Payment).filter(Payment.id == payment_id).first()

        if not payment:
            raise ValueError(f"Payment {payment_id} not found")

        payment_row: Any = payment
        metadata = dict(cast(Dict[str, Any], payment_row.meta or {}))
        a2a_info = None
        thread_id = metadata.get("a2a_thread_id")
        if thread_id or metadata.get("a2a_messages"):
            a2a_info = {
                "thread_id": thread_id,
                "messages": metadata.get("a2a_messages", {}),
            }

        completed_at_value = payment_row.completed_at
        completed_at_iso = (
            completed_at_value.isoformat() if completed_at_value is not None else None
        )

        return {
            "payment_id": str(payment_row.id),
            "task_id": str(payment_row.task_id),
            "status": payment_row.status.value,
            "amount": float(payment_row.amount),
            "currency": str(payment_row.currency),
            "transaction_id": payment_row.transaction_id,
            "authorization_id": payment_row.authorization_id,
            "created_at": payment_row.created_at.isoformat(),
            "completed_at": completed_at_iso,
            "a2a": a2a_info,
        }
    finally:
        db.close()
