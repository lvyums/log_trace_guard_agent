"""
Module 4: Compliance Audit

Provides compliance strategy infrastructure including QA, baseline generation,
and compliance checking strategies, a strategy factory, and a high-level
ComplianceService for audit operations.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

from log_guard.common.utils import JsonConfigLoader, LogManager, Result

logger = LogManager.get_logger("compliance")


# ---------------------------------------------------------------------------
# BaseComplianceStrategy
# ---------------------------------------------------------------------------

class BaseComplianceStrategy(ABC):
    """Abstract base strategy for compliance operations."""

    strategy_type: str = "base"

    @abstractmethod
    def execute(self, params: Any) -> Dict[str, Any]:
        """
        Execute the compliance strategy with the given parameters.

        Args:
            params: Strategy-specific parameters (dict or other type).

        Returns:
            A dict containing the strategy results.
        """
        ...


# ---------------------------------------------------------------------------
# QAStrategy
# ---------------------------------------------------------------------------

class QAStrategy(BaseComplianceStrategy):
    """Compliance Q&A strategy that searches standards for answers."""

    strategy_type = "qa"

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Answer compliance-related questions by searching standards.

        Expected params keys:
            - question (str): The user's compliance question.
            - asset_type (str, optional): Filter by applicable device type.
            - standard_filter (str, optional): Filter by standard category.

        Returns:
            dict with answered_questions, matched_count, standards.
        """
        question = params.get("question", "")
        asset_type = params.get("asset_type")
        standard_filter = params.get("standard_filter")

        standards = JsonConfigLoader.load("compliance_standards.json")
        matched_standards: List[Dict[str, Any]] = []
        matched_items: List[Dict[str, Any]] = []

        for std in standards:
            std_name = std.get("name", "")
            std_category = std.get("category", "")

            # Apply standard filter if provided
            if standard_filter:
                if standard_filter.lower() not in std_category.lower() and \
                   standard_filter.lower() not in std_name.lower():
                    continue

            items = std.get("items", [])
            std_matched_items: List[Dict[str, Any]] = []

            for item in items:
                requirement = item.get("requirement", "")
                detail = item.get("detail", "")
                applicable = item.get("applicable_devices", [])

                # Skip if asset_type filter provided and item doesn't apply
                if asset_type and "all" not in applicable:
                    if asset_type.lower() not in [d.lower() for d in applicable]:
                        continue

                # Search question keywords in requirement and detail
                if question:
                    q_lower = question.lower()
                    text = (requirement + " " + detail).lower()

                    # For Chinese text, try direct substring matching first
                    # Remove common stop words and try to find key terms
                    stop_words = {"的", "了", "吗", "呢", "啊", "是", "在", "有", "和", "与", "或", "需要", "满足", "什么", "如何", "怎么"}

                    # Try to match meaningful Chinese phrases (2-4 chars)
                    match_count = 0
                    found_any = False

                    # First try direct text contains check
                    if q_lower in text or any(phrase in text for phrase in [q_lower[:4], q_lower[:3], q_lower[:2]]):
                        found_any = True
                        match_count = 2

                    if not found_any:
                        # Extract meaningful characters/phrases
                        meaningful_chars = [c for c in q_lower if c.strip() and c not in "？，。、（）""'' "]
                        # Check 2-char and 3-char substrings
                        for length in [4, 3, 2]:
                            for i in range(len(q_lower) - length + 1):
                                phrase = q_lower[i:i+length]
                                if any(c in stop_words for c in [phrase]):
                                    continue
                                if phrase in text:
                                    match_count += 1
                                    found_any = True
                                    break
                            if found_any:
                                break

                    # For single character matching
                    if not found_any:
                        for c in meaningful_chars:
                            if c in text and c not in stop_words:
                                match_count += 0.5

                    if match_count < 1:
                        continue

                std_matched_items.append({
                    "item_id": item.get("item_id"),
                    "requirement": requirement,
                    "detail": detail,
                    "risk_if_not": item.get("risk_if_not"),
                    "check_method": item.get("check_method"),
                })

            if std_matched_items:
                matched_standards.append({
                    "standard_id": std.get("standard_id"),
                    "name": std_name,
                    "category": std_category,
                    "matched_items": std_matched_items,
                })
                matched_items.extend(std_matched_items)

        return {
            "answered_questions": matched_items,
            "matched_count": len(matched_items),
            "standards": matched_standards,
        }


# ---------------------------------------------------------------------------
# BaselineGenStrategy
# ---------------------------------------------------------------------------

class BaselineGenStrategy(BaseComplianceStrategy):
    """Generates a personalized compliance baseline configuration."""

    strategy_type = "baseline_gen"

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a personalized baseline based on environment parameters.

        Expected params keys:
            - asset_count (int): Number of assets being monitored.
            - business_type (str): Type of business (e.g., "finance", "tech").
            - device_types (list): List of device types in use.
            - monitor_scenarios (list, optional): Specific scenarios to monitor.
            - industry (str, optional): Industry sector for compliance focus.

        Returns:
            dict with baselines, summary.
        """
        asset_count = params.get("asset_count", 10)
        business_type = params.get("business_type", "general")
        device_types = params.get("device_types", [])
        monitor_scenarios = params.get("monitor_scenarios", [])
        industry = params.get("industry", "general")

        baselines = JsonConfigLoader.load("compliance_baselines.json")
        selected_baselines: List[Dict[str, Any]] = []
        applied_scenarios: List[str] = []
        skipped_scenarios: List[str] = []

        # Determine which baselines are applicable
        for bl in baselines:
            bl_name = bl.get("name", "")
            bl_scenario = bl.get("monitor_scenario", "")
            bl_devices = bl.get("applicable_devices", [])

            # Check if specific monitor scenarios are requested
            if monitor_scenarios:
                matched = False
                for req_scenario in monitor_scenarios:
                    if req_scenario.lower() in bl_scenario.lower() or \
                       bl_scenario.lower() in req_scenario.lower():
                        matched = True
                        break
                if not matched:
                    skipped_scenarios.append(bl_name)
                    continue

            # Check device type applicability
            if device_types and "all" not in bl_devices:
                device_match = any(
                    dt.lower() in [d.lower() for d in bl_devices]
                    for dt in device_types
                )
                if not device_match:
                    skipped_scenarios.append(bl_name)
                    continue

            # Scale thresholds based on asset count
            thresholds = dict(bl.get("thresholds", {}))
            if asset_count > 100:
                # Scale up thresholds for larger environments
                scaled = {}
                for key, val in thresholds.items():
                    scaled[key] = val
                thresholds = scaled
            elif asset_count < 5:
                # Tighten thresholds for small environments
                pass  # Keep default thresholds

            selected_baselines.append({
                "baseline_id": bl.get("baseline_id"),
                "name": bl_name,
                "category": bl.get("category"),
                "description": bl.get("description"),
                "monitor_scenario": bl_scenario,
                "thresholds": thresholds,
                "check_frequency": bl.get("check_frequency"),
                "alert_standard": bl.get("alert_standard"),
                "severity": bl.get("severity"),
                "remediation": bl.get("remediation"),
                "related_standards": bl.get("related_standards", []),
            })
            applied_scenarios.append(bl_name)

        # Build summary
        severity_counts: Dict[str, int] = {}
        for bl in selected_baselines:
            sev = bl.get("severity", "medium")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        summary = {
            "total_baselines": len(selected_baselines),
            "applied_scenarios": applied_scenarios,
            "skipped_scenarios": skipped_scenarios,
            "severity_distribution": severity_counts,
            "asset_count": asset_count,
            "business_type": business_type,
            "industry": industry,
            "note": (
                "Baselines selected based on device types and monitor scenarios. "
                "Review and adjust thresholds for your specific environment."
            ),
        }

        return {
            "baselines": selected_baselines,
            "summary": summary,
        }


# ---------------------------------------------------------------------------
# CheckStrategy
# ---------------------------------------------------------------------------

class CheckStrategy(BaseComplianceStrategy):
    """Evaluates compliance configuration against standards."""

    strategy_type = "check"

    # Standard compliance requirements
    REQUIREMENTS = {
        "log_retention_days": {
            "requirement": "≥ 180 days (6 months)",
            "suggestion": "Configure log rotation to retain at least 180 days of logs",
            "severity": "high",
            "pass_check": lambda v: (v or 0) >= 180,
        },
        "has_backup": {
            "requirement": "Log backup enabled",
            "suggestion": "Enable automated log backup with at least monthly frequency",
            "severity": "high",
            "pass_check": lambda v: bool(v),
        },
        "has_tamper_proof": {
            "requirement": "Tamper-proof mechanism enabled",
            "suggestion": "Enable WORM storage, blockchain attestation, or log signing",
            "severity": "high",
            "pass_check": lambda v: bool(v),
        },
        "device_count": {
            "requirement": "At least 1 monitored device",
            "suggestion": "Add devices to log collection scope",
            "severity": "medium",
            "pass_check": lambda v: (v or 0) >= 1,
        },
        "has_bastion": {
            "requirement": "Bastion host / jump server for access control",
            "suggestion": "Deploy a bastion host for centralized access management",
            "severity": "medium",
            "pass_check": lambda v: bool(v),
        },
        "has_audit_mechanism": {
            "requirement": "Audit mechanism enabled",
            "suggestion": "Enable audit logging for all critical systems",
            "severity": "high",
            "pass_check": lambda v: bool(v),
        },
        "has_ntp": {
            "requirement": "NTP time synchronization configured",
            "suggestion": "Configure NTP servers to ensure timestamp accuracy",
            "severity": "medium",
            "pass_check": lambda v: bool(v),
        },
        "has_alert_system": {
            "requirement": "Alert / notification system configured",
            "suggestion": "Configure real-time alerting for security events",
            "severity": "high",
            "pass_check": lambda v: bool(v),
        },
    }

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate compliance configuration against standards.

        Expected params keys match the REQUIREMENTS keys above.

        Returns:
            dict with overall_compliance (bool) and items (list of check results).
        """
        items: List[Dict[str, Any]] = []
        passed = 0
        failed = 0
        total = 0

        for check_name, check_def in self.REQUIREMENTS.items():
            actual_value = params.get(check_name)
            requirement = check_def["requirement"]
            suggestion = check_def["suggestion"]
            severity = check_def["severity"]
            is_pass = check_def["pass_check"](actual_value)

            items.append({
                "check_name": check_name,
                "status": "pass" if is_pass else "fail",
                "requirement": requirement,
                "actual": actual_value,
                "suggestion": suggestion if not is_pass else "",
                "severity": severity,
            })

            total += 1
            if is_pass:
                passed += 1
            else:
                failed += 1

        # Calculate compliance percentage
        compliance_pct = round((passed / total * 100) if total > 0 else 0, 1)

        # Determine overall pass/fail
        high_severity_fails = [
            it for it in items
            if it["status"] == "fail" and it["severity"] == "high"
        ]
        overall_compliance = compliance_pct >= 80 and len(high_severity_fails) == 0

        return {
            "overall_compliance": overall_compliance,
            "compliance_percentage": compliance_pct,
            "passed": passed,
            "failed": failed,
            "total": total,
            "high_severity_fails": len(high_severity_fails),
            "items": items,
        }


# ---------------------------------------------------------------------------
# ComplianceStrategyFactory
# ---------------------------------------------------------------------------

class ComplianceStrategyFactory:
    """
    Factory for registering and retrieving compliance strategies.

    Maintains a registry of strategy classes keyed by strategy type name.
    """

    def __init__(self):
        self._strategies: Dict[str, Type[BaseComplianceStrategy]] = {}
        self._instances: Dict[str, BaseComplianceStrategy] = {}

    def register(self, name: str, strategy_cls: Type[BaseComplianceStrategy]) -> None:
        """
        Register a strategy class under the given name.

        Args:
            name: Canonical name for the strategy.
            strategy_cls: Strategy class (subclass of BaseComplianceStrategy).
        """
        self._strategies[name] = strategy_cls

    def get_strategy(self, name: str) -> Optional[BaseComplianceStrategy]:
        """
        Get or create a strategy instance by name.

        Args:
            name: Strategy name (e.g., "qa", "baseline_gen", "check").

        Returns:
            A BaseComplianceStrategy instance, or None if not registered.
        """
        if name in self._instances:
            return self._instances[name]

        cls = self._strategies.get(name)
        if cls is None:
            return None

        instance = cls()
        self._instances[name] = instance
        return instance

    @property
    def registered_types(self) -> List[str]:
        """Return list of registered strategy type names."""
        return list(self._strategies.keys())


# ---- Default strategies registration ----

_default_factory: Optional[ComplianceStrategyFactory] = None


def _register_default_strategies() -> ComplianceStrategyFactory:
    """Create the default factory and register all built-in strategies."""
    factory = ComplianceStrategyFactory()
    factory.register("qa", QAStrategy)
    factory.register("baseline_gen", BaselineGenStrategy)
    factory.register("check", CheckStrategy)
    return factory


def get_default_factory() -> ComplianceStrategyFactory:
    """Get or create the default strategy factory with all built-in strategies."""
    global _default_factory
    if _default_factory is None:
        _default_factory = _register_default_strategies()
    return _default_factory


# Register at module level
_default_factory = _register_default_strategies()


# ---------------------------------------------------------------------------
# ComplianceService
# ---------------------------------------------------------------------------

class ComplianceService:
    """
    High-level service for compliance audit operations.

    Provides QA, baseline generation, and compliance checking functionality
    using the strategy pattern and returning Result-wrapped responses.
    """

    def __init__(self, factory: Optional[ComplianceStrategyFactory] = None):
        self.factory = factory or get_default_factory()

    # ------------------------------------------------------------------
    # compliance_qa
    # ------------------------------------------------------------------

    def compliance_qa(
        self,
        question: str,
        asset_type: Optional[str] = None,
        standard_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Answer compliance-related questions by searching standards.

        Args:
            question: The user's compliance question.
            asset_type: Optional filter by applicable device type.
            standard_filter: Optional filter by standard category.

        Returns:
            Result dict with answered questions and matched standards.
        """
        try:
            strategy = self.factory.get_strategy("qa")
            if strategy is None:
                return Result.fail("QA strategy not available")

            result = strategy.execute({
                "question": question,
                "asset_type": asset_type,
                "standard_filter": standard_filter,
            })

            if result.get("matched_count", 0) == 0:
                return Result.ok(
                    data={
                        "answered_questions": [],
                        "matched_count": 0,
                        "standards": [],
                        "note": "No matching compliance standards found for your question. "
                                "Try broadening your query or checking the standard filter.",
                    },
                    msg="No matching standards found",
                )

            return Result.ok(data=result, msg=f"Found {result['matched_count']} matching items")
        except Exception as e:
            logger.error(f"Compliance QA failed: {e}", exc_info=True)
            return Result.from_exception(500, f"Compliance QA failed: {e}")

    # ------------------------------------------------------------------
    # generate_baseline
    # ------------------------------------------------------------------

    def generate_baseline(
        self,
        asset_count: int = 10,
        business_type: str = "general",
        device_types: Optional[List[str]] = None,
        monitor_scenarios: Optional[List[str]] = None,
        industry: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a personalized compliance baseline.

        Args:
            asset_count: Number of assets being monitored.
            business_type: Type of business.
            device_types: List of device types in use.
            monitor_scenarios: Specific scenarios to monitor.
            industry: Industry sector.

        Returns:
            Result dict with generated baselines and summary.
        """
        try:
            strategy = self.factory.get_strategy("baseline_gen")
            if strategy is None:
                return Result.fail("Baseline generation strategy not available")

            result = strategy.execute({
                "asset_count": asset_count,
                "business_type": business_type,
                "device_types": device_types or [],
                "monitor_scenarios": monitor_scenarios or [],
                "industry": industry or "general",
            })

            total = result.get("summary", {}).get("total_baselines", 0)
            return Result.ok(
                data=result,
                msg=f"Generated {total} compliance baselines",
            )
        except Exception as e:
            logger.error(f"Baseline generation failed: {e}", exc_info=True)
            return Result.from_exception(500, f"Baseline generation failed: {e}")

    # ------------------------------------------------------------------
    # compliance_check
    # ------------------------------------------------------------------

    def compliance_check(
        self,
        log_retention_days: Optional[int] = None,
        has_backup: Optional[bool] = None,
        has_tamper_proof: Optional[bool] = None,
        device_count: Optional[int] = None,
        has_bastion: Optional[bool] = None,
        has_audit_mechanism: Optional[bool] = None,
        has_ntp: Optional[bool] = None,
        has_alert_system: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate compliance configuration against standards.

        Each parameter represents a compliance check item.

        Returns:
            Result dict with compliance check results.
        """
        try:
            strategy = self.factory.get_strategy("check")
            if strategy is None:
                return Result.fail("Compliance check strategy not available")

            result = strategy.execute({
                "log_retention_days": log_retention_days,
                "has_backup": has_backup,
                "has_tamper_proof": has_tamper_proof,
                "device_count": device_count,
                "has_bastion": has_bastion,
                "has_audit_mechanism": has_audit_mechanism,
                "has_ntp": has_ntp,
                "has_alert_system": has_alert_system,
            })

            status = "compliant" if result.get("overall_compliance") else "non-compliant"
            return Result.ok(
                data=result,
                msg=f"Compliance check: {status} "
                    f"({result.get('passed', 0)}/{result.get('total', 0)} passed)",
            )
        except Exception as e:
            logger.error(f"Compliance check failed: {e}", exc_info=True)
            return Result.from_exception(500, f"Compliance check failed: {e}")

    # ------------------------------------------------------------------
    # compliance_check_batch
    # ------------------------------------------------------------------

    def compliance_check_batch(self, checks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run compliance checks for multiple configurations.

        Each entry in *checks* should be a dict with the same keys as
        compliance_check() parameters.

        Args:
            checks: List of compliance check parameter dicts.

        Returns:
            Result dict with a list of individual check results and a summary.
        """
        if not checks:
            return Result.fail("No checks provided", code=400)

        try:
            strategy = self.factory.get_strategy("check")
            if strategy is None:
                return Result.fail("Compliance check strategy not available")

            results: List[Dict[str, Any]] = []
            overall_passed = 0
            overall_total = 0

            for i, check_params in enumerate(checks):
                result = strategy.execute(check_params)
                results.append({
                    "index": i,
                    "overall_compliance": result.get("overall_compliance"),
                    "compliance_percentage": result.get("compliance_percentage"),
                    "passed": result.get("passed"),
                    "failed": result.get("failed"),
                    "total": result.get("total"),
                    "items": result.get("items", []),
                })
                overall_passed += 1 if result.get("overall_compliance") else 0
                overall_total += 1

            summary = {
                "total_checks": len(checks),
                "compliant_count": overall_passed,
                "non_compliant_count": overall_total - overall_passed,
                "overall_compliance_rate": round(
                    (overall_passed / overall_total * 100) if overall_total > 0 else 0, 1
                ),
            }

            return Result.ok(
                data={
                    "results": results,
                    "summary": summary,
                },
                msg=f"Batch check complete: {overall_passed}/{overall_total} compliant",
            )
        except Exception as e:
            logger.error(f"Batch compliance check failed: {e}", exc_info=True)
            return Result.from_exception(500, f"Batch compliance check failed: {e}")