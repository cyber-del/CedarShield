from decimal import Decimal
from src.anomaly_monitor import canonical_hash_block, convert_decimals_to_primitives

GENESIS_PREV_HASH = "0" * 64


def verify_chain(records: list[dict]) -> tuple[bool, str, int]:
    """
    Validates a sequential cryptographic SHA-256 hash chain:
    1. Sequence numbers must be strictly consecutive (1, 2, 3, ...).
    2. Genesis block (seq 1) must have prev_hash == 0*64.
    3. Every block's record_hash must match canonical SHA-256 hash of its contents.
    4. For every block N > 1, prev_hash must strictly match block N-1's record_hash.
    """
    if not records:
        return True, "Chain is empty.", 0

    sorted_records = sorted(records, key=lambda x: int(x.get("sequence_number", 0)))

    for i, record in enumerate(sorted_records):
        seq = int(record.get("sequence_number", 0))
        expected_seq = i + 1
        if seq != expected_seq:
            return False, f"Sequence gap or out of order at index {i}: expected {expected_seq}, got {seq}", seq

        recorded_hash = record.get("record_hash")
        computed_hash = canonical_hash_block(record)
        if recorded_hash != computed_hash:
            return False, f"Record hash mismatch at block #{seq}: recorded={recorded_hash}, computed={computed_hash}", seq

        prev_hash = record.get("prev_hash")
        if i == 0:
            if prev_hash != GENESIS_PREV_HASH:
                return False, f"Genesis block #{seq} prev_hash invalid: {prev_hash}", seq
        else:
            prev_block_hash = sorted_records[i - 1].get("record_hash")
            if prev_hash != prev_block_hash:
                return False, f"Hash pointer broken at block #{seq}: points to {prev_hash}, but previous block hash is {prev_block_hash}", seq

    return True, "Hash chain mathematically verified.", len(sorted_records)


def build_sample_chain(length: int = 4) -> list[dict]:
    """
    Helper to construct a valid cryptographic SHA-256 hash chain.
    """
    chain = []
    prev_hash = GENESIS_PREV_HASH

    for seq in range(1, length + 1):
        block = {
            "sequence_number": str(seq),
            "run_id": f"run_{seq:02d}",
            "action": "process-refund",
            "amount": Decimal(str(500 * seq)),
            "principal": "arn:aws:iam::123456789012:role/CedarShield-FinanceAgent-Role",
            "status": "APPLIED" if seq % 2 != 0 else "MANUAL_REVIEW",
            "timestamp": f"2026-10-12T10:0{seq}:00Z",
            "prev_hash": prev_hash,
        }
        rec_hash = canonical_hash_block(block)
        block["record_hash"] = rec_hash
        chain.append(block)
        prev_hash = rec_hash

    return chain


class TestHashChain:
    """
    Unit tests for cryptographic linear SHA-256 hash chain calculation and tamper detection.
    """

    def test_pristine_chain_passes_verification(self):
        chain = build_sample_chain(length=4)
        is_valid, msg, count = verify_chain(chain)
        assert is_valid is True
        assert count == 4
        assert "verified" in msg.lower()

    def test_tampering_payload_field_fails_verification(self):
        chain = build_sample_chain(length=4)

        # Adversary modifies amount in block #2 from $1000 to $5000
        chain[1]["amount"] = Decimal("5000")

        is_valid, msg, bad_seq = verify_chain(chain)
        assert is_valid is False
        assert bad_seq == 2
        assert "Record hash mismatch at block #2" in msg

    def test_tampering_status_fails_verification(self):
        chain = build_sample_chain(length=4)

        # Adversary modifies status in block #2 from MANUAL_REVIEW to APPLIED
        chain[1]["status"] = "APPLIED"

        is_valid, msg, bad_seq = verify_chain(chain)
        assert is_valid is False
        assert bad_seq == 2
        assert "Record hash mismatch at block #2" in msg

    def test_recomputing_single_block_hash_breaks_downstream_prev_pointer(self):
        chain = build_sample_chain(length=4)

        # Adversary modifies block #2 AND recomputes block #2's hash
        chain[1]["amount"] = Decimal("9999")
        chain[1]["record_hash"] = canonical_hash_block(chain[1])

        # Block 2 itself now has matching record_hash, but Block 3's prev_hash points to old hash!
        is_valid, msg, bad_seq = verify_chain(chain)
        assert is_valid is False
        assert bad_seq == 3
        assert "Hash pointer broken at block #3" in msg

    def test_tampering_genesis_prev_hash_fails(self):
        chain = build_sample_chain(length=4)
        chain[0]["prev_hash"] = "1" * 64
        # Recompute hash for block 0
        chain[0]["record_hash"] = canonical_hash_block(chain[0])

        is_valid, msg, bad_seq = verify_chain(chain)
        assert is_valid is False
        assert bad_seq == 1
        assert "Genesis block #1 prev_hash invalid" in msg

    def test_convert_decimals_to_primitives(self):
        raw = {
            "int_val": Decimal("100"),
            "float_val": Decimal("100.5"),
            "nested": {"val": Decimal("50")},
            "lst": [Decimal("10"), Decimal("20.2")],
            "str_val": "text",
        }
        clean = convert_decimals_to_primitives(raw)
        assert clean["int_val"] == 100
        assert isinstance(clean["int_val"], int)
        assert clean["float_val"] == 100.5
        assert isinstance(clean["float_val"], float)
        assert clean["nested"]["val"] == 50
        assert clean["lst"] == [10, 20.2]
        assert clean["str_val"] == "text"
