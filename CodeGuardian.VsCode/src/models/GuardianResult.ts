export type Severity = 'critical' | 'error' | 'warning' | 'info';

export interface GuardianIssue {
  rule_id: string;
  severity: Severity;
  message: string;
  file: string;
  line: number;
  category: string;
  source: 'rule_engine' | 'metrics' | 'ai';
}

export interface FileMetrics {
  file: string;
  total_lines: number;
  largest_method_lines: number;
  max_nesting: number;
  constructor_deps: number;
}

export interface GuardianResult {
  risk_score: number;
  issues: GuardianIssue[];
  metrics: FileMetrics[];
  critical_count: number;
  error_count: number;
  warning_count: number;
  info_count: number;
  ai_summary?: string;
  timestamp: string;
}
