/** 后端混合召回的可选诊断字段。 */
export interface Citation {
  id: string
  chunk_id: string
  document_id: string
  evidence_type?: 'faq' | 'spot' | 'route' | 'document' | 'weather' | 'tool'
  confidence?: number
  quality_reason?: string
  provider?: string | null
  tool_call_id?: string | null
  as_of?: string | null
  expires_at?: string | null
  status?: string
  source: {
    title?: string
    filename?: string
    type?: string
  }
  quote: string
  locator?: {
    section?: string
    page?: number | null
    char_start?: number | null
    char_end?: number | null
  }
  retrieval?: {
    route?: string
    vector_rank?: number | null
    keyword_rank?: number | null
    vector_score?: number | null
    keyword_score?: number | null
    fused_score?: number | null
  }
  index_version?: string
}

export interface RetrievalTrace {
  route?: string
  index_version?: string
  degraded?: boolean
  fallback_reason?: string | null
  latency_ms?: number
  candidate_count?: number
  vector_count?: number
  keyword_count?: number
  filtered_count?: number
  route_candidates?: string[]
  chosen_route?: string
  filter_reasons?: string[]
  manifest_id?: string | null
  answer_citation_ids?: string[]
  citation_validation?: 'not_checked' | 'valid' | 'not_present' | 'invalid_unknown_id' | 'no_evidence' | 'generation_failed' | 'empty_answer' | string
}
