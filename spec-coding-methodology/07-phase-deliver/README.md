# Phase 5: 验证部署 (Deliver)

## 目标

确保代码**符合规范、通过验证、可靠部署**。

**关键产出**:
- 验证报告
- 部署配置
- 监控告警
- 回滚计划

---

## 可执行方法

### 方法 1: 验证矩阵

| 验证类型 | 工具 | 触发条件 | 通过标准 | 责任人 |
|---------|------|---------|---------|--------|
| **单元测试** | gtest/catch2 | 每次代码提交 | 覆盖率 > 80%，全部通过 | 开发者 |
| **集成测试** | custom | 功能完成后 | API 契约符合 Spec | 开发者 |
| **性能测试** | Google Benchmark | 发布前 | 满足 NFR 指标 | QA |
| **契约测试** | Pact | 接口变更时 | 消费者/提供者兼容 | 开发者 |
| **安全扫描** | Trivy/Snyk | 每次构建 | 无高危漏洞 | DevSecOps |
| **规范一致性** | custom script | CI 中 | 代码注释包含 @require | CI |
| **混沌测试** | Chaos Mesh | 发布前 | 故障下系统可用 | SRE |

---

### 方法 2: CI/CD 流程

**GitHub Actions 示例**:
```yaml
# .github/workflows/spec-coding-ci.yml
name: Spec Coding CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  # Phase 1: Spec Validation
  spec-validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Validate Spec Format
        run: |
          python scripts/validate_spec.py specs/
      
      - name: Check Traceability
        run: |
          python scripts/check_requirement_tags.py src/
          
      - name: Verify ADR Links
        run: |
          python scripts/check_adr_links.py

  # Phase 2: Build & Test
  build-and-test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest]
        compiler: [gcc, clang]
    needs: spec-validation
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure
        run: cmake -B build -S . -DCMAKE_BUILD_TYPE=Release
      
      - name: Build
        run: cmake --build build -j$(nproc)
      
      - name: Unit Tests
        run: cd build && ctest --output-on-failure
      
      - name: Coverage Report
        run: |
          cmake -B build -S . -DENABLE_COVERAGE=ON
          cmake --build build
          cd build && ctest
          gcovr -r .. --html-details -o coverage.html
      
      - name: Upload Coverage
        uses: codecov/codecov-action@v3
        with:
          files: build/coverage.xml

  # Phase 3: Performance Test
  performance-test:
    runs-on: ubuntu-latest
    needs: build-and-test
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Build Release
        run: |
          cmake -B build -S . -DCMAKE_BUILD_TYPE=Release
          cmake --build build
      
      - name: Run Benchmarks
        run: ./build/tests/benchmarks
      
      - name: Check Performance Regression
        run: |
          python scripts/check_performance_regression.py \
            --baseline baseline.json \
            --current results.json \
            --threshold 5%

  # Phase 4: Security Scan
  security-scan:
    runs-on: ubuntu-latest
    needs: build-and-test
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Trivy
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          format: 'sarif'
          output: 'trivy-results.sarif'
      
      - name: Upload to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

  # Phase 5: Deploy to Staging
  deploy-staging:
    runs-on: ubuntu-latest
    needs: [performance-test, security-scan]
    if: github.ref == 'refs/heads/main'
    environment: staging
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy
        run: |
          echo "Deploying to staging..."
          # kubectl apply -f k8s/staging/
      
      - name: Smoke Tests
        run: |
          ./scripts/smoke_tests.sh staging
      
      - name: Performance Validation
        run: |
          ./scripts/perf_test.sh staging --duration=5m

  # Phase 6: Deploy to Production
  deploy-production:
    runs-on: ubuntu-latest
    needs: deploy-staging
    if: github.ref == 'refs/heads/main'
    environment: production
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Blue-Green Deploy
        run: |
          echo "Deploying to production..."
          # ./scripts/blue_green_deploy.sh
      
      - name: Canary Analysis
        run: |
          ./scripts/canary_analysis.sh --duration=10m
```

---

### 方法 3: 蓝绿部署

```yaml
# deployment.yaml
deployment:
  strategy: blue-green
  
  blue:
    version: v1.2.3
    traffic: 100%
    instances: 5
  
  green:
    version: v1.3.0
    traffic: 0%
    instances: 5
  
  promotion_criteria:
    - metric: error_rate
      threshold: "< 0.1%"
      window: 5m
      
    - metric: latency_p99
      threshold: "< 200ms"
      window: 5m
      
    - metric: cpu_usage
      threshold: "< 70%"
      window: 10m
      
    - metric: memory_usage
      threshold: "< 80%"
      window: 10m
  
  canary:
    enabled: true
    steps:
      - traffic: 5%
        duration: 5m
      - traffic: 25%
        duration: 10m
      - traffic: 50%
        duration: 10m
      - traffic: 100%
  
  rollback:
    auto_rollback: true
    triggers:
      - metric: error_rate
        threshold: "> 1%"
        window: 2m
        
      - metric: latency_p99
        threshold: "> 500ms"
        window: 5m
        
      - manual: true
    
    strategy: immediate  # or gradual
```

---

### 方法 4: 持续评估管道

```python
# scripts/eval_pipeline.py
#!/usr/bin/env python3
"""
Continuous Evaluation Pipeline for AI-Assisted Development
"""

import json
import logging
from datetime import datetime
from typing import Dict, List

class EvaluationPipeline:
    def __init__(self, config_path: str):
        with open(config_path) as f:
            self.config = json.load(f)
        self.baseline = self.load_baseline()
        
    def load_baseline(self) -> Dict:
        """Load baseline metrics from previous runs"""
        try:
            with open('baseline_metrics.json') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def run_evaluation(self) -> Dict:
        """Run full evaluation suite"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'test_results': self.run_tests(),
            'coverage': self.measure_coverage(),
            'performance': self.run_benchmarks(),
            'spec_compliance': self.check_spec_compliance(),
            'cost_metrics': self.calculate_costs()
        }
        return metrics
    
    def run_tests(self) -> Dict:
        """Run test suite and collect results"""
        import subprocess
        
        result = subprocess.run(
            ['./build/run_tests'],
            capture_output=True,
            text=True
        )
        
        return {
            'passed': result.returncode == 0,
            'total': 150,  # parse from output
            'failed': 0,
            'skipped': 0
        }
    
    def measure_coverage(self) -> float:
        """Measure code coverage"""
        import subprocess
        
        result = subprocess.run(
            ['gcovr', '-r', '.', '--json'],
            capture_output=True,
            text=True
        )
        
        data = json.loads(result.stdout)
        return data['line_coverage']
    
    def run_benchmarks(self) -> Dict:
        """Run performance benchmarks"""
        import subprocess
        
        result = subprocess.run(
            ['./build/run_benchmarks', '--json'],
            capture_output=True,
            text=True
        )
        
        return json.loads(result.stdout)
    
    def check_spec_compliance(self) -> Dict:
        """Check code compliance with specifications"""
        import subprocess
        
        # Check @require tags
        result = subprocess.run(
            ['python', 'scripts/check_requirement_tags.py', 'src/'],
            capture_output=True,
            text=True
        )
        
        return {
            'requirements_covered': 45,
            'requirements_total': 50,
            'coverage_percent': 90
        }
    
    def calculate_costs(self) -> Dict:
        """Calculate development costs"""
        return {
            'tokens_used': 150000,
            'api_calls': 50,
            'estimated_cost_usd': 2.50
        }
    
    def check_regression(self, metrics: Dict) -> List[str]:
        """Check for performance/feature regression"""
        alerts = []
        
        if not self.baseline:
            return alerts
        
        # Check test pass rate
        current_pass_rate = metrics['test_results']['passed']
        baseline_pass_rate = self.baseline.get('test_results', {}).get('passed', True)
        
        if current_pass_rate != baseline_pass_rate:
            alerts.append("Test pass rate regression!")
        
        # Check coverage
        current_coverage = metrics['coverage']
        baseline_coverage = self.baseline.get('coverage', 100)
        
        if current_coverage < baseline_coverage * 0.95:
            alerts.append(f"Coverage regression: {baseline_coverage}% → {current_coverage}%")
        
        # Check performance
        current_perf = metrics['performance'].get('latency_p99', 0)
        baseline_perf = self.baseline.get('performance', {}).get('latency_p99', float('inf'))
        
        if current_perf > baseline_perf * 1.1:
            alerts.append(f"Performance regression: {baseline_perf}ms → {current_perf}ms")
        
        return alerts
    
    def generate_report(self, metrics: Dict, alerts: List[str]) -> str:
        """Generate evaluation report"""
        report = f"""
# Evaluation Report
**Date**: {metrics['timestamp']}

## Test Results
- Status: {'✅ PASSED' if metrics['test_results']['passed'] else '❌ FAILED'}
- Coverage: {metrics['coverage']:.1f}%

## Performance
```json
{json.dumps(metrics['performance'], indent=2)}
```

## Spec Compliance
- Requirements Covered: {metrics['spec_compliance']['requirements_covered']}/{metrics['spec_compliance']['requirements_total']}
- Coverage: {metrics['spec_compliance']['coverage_percent']}%

## Cost Metrics
- Tokens Used: {metrics['cost_metrics']['tokens_used']:,}
- API Calls: {metrics['cost_metrics']['api_calls']}
- Estimated Cost: ${metrics['cost_metrics']['estimated_cost_usd']:.2f}

## Alerts
"""
        if alerts:
            for alert in alerts:
                report += f"- ⚠️ {alert}\n"
        else:
            report += "- ✅ No regressions detected\n"
        
        return report
    
    def save_baseline(self, metrics: Dict):
        """Save current metrics as new baseline"""
        with open('baseline_metrics.json', 'w') as f:
            json.dump(metrics, f, indent=2)

def main():
    pipeline = EvaluationPipeline('eval_config.json')
    
    # Run evaluation
    metrics = pipeline.run_evaluation()
    
    # Check regression
    alerts = pipeline.check_regression(metrics)
    
    # Generate report
    report = pipeline.generate_report(metrics, alerts)
    print(report)
    
    # Save report
    with open('evaluation_report.md', 'w') as f:
        f.write(report)
    
    # Update baseline if no alerts
    if not alerts:
        pipeline.save_baseline(metrics)
        print("✅ Baseline updated")
    else:
        print("❌ Regression detected, baseline not updated")
        exit(1)

if __name__ == '__main__':
    main()
```

---

## 部署检查清单

### 发布前检查
- [ ] 所有测试通过
- [ ] 性能测试满足 NFR
- [ ] 安全扫描无高危漏洞
- [ ] 文档已更新
- [ ] 回滚计划已准备
- [ ] 监控告警已配置

### 部署中检查
- [ ] 蓝绿部署流量切换正常
- [ ] Canary 指标正常
- [ ] 错误率在阈值内
- [ ] 延迟在阈值内

### 发布后检查
- [ ] 核心功能 Smoke Test 通过
- [ ] 业务指标正常
- [ ] 客户反馈正常
- [ ] 24小时内无 P0/P1 事故

---

## 工具推荐

| 类别 | 工具 | 用途 |
|------|------|------|
| CI/CD | GitHub Actions, GitLab CI | 自动化流水线 |
| 部署 | ArgoCD, Spinnaker | GitOps 部署 |
| 监控 | Prometheus, Grafana | 指标监控 |
| 日志 | ELK, Loki | 日志分析 |
| 追踪 | Jaeger, Zipkin | 分布式追踪 |
| 混沌 | Chaos Mesh, Gremlin | 混沌工程 |

---

## 下一章

→ [继续阅读: 08-tools - 工具链与检查清单](../08-tools/README.md)
