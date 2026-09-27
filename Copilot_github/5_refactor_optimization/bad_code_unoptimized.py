

# Optimized approach: O(N) time complexity using a set for deduplication
def get_high_spenders(transactions):
    high_spenders = []
    seen = set()
    for t in transactions:
        if t['amount'] > 10000:
            user_id = t['user_id']
            if user_id not in seen:
                seen.add(user_id)
                high_spenders.append(user_id)
    return high_spenders