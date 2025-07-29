# Simple pass-through mapper for evmd
# Since evmd is Cosmos-based, it might not use the same genesis format as Ethereum clients
# For now, we'll just pass through the input and let evmd handle it

# Converts decimal string to number.
def to_int:
  if . == null then . else .|tonumber end
;

# For evmd, just pass through the original genesis
# The evmd startup script will handle the conversion to Cosmos format
.