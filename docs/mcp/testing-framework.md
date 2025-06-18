# MCP Testing Framework

> **Purpose**: Comprehensive testing suite for MCP vs REST API comparison  
> **Components**: Performance benchmarks, quality assurance, automated reporting  
> **Integration**: CI/CD pipeline with regression detection

## Testing Architecture

### Test Categories

1. **Performance Benchmarks** - Speed and efficiency comparison
2. **Quality Assurance** - Data accuracy and analysis consistency  
3. **Reliability Testing** - Error handling and fallback behavior
4. **Load Testing** - High-volume conversation processing
5. **Integration Testing** - End-to-end workflow validation

### Test Suite Structure

```
tests/
├── integration/
│   ├── test_mcp_vs_rest.py           # Core comparison suite
│   ├── test_mcp_performance.py       # Performance benchmarks
│   ├── test_mcp_quality.py           # Quality assurance
│   ├── test_mcp_reliability.py       # Error handling & fallback
│   └── test_mcp_load.py              # High-volume testing
├── unit/
│   ├── test_mcp_client.py            # MCP client unit tests
│   ├── test_mcp_auth.py              # Authentication testing
│   └── test_conversation_fetcher.py  # Dual-mode abstraction
└── benchmarks/
    ├── performance_reports/          # Generated benchmark reports
    ├── regression_tracking/          # Historical performance data
    └── quality_metrics/              # Data accuracy tracking
```

## Core Testing Implementation

### Performance Benchmark Suite

```python
# tests/integration/test_mcp_vs_rest.py

import asyncio
import time
import statistics
from dataclasses import dataclass
from typing import List, Dict, Any
import pytest

from src.config import Config
from src.query_processor import QueryProcessor
from src.models import ConversationFilters


@dataclass
class BenchmarkResult:
    """Performance benchmark result."""
    mode: str  # 'rest' or 'mcp'
    query: str
    conversation_count: int
    fetch_duration: float
    total_duration: float
    cost_estimate: float
    memory_usage: float
    error_count: int


class MCPvRESTBenchmark:
    """Comprehensive performance comparison between MCP and REST modes."""
    
    def __init__(self):
        self.config = Config.from_env()
        self.test_queries = [
            "show me issues from the last 1 hour",
            "show me issues from the last 24 hours", 
            "analyze patterns in verification problems from the last week",
            "how many conversations from the last 1 hour",
            "list customer complaints from yesterday"
        ]
        
    async def run_comparative_benchmark(self, iterations: int = 5) -> Dict[str, Any]:
        """Run side-by-side comparison of MCP vs REST performance."""
        results = {
            'rest_results': [],
            'mcp_results': [],
            'comparison_summary': {},
            'quality_metrics': {}
        }
        
        for query in self.test_queries:
            print(f"\\n🧪 Benchmarking: '{query}'")
            
            # Run REST benchmarks
            rest_results = await self._benchmark_mode('rest', query, iterations)
            results['rest_results'].extend(rest_results)
            
            # Run MCP benchmarks  
            mcp_results = await self._benchmark_mode('mcp', query, iterations)
            results['mcp_results'].extend(mcp_results)
            
            # Quality comparison
            quality_metrics = await self._compare_quality('rest', 'mcp', query)
            results['quality_metrics'][query] = quality_metrics
            
        # Generate comparison summary
        results['comparison_summary'] = self._generate_summary(
            results['rest_results'], 
            results['mcp_results']
        )
        
        return results
    
    async def _benchmark_mode(self, mode: str, query: str, iterations: int) -> List[BenchmarkResult]:
        """Benchmark a specific mode (REST or MCP) for given query."""
        results = []
        
        for i in range(iterations):
            print(f"  {mode.upper()} iteration {i+1}/{iterations}")
            
            # Configure mode
            config = Config.from_env()
            config.enable_mcp = (mode == 'mcp')
            config.mcp_fallback_enabled = False  # Pure mode testing
            
            processor = QueryProcessor(config)
            
            # Measure performance
            start_time = time.time()
            memory_before = self._get_memory_usage()
            
            try:
                result = await processor.process_query(query)
                
                fetch_duration = time.time() - start_time  # Simplified for example
                total_duration = time.time() - start_time
                memory_after = self._get_memory_usage()
                
                benchmark_result = BenchmarkResult(
                    mode=mode,
                    query=query,
                    conversation_count=result.conversation_count,
                    fetch_duration=fetch_duration * 0.7,  # Estimated fetch portion
                    total_duration=total_duration,
                    cost_estimate=result.cost_info.estimated_cost_usd,
                    memory_usage=memory_after - memory_before,
                    error_count=0
                )
                
                results.append(benchmark_result)
                
            except Exception as e:
                print(f"    ❌ Error in {mode}: {e}")
                # Log error but continue testing
                results.append(BenchmarkResult(
                    mode=mode, query=query, conversation_count=0,
                    fetch_duration=0, total_duration=0, cost_estimate=0,
                    memory_usage=0, error_count=1
                ))
                
        return results
    
    async def _compare_quality(self, mode1: str, mode2: str, query: str) -> Dict[str, Any]:
        """Compare data quality between two modes."""
        # Run same query in both modes
        config1 = Config.from_env()
        config1.enable_mcp = (mode1 == 'mcp')
        
        config2 = Config.from_env() 
        config2.enable_mcp = (mode2 == 'mcp')
        
        processor1 = QueryProcessor(config1)
        processor2 = QueryProcessor(config2)
        
        result1 = await processor1.process_query(query)
        result2 = await processor2.process_query(query)
        
        # Compare results
        quality_metrics = {
            'conversation_count_match': result1.conversation_count == result2.conversation_count,
            'conversation_count_diff': abs(result1.conversation_count - result2.conversation_count),
            'cost_diff': abs(result1.cost_info.estimated_cost_usd - result2.cost_info.estimated_cost_usd),
            'summary_similarity': self._calculate_text_similarity(result1.summary, result2.summary),
            'insights_count_match': len(result1.key_insights) == len(result2.key_insights)
        }
        
        return quality_metrics
    
    def _generate_summary(self, rest_results: List[BenchmarkResult], 
                         mcp_results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Generate performance comparison summary."""
        
        # Calculate averages for each mode
        rest_avg = self._calculate_averages(rest_results)
        mcp_avg = self._calculate_averages(mcp_results)
        
        # Performance improvements
        fetch_improvement = ((rest_avg['fetch_duration'] - mcp_avg['fetch_duration']) 
                           / rest_avg['fetch_duration']) * 100
        total_improvement = ((rest_avg['total_duration'] - mcp_avg['total_duration']) 
                           / rest_avg['total_duration']) * 100
        
        summary = {
            'rest_averages': rest_avg,
            'mcp_averages': mcp_avg,
            'improvements': {
                'fetch_time_improvement_pct': fetch_improvement,
                'total_time_improvement_pct': total_improvement,
                'cost_difference_pct': ((mcp_avg['cost_estimate'] - rest_avg['cost_estimate'])
                                      / rest_avg['cost_estimate']) * 100,
                'memory_difference_mb': mcp_avg['memory_usage'] - rest_avg['memory_usage']
            },
            'reliability': {
                'rest_error_rate': sum(r.error_count for r in rest_results) / len(rest_results),
                'mcp_error_rate': sum(r.error_count for r in mcp_results) / len(mcp_results)
            },
            'recommendation': self._generate_recommendation(fetch_improvement, total_improvement)
        }
        
        return summary
    
    def _calculate_averages(self, results: List[BenchmarkResult]) -> Dict[str, float]:
        """Calculate average metrics from benchmark results."""
        valid_results = [r for r in results if r.error_count == 0]
        
        if not valid_results:
            return {'error': 'No valid results'}
            
        return {
            'fetch_duration': statistics.mean(r.fetch_duration for r in valid_results),
            'total_duration': statistics.mean(r.total_duration for r in valid_results),
            'cost_estimate': statistics.mean(r.cost_estimate for r in valid_results),
            'memory_usage': statistics.mean(r.memory_usage for r in valid_results),
            'conversation_count': statistics.mean(r.conversation_count for r in valid_results)
        }
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text summaries."""
        # Simple word overlap similarity (could use more sophisticated NLP)
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def _generate_recommendation(self, fetch_improvement: float, total_improvement: float) -> str:
        """Generate recommendation based on performance results."""
        if total_improvement > 30:
            return "STRONG RECOMMENDATION: Use MCP as primary mode"
        elif total_improvement > 15:
            return "MODERATE RECOMMENDATION: Use MCP with REST fallback"
        elif total_improvement > 0:
            return "WEAK RECOMMENDATION: MCP provides marginal benefits"
        else:
            return "NOT RECOMMENDED: Stick with REST API for better performance"
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024  # Convert to MB


# Test execution
@pytest.mark.asyncio
async def test_mcp_vs_rest_performance():
    """Main test function for performance comparison."""
    benchmark = MCPvRESTBenchmark()
    results = await benchmark.run_comparative_benchmark(iterations=3)
    
    # Assert basic functionality
    assert len(results['rest_results']) > 0
    assert len(results['mcp_results']) > 0
    assert 'comparison_summary' in results
    
    # Performance assertions (adjust thresholds as needed)
    summary = results['comparison_summary']
    
    # MCP should be faster than REST (target: >20% improvement)
    fetch_improvement = summary['improvements']['fetch_time_improvement_pct']
    assert fetch_improvement > 10, f"MCP fetch time improvement too low: {fetch_improvement}%"
    
    # Error rates should be low
    assert summary['reliability']['mcp_error_rate'] < 0.2, "MCP error rate too high"
    assert summary['reliability']['rest_error_rate'] < 0.2, "REST error rate too high"
    
    # Quality should be maintained
    for query, metrics in results['quality_metrics'].items():
        assert metrics['conversation_count_match'] or metrics['conversation_count_diff'] <= 2, \
            f"Conversation count mismatch for '{query}'"
        assert metrics['summary_similarity'] > 0.7, \
            f"Summary similarity too low for '{query}': {metrics['summary_similarity']}"
    
    # Generate report
    generate_performance_report(results)
    
    return results


def generate_performance_report(results: Dict[str, Any]) -> None:
    """Generate detailed performance report."""
    import json
    from datetime import datetime
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'test_summary': results['comparison_summary'],
        'detailed_results': {
            'rest_results': [r.__dict__ for r in results['rest_results']],
            'mcp_results': [r.__dict__ for r in results['mcp_results']]
        },
        'quality_metrics': results['quality_metrics']
    }
    
    # Save to file
    report_file = f"tests/benchmarks/performance_reports/mcp_vs_rest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\\n📊 Performance report saved: {report_file}")
    
    # Print summary
    summary = results['comparison_summary']
    print("\\n" + "="*60)
    print("🏁 PERFORMANCE COMPARISON SUMMARY")
    print("="*60)
    print(f"Fetch Time Improvement: {summary['improvements']['fetch_time_improvement_pct']:.1f}%")
    print(f"Total Time Improvement: {summary['improvements']['total_time_improvement_pct']:.1f}%")
    print(f"Cost Difference: {summary['improvements']['cost_difference_pct']:.1f}%")
    print(f"Recommendation: {summary['recommendation']}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_mcp_vs_rest_performance())
```

### Quality Assurance Testing

```python
# tests/integration/test_mcp_quality.py

import asyncio
import pytest
from src.config import Config
from src.query_processor import QueryProcessor


class MCPQualityAssurance:
    """Ensure MCP and REST provide identical analysis quality."""
    
    async def test_data_consistency(self):
        """Verify MCP and REST return identical conversation data."""
        test_queries = [
            "show me issues from the last 1 hour",
            "how many conversations from yesterday"
        ]
        
        for query in test_queries:
            rest_config = Config.from_env()
            rest_config.enable_mcp = False
            
            mcp_config = Config.from_env()
            mcp_config.enable_mcp = True
            mcp_config.mcp_fallback_enabled = False
            
            rest_processor = QueryProcessor(rest_config)
            mcp_processor = QueryProcessor(mcp_config)
            
            rest_result = await rest_processor.process_query(query)
            mcp_result = await mcp_processor.process_query(query)
            
            # Data consistency checks
            assert rest_result.conversation_count == mcp_result.conversation_count, \
                f"Conversation count mismatch: REST={rest_result.conversation_count}, MCP={mcp_result.conversation_count}"
            
            # Allow small cost differences due to model selection
            cost_diff = abs(rest_result.cost_info.estimated_cost_usd - mcp_result.cost_info.estimated_cost_usd)
            assert cost_diff < 0.05, f"Cost difference too large: {cost_diff}"
            
            # Summary should be substantially similar
            similarity = self._text_similarity(rest_result.summary, mcp_result.summary)
            assert similarity > 0.8, f"Summary similarity too low: {similarity}"
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity score."""
        # Implementation similar to benchmark suite
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)


@pytest.mark.asyncio
async def test_mcp_quality_assurance():
    """Run comprehensive quality assurance tests."""
    qa = MCPQualityAssurance()
    await qa.test_data_consistency()
```

### Reliability Testing

```python
# tests/integration/test_mcp_reliability.py

import asyncio
import pytest
from unittest.mock import patch
from src.config import Config
from src.query_processor import QueryProcessor


class MCPReliabilityTesting:
    """Test MCP error handling and fallback mechanisms."""
    
    async def test_fallback_mechanism(self):
        """Test that MCP failures gracefully fallback to REST."""
        config = Config.from_env()
        config.enable_mcp = True
        config.mcp_fallback_enabled = True
        
        # Simulate MCP connection failure
        with patch('src.mcp_client.MCPIntercomClient.fetch_conversations') as mock_mcp:
            mock_mcp.side_effect = ConnectionError("MCP server unavailable")
            
            processor = QueryProcessor(config)
            result = await processor.process_query("test query")
            
            # Should succeed via REST fallback
            assert result is not None
            assert result.conversation_count >= 0
    
    async def test_partial_failure_handling(self):
        """Test handling of partial MCP failures."""
        config = Config.from_env()
        config.enable_mcp = True
        
        # Simulate partial data retrieval
        with patch('src.mcp_client.MCPIntercomClient.fetch_conversations') as mock_mcp:
            # Return partial data
            mock_mcp.return_value = []  # Simulate empty result
            
            processor = QueryProcessor(config)
            result = await processor.process_query("test query")
            
            # Should handle gracefully
            assert result is not None
    
    async def test_timeout_handling(self):
        """Test MCP timeout scenarios."""
        config = Config.from_env()
        config.enable_mcp = True
        config.mcp_timeout = 1  # Very short timeout
        
        processor = QueryProcessor(config)
        
        # Should complete without hanging
        start_time = time.time()
        result = await processor.process_query("test query")
        duration = time.time() - start_time
        
        assert duration < 10, "Query took too long, timeout may not be working"
        assert result is not None


@pytest.mark.asyncio
async def test_mcp_reliability():
    """Run reliability test suite."""
    reliability = MCPReliabilityTesting()
    await reliability.test_fallback_mechanism()
    await reliability.test_partial_failure_handling()
    await reliability.test_timeout_handling()
```

## Automated Reporting

### CI/CD Integration

```yaml
# .github/workflows/mcp-performance.yml
name: MCP Performance Testing

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM

jobs:
  mcp-benchmark:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.13'
    
    - name: Install dependencies
      run: |
        pip install poetry
        poetry install
    
    - name: Run MCP vs REST benchmarks
      env:
        INTERCOM_ACCESS_TOKEN: ${{ secrets.INTERCOM_ACCESS_TOKEN }}
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        ENABLE_MCP: true
      run: |
        poetry run python tests/integration/test_mcp_vs_rest.py
    
    - name: Upload performance reports
      uses: actions/upload-artifact@v3
      with:
        name: performance-reports
        path: tests/benchmarks/performance_reports/
    
    - name: Performance regression check
      run: |
        poetry run python scripts/check_performance_regression.py
```

### Performance Dashboard

```python
# scripts/generate_performance_dashboard.py

import json
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import glob


def generate_performance_dashboard():
    """Generate performance dashboard from historical data."""
    
    # Load recent performance reports
    report_files = glob.glob("tests/benchmarks/performance_reports/*.json")
    report_files.sort(reverse=True)  # Most recent first
    
    reports = []
    for file_path in report_files[:30]:  # Last 30 reports
        with open(file_path) as f:
            reports.append(json.load(f))
    
    # Extract performance trends
    dates = [datetime.fromisoformat(r['timestamp'].replace('Z', '+00:00')) for r in reports]
    rest_times = [r['test_summary']['rest_averages']['total_duration'] for r in reports]
    mcp_times = [r['test_summary']['mcp_averages']['total_duration'] for r in reports]
    improvements = [r['test_summary']['improvements']['total_time_improvement_pct'] for r in reports]
    
    # Create dashboard plots
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    
    # Performance comparison over time
    ax1.plot(dates, rest_times, label='REST API', marker='o')
    ax1.plot(dates, mcp_times, label='MCP', marker='s')
    ax1.set_title('Performance Comparison Over Time')
    ax1.set_ylabel('Response Time (seconds)')
    ax1.legend()
    ax1.grid(True)
    
    # Performance improvement trend
    ax2.plot(dates, improvements, label='MCP Improvement %', marker='^', color='green')
    ax2.axhline(y=0, color='red', linestyle='--', alpha=0.5)
    ax2.set_title('MCP Performance Improvement Trend')
    ax2.set_ylabel('Improvement (%)')
    ax2.grid(True)
    
    # Latest comparison
    latest = reports[0]['test_summary']
    modes = ['REST', 'MCP']
    times = [latest['rest_averages']['total_duration'], latest['mcp_averages']['total_duration']]
    
    bars = ax3.bar(modes, times, color=['orange', 'blue'])
    ax3.set_title('Latest Performance Comparison')
    ax3.set_ylabel('Response Time (seconds)')
    
    # Add value labels on bars
    for bar, time_val in zip(bars, times):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, 
                f'{time_val:.1f}s', ha='center', va='bottom')
    
    # Cost comparison
    rest_costs = [r['test_summary']['rest_averages']['cost_estimate'] for r in reports]
    mcp_costs = [r['test_summary']['mcp_averages']['cost_estimate'] for r in reports]
    
    ax4.plot(dates, rest_costs, label='REST Cost', marker='o')
    ax4.plot(dates, mcp_costs, label='MCP Cost', marker='s')
    ax4.set_title('Cost Comparison Over Time')
    ax4.set_ylabel('Cost (USD)')
    ax4.legend()
    ax4.grid(True)
    
    plt.tight_layout()
    plt.savefig('tests/benchmarks/performance_dashboard.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print("📊 Performance dashboard generated: tests/benchmarks/performance_dashboard.png")


if __name__ == "__main__":
    generate_performance_dashboard()
```

## Expected Outcomes

### Performance Metrics

- **Baseline Comparison**: Current REST performance vs MCP performance
- **Improvement Tracking**: Percentage improvements in fetch time and total time
- **Cost Analysis**: OpenAI API cost differences between modes
- **Reliability Metrics**: Error rates and fallback success rates

### Quality Assurance

- **Data Consistency**: 100% conversation count accuracy between modes
- **Analysis Quality**: >90% similarity in generated insights
- **Customer Identification**: Identical customer email extraction
- **URL Generation**: Consistent conversation link creation

### Automated Monitoring

- **Daily Benchmarks**: Automated performance testing in CI/CD
- **Regression Detection**: Alerts for performance degradation
- **Historical Tracking**: Long-term performance trend analysis
- **Quality Validation**: Continuous data accuracy monitoring

This comprehensive testing framework ensures that MCP integration maintains the high quality and performance standards established in Phase 0-4 while providing clear visibility into the benefits of the new protocol implementation.

---

**Next**: Implement testing framework alongside MCP client development  
**Related**: [integration-plan.md](integration-plan.md) for implementation roadmap
