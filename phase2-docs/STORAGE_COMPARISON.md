# Storage Cost Comparison for Conversation History

## Requirements

**Phase 2 Interactive Bot:**
- Store conversation history for context
- Fast lookup by conversation_id
- Auto-expire old conversations (7 days)
- Support archival for compliance/analysis

**Expected Load:**
- 50 conversations/month
- 10 messages per conversation = 500 messages/month
- Average 2KB per message = 1MB/month total
- Read pattern: Load recent messages (< 7 days old)
- Write pattern: Append new messages

---

## Option 1: DynamoDB On-Demand ⭐ (Recommended for Phase 2)

### Architecture
```
DynamoDB Table: Conversations
- Primary Key: conversation_id
- Attributes: user_id, messages[], created_at, ttl
- TTL enabled: Auto-delete after 7 days
```

### Cost Breakdown (Monthly)
```
Writes: 500 messages × $1.25/million = $0.000625
Reads:  1000 reads × $0.25/million  = $0.00025
Storage: 1MB × $0.25/GB            = $0.00025
-------------------------------------------
Total:                               $0.00137/month

Rounded up: ~$0.01/month
```

### Pros
- ✅ Fast lookups (single-digit millisecond latency)
- ✅ Auto-scaling (no capacity planning)
- ✅ TTL for auto-deletion (free)
- ✅ Consistent performance
- ✅ Good for interactive chat (need fast reads)

### Cons
- ❌ More expensive than S3 (but still cheap)
- ❌ 400KB item size limit (might need pagination for long conversations)

---

## Option 2: S3 Only (Cheapest)

### Architecture
```
S3 Bucket: aws-alert-intelligence-conversations
Key Structure: {user_id}/{date}/{conversation_id}.json

Example:
  U123ABC/2025-10-21/conv-001.json
```

### Cost Breakdown (Monthly)
```
Storage: 1MB × $0.023/GB              = $0.000023
PUT:     500 requests × $0.005/1000   = $0.0025
GET:     1000 requests × $0.0004/1000 = $0.0004
-------------------------------------------
Total:                                  $0.003/month

Rounded: ~$0.01/month
```

### Pros
- ✅ Extremely cheap
- ✅ No item size limits
- ✅ Simple architecture
- ✅ Good for archival
- ✅ Can use S3 Select for queries

### Cons
- ❌ Slower than DynamoDB (10-100ms vs 1-5ms)
- ❌ No native TTL (need lifecycle policies)
- ❌ Harder to query (no indexes)
- ❌ Not ideal for interactive chat (higher latency)

---

## Option 3: S3 + Lambda Caching (Hybrid)

### Architecture
```
S3: Long-term storage
Lambda: In-memory cache for active conversations

Lambda keeps last 10 conversations in memory:
{
  "conv-001": {...},
  "conv-002": {...}
}

Cache hit: < 1ms
Cache miss: Read from S3 (10-50ms)
```

### Cost Breakdown (Monthly)
```
S3 Storage: 1MB × $0.023/GB           = $0.000023
S3 PUT:     500 × $0.005/1000         = $0.0025
S3 GET:     ~100 (cache misses only)  = $0.00004
Lambda:     Included in existing cost = $0
-------------------------------------------
Total:                                  $0.003/month
```

### Pros
- ✅ Very cheap (similar to S3-only)
- ✅ Fast for active conversations (cache)
- ✅ No database needed
- ✅ Simple to implement

### Cons
- ❌ Cache is per-Lambda instance (not shared)
- ❌ Cold start loses cache
- ❌ More complex than pure S3 or DynamoDB

---

## Option 4: ElastiCache (Redis) - NOT RECOMMENDED

### Cost
```
Smallest node: cache.t4g.micro = $0.017/hour
Monthly: $0.017 × 24 × 30 = $12.24/month
```

### Verdict
- ❌ **WAY too expensive** for our use case
- ❌ Not serverless (always running)
- Only makes sense for high-volume (1000s of messages/day)

---

## Option 5: RDS Aurora Serverless v2 - NOT RECOMMENDED

### Cost
```
Min capacity: 0.5 ACU × $0.12/hour
Monthly: ~$43/month (even with auto-pause)
```

### Verdict
- ❌ **Extremely expensive** for our use case
- ❌ Overkill for simple key-value storage
- Only makes sense for complex relational queries

---

## Recommendation by Phase

### Phase 1: No Storage Needed ✅
- One-shot analysis
- No conversation history
- **Cost: $0**

### Phase 2: DynamoDB On-Demand ⭐
- Fast interactive chat
- Auto-scaling
- TTL for cleanup
- **Cost: ~$0.01/month**

### Alternative for Cost-Sensitive: S3 + Lambda Cache
- Slightly slower (acceptable for Slack bot)
- Even cheaper than DynamoDB
- **Cost: ~$0.003/month**

---

## Feature Comparison

| Feature | DynamoDB | S3 Only | S3 + Cache | ElastiCache | Aurora |
|---------|----------|---------|------------|-------------|---------|
| **Cost/month** | $0.01 | $0.003 | $0.003 | $12 | $43 |
| **Read Latency** | 1-5ms | 10-100ms | 1-100ms | <1ms | 5-10ms |
| **Serverless** | ✅ | ✅ | ✅ | ❌ | ⚠️ |
| **Auto-Scale** | ✅ | ✅ | ✅ | ❌ | ✅ |
| **TTL Support** | ✅ Native | ⚠️ Lifecycle | ⚠️ Lifecycle | ⚠️ Manual | ⚠️ Manual |
| **Query Complexity** | Simple | Simple | Simple | High | Very High |
| **Setup Complexity** | Low | Very Low | Medium | High | High |
| **Best For** | Interactive | Archival | Hybrid | High Volume | Complex Queries |

---

## Code Examples

### DynamoDB Implementation

```python
import boto3
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Conversations')

def save_message(conversation_id: str, user_id: str, role: str, content: str):
    """Save a message to conversation."""
    item = {
        'conversation_id': conversation_id,
        'user_id': user_id,
        'messages': [
            {'role': role, 'content': content, 'timestamp': int(datetime.now().timestamp())}
        ],
        'ttl': int((datetime.now() + timedelta(days=7)).timestamp())
    }

    # Append to existing conversation or create new
    table.update_item(
        Key={'conversation_id': conversation_id},
        UpdateExpression='SET messages = list_append(if_not_exists(messages, :empty), :msg), #ttl = :ttl',
        ExpressionAttributeNames={'#ttl': 'ttl'},
        ExpressionAttributeValues={
            ':msg': item['messages'],
            ':ttl': item['ttl'],
            ':empty': []
        }
    )

def load_conversation(conversation_id: str) -> list:
    """Load conversation history."""
    response = table.get_item(Key={'conversation_id': conversation_id})
    return response.get('Item', {}).get('messages', [])
```

### S3 + Lambda Cache Implementation

```python
import boto3
import json
from functools import lru_cache

s3 = boto3.client('s3')
BUCKET = 'aws-alert-intelligence-conversations'

# In-memory cache (per Lambda instance)
conversation_cache = {}

def save_message(conversation_id: str, user_id: str, role: str, content: str):
    """Save message to S3."""
    # Update cache
    if conversation_id not in conversation_cache:
        conversation_cache[conversation_id] = []

    conversation_cache[conversation_id].append({
        'role': role,
        'content': content,
        'timestamp': datetime.now().isoformat()
    })

    # Save to S3
    key = f"{user_id}/{datetime.now().date()}/{conversation_id}.json"
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=json.dumps(conversation_cache[conversation_id])
    )

def load_conversation(conversation_id: str, user_id: str) -> list:
    """Load conversation (cache or S3)."""
    # Check cache first
    if conversation_id in conversation_cache:
        return conversation_cache[conversation_id]

    # Load from S3
    try:
        key = f"{user_id}/{datetime.now().date()}/{conversation_id}.json"
        response = s3.get_object(Bucket=BUCKET, Key=key)
        messages = json.loads(response['Body'].read())

        # Update cache
        conversation_cache[conversation_id] = messages
        return messages
    except s3.exceptions.NoSuchKey:
        return []
```

---

## Lifecycle Management

### DynamoDB TTL (Automatic)

```python
# Configure TTL on table
dynamodb.update_time_to_live(
    TableName='Conversations',
    TimeToLiveSpecification={
        'Enabled': True,
        'AttributeName': 'ttl'
    }
)

# Items automatically deleted ~48 hours after TTL expires
# No cost for deletions
```

### S3 Lifecycle Policy (Semi-Automatic)

```python
# Define lifecycle rule
s3.put_bucket_lifecycle_configuration(
    Bucket=BUCKET,
    LifecycleConfiguration={
        'Rules': [
            {
                'Id': 'DeleteOldConversations',
                'Status': 'Enabled',
                'Expiration': {'Days': 7},
                'Filter': {'Prefix': ''}
            },
            {
                'Id': 'ArchiveToGlacier',
                'Status': 'Enabled',
                'Transitions': [
                    {'Days': 30, 'StorageClass': 'GLACIER'}
                ],
                'Filter': {'Prefix': 'archive/'}
            }
        ]
    }
)
```

---

## Cost Projection at Scale

### Scenario: 10x Traffic

**500 conversations/month, 5000 messages/month**

| Solution | Cost |
|----------|------|
| DynamoDB | $0.01 × 10 = **$0.10/month** |
| S3 Only | $0.003 × 10 = **$0.03/month** |
| S3 + Cache | $0.003 × 10 = **$0.03/month** |

### Scenario: 100x Traffic

**5000 conversations/month, 50,000 messages/month**

| Solution | Cost |
|----------|------|
| DynamoDB | $0.01 × 100 = **$1.00/month** |
| S3 Only | $0.003 × 100 = **$0.30/month** |
| S3 + Cache | $0.003 × 100 = **$0.30/month** |

**Still incredibly cheap!**

---

## Final Recommendation

### For Most Users: DynamoDB On-Demand
- Fast, reliable, simple
- Auto-scaling, TTL included
- **Cost: ~$0.01-0.10/month** (even at 10x scale)
- Negligible compared to LLM costs ($5-8/month)

### For Ultra-Cost-Conscious: S3 + Lambda Cache
- 3x cheaper than DynamoDB
- Acceptable latency for Slack (users won't notice 50ms vs 5ms)
- **Cost: ~$0.003-0.03/month**

### Trade-off Analysis

**Is $0.007/month savings worth the added complexity?**

Probably not. Go with DynamoDB unless:
- You're expecting 1000+ conversations/month
- Every penny matters
- You enjoy optimizing infrastructure

---

## Decision Matrix

Choose DynamoDB if:
- ✅ You want simple, proven solution
- ✅ You value fast response times
- ✅ You want minimal code complexity
- ✅ Cost difference is negligible to you

Choose S3 + Cache if:
- ✅ You're extremely cost-conscious
- ✅ 50-100ms latency is acceptable
- ✅ You want to minimize AWS bills
- ✅ You enjoy building custom solutions

**My recommendation: Start with DynamoDB, optimize later if needed.**

---

**Status:** Analysis Complete
**Recommended:** DynamoDB On-Demand for Phase 2
**Cost Impact:** Negligible (<1% of total system cost)
