def calculate_parity(data_bits, parity_type='even'):
    ones_count = data_bits.count('1')
    if parity_type == 'even':
        return '1' if ones_count % 2 != 0 else '0'
    else:
        return '1' if ones_count % 2 == 0 else '0'

def check_parity(data_with_parity, parity_type='even'):
    return calculate_parity(data_with_parity, parity_type) == '0'

def calculate_crc(data, divisor="1011"):
    crc_length = len(divisor) - 1
    dividend = list(data + '0' * crc_length)
    for i in range(len(data)):
        if dividend[i] == '1':
            for j in range(len(divisor)):
                dividend[i + j] = str(int(dividend[i + j]) ^ int(divisor[j]))
    return ''.join(dividend[-crc_length:])

def verify_crc(data_with_crc, divisor="1011"):
    dividend = list(data_with_crc)
    for i in range(len(data_with_crc) - len(divisor) + 1):
        if dividend[i] == '1':
            for j in range(len(divisor)):
                dividend[i + j] = str(int(dividend[i + j]) ^ int(divisor[j]))
    remainder = ''.join(dividend[-(len(divisor)-1):])
    return remainder == '0' * (len(divisor) - 1)

def encode_hamming(data):
    if len(data) != 4:
        data = data.zfill(4)[-4:]
    d = [int(b) for b in data]
    p1 = d[0] ^ d[1] ^ d[3]
    p2 = d[0] ^ d[2] ^ d[3]
    p4 = d[1] ^ d[2] ^ d[3]
    result = [p1, p2, d[0], p4, d[1], d[2], d[3]]
    return ''.join(str(b) for b in result)

def decode_hamming(encoded):
    if len(encoded) != 7:
        return None, 0, False
    bits = [int(b) for b in encoded]
    c1 = bits[0] ^ bits[2] ^ bits[4] ^ bits[6]
    c2 = bits[1] ^ bits[2] ^ bits[5] ^ bits[6]
    c4 = bits[3] ^ bits[4] ^ bits[5] ^ bits[6]
    error_pos = c4 * 4 + c2 * 2 + c1 * 1
    corrected = bits.copy()
    was_corrected = False
    if error_pos != 0:
        corrected[error_pos - 1] = 1 - corrected[error_pos - 1]
        was_corrected = True
    data = ''.join(str(corrected[i]) for i in [2, 4, 5, 6])
    return data, error_pos, was_corrected

def calculate_checksum(data, block_size=8):
    blocks = [data[i:i+block_size] for i in range(0, len(data), block_size)]
    if len(blocks[-1]) < block_size:
        blocks[-1] = blocks[-1].ljust(block_size, '0')
    total = 0
    for block in blocks:
        total += int(block, 2)
    max_val = (1 << block_size) - 1
    while total > max_val:
        carry = total >> block_size
        total = (total & max_val) + carry
    checksum = max_val - total
    return format(checksum, f'0{block_size}b')

def verify_checksum(data_with_checksum, block_size=8):
    blocks = [data_with_checksum[i:i+block_size] for i in range(0, len(data_with_checksum), block_size)]
    total = 0
    for block in blocks:
        if len(block) == block_size:
            total += int(block, 2)
    max_val = (1 << block_size) - 1
    while total > max_val:
        carry = total >> block_size
        total = (total & max_val) + carry
    return total == max_val

def int_to_binary(num, bits=4):
    return format(num, f'0{bits}b')

def binary_to_int(binary):
    return int(binary, 2)

def text_to_binary(text):
    return ''.join(format(ord(c), '08b') for c in text)

def binary_to_text(binary):
    chars = [binary[i:i+8] for i in range(0, len(binary), 8)]
    result = ''
    for c in chars:
        if len(c) == 8:
            try:
                result += chr(int(c, 2))
            except:
                result += '?'
    return result

def flip_bit(data, position):
    bits = list(data)
    if 0 <= position < len(bits):
        bits[position] = '1' if bits[position] == '0' else '0'
    return ''.join(bits)

def delete_random_bit(data):
    import random
    if len(data) <= 1:
        return '', 0
    pos = random.randint(0, len(data) - 1)
    return data[:pos] + data[pos+1:], pos

def encode_message(text, method='crc'):
    binary = text_to_binary(text)
    result = {'original_text': text, 'binary': binary, 'method': method, 'control_info': '', 'encoded_data': ''}
    
    if method == 'parity':
        encoded = ''
        for i in range(0, len(binary), 8):
            block = binary[i:i+8]
            if len(block) == 8:
                parity = calculate_parity(block)
                encoded += block + parity
        result['control_info'] = 'parity_bits'
        result['encoded_data'] = encoded
    elif method == 'crc':
        crc = calculate_crc(binary)
        result['control_info'] = crc
        result['encoded_data'] = binary + crc
    elif method == 'hamming':
        encoded = ''
        for i in range(0, len(binary), 4):
            block = binary[i:i+4]
            if len(block) == 4:
                hamming = encode_hamming(block)
                encoded += hamming
            else:
                encoded += block.ljust(4, '0')
        result['control_info'] = 'hamming_7_4'
        result['encoded_data'] = encoded
    elif method == 'checksum':
        checksum = calculate_checksum(binary)
        result['control_info'] = checksum
        result['encoded_data'] = binary + checksum
    return result

def decode_message(encoded_data, method='crc'):
    result = {'valid': True, 'errors_detected': False, 'errors_corrected': False, 'error_details': [], 'decoded_text': '', 'received_control': '', 'calculated_control': '', 'control_match': True}
    
    if method == 'parity':
        decoded = ''
        for i in range(0, len(encoded_data), 9):
            block = encoded_data[i:i+9]
            if len(block) >= 8:
                data = block[:8]
                received_parity = block[8] if len(block) > 8 else '0'
                calculated_parity = calculate_parity(data)
                result['received_control'] += received_parity
                result['calculated_control'] += calculated_parity
                if received_parity != calculated_parity:
                    result['errors_detected'] = True
                    result['error_details'].append(f'Parity error at block {i//9}')
                    result['control_match'] = False
                decoded += data
        result['decoded_text'] = binary_to_text(decoded)
    elif method == 'crc':
        if len(encoded_data) > 3:
            data = encoded_data[:-3]
            received_crc = encoded_data[-3:]
            calculated_crc = calculate_crc(data)
            result['received_control'] = received_crc
            result['calculated_control'] = calculated_crc
            result['control_match'] = (received_crc == calculated_crc)
            if not result['control_match']:
                result['errors_detected'] = True
                result['error_details'].append(f'CRC mismatch')
            result['decoded_text'] = binary_to_text(data)
    elif method == 'hamming':
        decoded = ''
        for i in range(0, len(encoded_data), 7):
            block = encoded_data[i:i+7]
            if len(block) == 7:
                data, error_pos, was_corrected = decode_hamming(block)
                if data:
                    decoded += data
                    if was_corrected:
                        result['errors_corrected'] = True
                        result['error_details'].append(f'Hamming corrected bit {error_pos}')
        result['decoded_text'] = binary_to_text(decoded)
        result['control_match'] = not result['errors_detected']
    elif method == 'checksum':
        if len(encoded_data) > 8:
            data = encoded_data[:-8]
            received_checksum = encoded_data[-8:]
            calculated_checksum = calculate_checksum(data)
            result['received_control'] = received_checksum
            result['calculated_control'] = calculated_checksum
            result['control_match'] = (received_checksum == calculated_checksum)
            if not result['control_match']:
                result['errors_detected'] = True
                result['error_details'].append('Checksum mismatch')
            result['decoded_text'] = binary_to_text(data)
    result['valid'] = not result['errors_detected'] or result['errors_corrected']
    return result

def encode_move(position, symbol):
    pos_binary = int_to_binary(position, 4)
    symbol_bit = '0' if symbol == 'X' else '1'
    data = pos_binary
    hamming = encode_hamming(data)
    crc = calculate_crc(hamming)
    parity = calculate_parity(hamming + crc)
    return {'position': position, 'symbol': symbol, 'binary': pos_binary, 'hamming': hamming, 'crc': crc, 'parity': parity, 'full_data': hamming + crc + parity}

def decode_move(full_data, expected_symbol=None):
    result = {'valid': True, 'errors': [], 'corrections': [], 'position': None, 'symbol': expected_symbol}
    if len(full_data) < 11:
        result['valid'] = False
        result['errors'].append('Data too short')
        return result
    hamming = full_data[:7]
    crc = full_data[7:10]
    parity = full_data[10] if len(full_data) > 10 else '0'
    parity_valid = check_parity(hamming + crc + parity)
    if not parity_valid:
        result['errors'].append('Parity check failed')
    crc_valid = verify_crc(hamming + crc)
    if not crc_valid:
        result['errors'].append('CRC check failed')
    decoded_data, error_pos, was_corrected = decode_hamming(hamming)
    if was_corrected:
        result['corrections'].append(f'Hamming corrected bit at position {error_pos}')
    if decoded_data:
        result['position'] = binary_to_int(decoded_data)
        if result['position'] > 8:
            result['position'] = result['position'] % 9
    if result['errors'] and not was_corrected:
        result['valid'] = False
    return result

if __name__ == "__main__":
    print("Testing Error Detection Algorithms")
    for method in ['parity', 'crc', 'hamming', 'checksum']:
        print(f"\n--- {method.upper()} ---")
        msg = "Hi"
        encoded = encode_message(msg, method)
        print(f"Original: {msg}")
        print(f"Encoded: {encoded['encoded_data'][:30]}...")
        decoded = decode_message(encoded['encoded_data'], method)
        print(f"Decoded: {decoded['decoded_text']}")
        print(f"Valid: {decoded['valid']}")
