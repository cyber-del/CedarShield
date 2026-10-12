import json
import hashlib
import boto3
from decimal import Decimal

REGION = 'ap-southeast-2'
TABLE_NAME = 'cedarshield-audit-log'

dynamodb = boto3.resource('dynamodb', region_name=REGION)
table = dynamodb.Table(TABLE_NAME)

def convert_decimals_to_primitives(obj):
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    if isinstance(obj, dict):
        return {k: convert_decimals_to_primitives(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_decimals_to_primitives(v) for v in obj]
    return obj

def compute_record_hash(record_data):
    canonical_data = {k: v for k, v in record_data.items() if k != 'record_hash'}
    clean_data = convert_decimals_to_primitives(canonical_data)
    canonical_json = json.dumps(clean_data, sort_keys=True, default=str)
    return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

def verify_audit_chain(verbose=True):
    print('=' * 80)
    print('CEDARSHIELD TAMPER-EVIDENT AUDIT CHAIN VERIFIER')
    print(f'Target Table: {TABLE_NAME} (Region: {REGION})')
    print('=' * 80)
    
    response = table.scan()
    items = response.get('Items', [])
    chain_records = [it for it in items if 'prev_hash' in it]
    chain_records.sort(key=lambda x: int(x.get('sequence_number', 0)))
    
    if not chain_records:
        print('[!] No chained audit records found in table.')
        return False
        
    print(f'Found {len(chain_records)} chained audit blocks in DynamoDB. Verifying cryptographic integrity...\n')
    
    chain_valid = True
    expected_prev_hash = '0' * 64
    
    for idx, rec in enumerate(chain_records):
        seq = int(rec.get('sequence_number', idx + 1))
        run_id = rec.get('run_id', 'unknown')
        stored_prev_hash = rec.get('prev_hash')
        stored_record_hash = rec.get('record_hash')
        timestamp = rec.get('timestamp', 'unknown')
        decision = rec.get('final_decision', rec.get('status', 'unknown'))
        
        if stored_prev_hash != expected_prev_hash:
            print(f'[FAIL] CHAIN BREAK AT BLOCK #{seq} (run_id: {run_id})')
            print(f'   Expected prev_hash: {expected_prev_hash}')
            print(f'   Stored prev_hash:   {stored_prev_hash}')
            chain_valid = False
            return False
            
        recomputed_hash = compute_record_hash(rec)
        if recomputed_hash != stored_record_hash:
            print(f'[FAIL] TAMPER / CORRUPTION DETECTED AT BLOCK #{seq} (run_id: {run_id})')
            print(f'   Stored record_hash:     {stored_record_hash}')
            print(f'   Recomputed record_hash: {recomputed_hash}')
            print(f'   The contents of block #{seq} have been tampered with or modified directly in DynamoDB!')
            chain_valid = False
            return False
            
        if verbose:
            print(f'[VALID] Block #{seq:02d} | Run: {run_id:<24} | Decision: {decision:<14} | Hash: {stored_record_hash[:16]}... | Prev: {stored_prev_hash[:16]}...')
            
        expected_prev_hash = stored_record_hash
        
    print('\n' + '-' * 80)
    print('VERIFICATION RESULT: ALL CRYPTOGRAPHIC HASHES AND LINKS VALID!')
    print(f'Total Blocks Verified: {len(chain_records)}')
    print(f'Latest Block Hash:     {expected_prev_hash}')
    print('Chain Status:          TAMPER-FREE & CRYPTOGRAPHICALLY INTACT')
    print('-' * 80)
    return True

if __name__ == '__main__':
    verify_audit_chain()
