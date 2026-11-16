# Performance and Reliability Documentation

## System Requirements

### CPU
- **Minimum**: 2 cores
- **Recommended**: 4+ cores for concurrent screening of multiple resumes

### RAM
- **Minimum**: 4 GB
- **Recommended**: 8 GB for semantic matching with sentence-transformers
- **Note**: Sentence-transformers model (all-MiniLM-L6-v2) requires ~500MB RAM when loaded

### Storage
- **Model Cache**: ~120MB for sentence-transformers model (cached after first download)
- **Database**: PostgreSQL storage for resumes and screening results

## Performance Optimizations

### 1. Model Caching
- **Implementation**: `SemanticMatchingService` uses `@functools.lru_cache` for model loading
- **Benefit**: Model loaded once per process, reused for all requests
- **Location**: `app/services/semantic_matching_service.py`

### 2. Evidence Extraction
- **Deterministic**: Section detection and evidence extraction are deterministic
- **No External Calls**: All processing is local, no API calls
- **Complexity**: O(n) where n is resume length

### 3. Skill Matching
- **Normalization**: Skills normalized once per resume
- **Alternative Detection**: Alternative patterns detected during job analysis
- **Complexity**: O(m * k) where m is resume skills, k is job skills

## Expected Performance

### Single Resume Screening
- **Without Semantic**: ~100-500ms
- **With Semantic**: ~500-2000ms (first request includes model load)
- **Subsequent Semantic Requests**: ~200-500ms (model cached)

### Batch Screening (10 Resumes)
- **Without Semantic**: ~1-5 seconds
- **With Semantic**: ~2-10 seconds

## Scalability Considerations

### Current Limitations
- **Single-Process**: Model loaded in-process, not shared across workers
- **No Distributed Caching**: JD embeddings not cached across requests
- **Synchronous Processing**: Each resume processed sequentially

### Recommended Improvements for Scale
1. **Model Server**: Run sentence-transformers in separate service
2. **Redis Cache**: Cache JD embeddings and skill extraction results
3. **Async Processing**: Use Celery for background screening
4. **Database Indexing**: Existing indexes on `overall_score`, `job_id`, `resume_id`

## Error Handling

### Semantic Matching Failures
- **Graceful Fallback**: System continues with TF-IDF + skill matching
- **Error Categorization**: DLL failures, import failures, model download failures
- **Logging**: Detailed error messages for debugging

### Resume Parsing Failures
- **Individual Failure**: One failed resume doesn't block batch processing
- **Error Reporting**: Failed resumes reported in `MatchingResponse`

## Reliability

### Idempotency
- **Screening Results**: Same resume + job produces consistent results
- **Evidence Extraction**: Deterministic based on resume text

### Data Integrity
- **Database Transactions**: Screening results saved in transactions
- **Cascade Deletes**: Resumes/jobs cascade delete screening results
- **Unique Constraints**: One screening result per (job, resume) pair

## Monitoring Recommendations

### Key Metrics
- Screening latency (p50, p95, p99)
- Semantic model load time
- Evidence extraction time
- Skill extraction accuracy (via evaluation)

### Logging
- Model load success/failure
- Semantic availability status
- Screening errors by type
