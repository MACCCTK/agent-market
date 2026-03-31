"""Unit tests for capability search functionality"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.capability_search import (
    AgentCapabilityMatch,
    SearchCapabilityRequest,
    SearchCapabilityResult,
)


class TestSearchCapabilityRequest:
    """Test SearchCapabilityRequest schema"""

    def test_minimal_search_request(self) -> None:
        """Test with only required fields"""
        task_id = uuid4()
        request = SearchCapabilityRequest(task_template_id=task_id)

        assert request.task_template_id == task_id
        assert request.keyword is None
        assert request.min_reputation_score == 0
        assert request.required_tags is None
        assert request.required_tools is None
        assert request.top_n == 3

    def test_full_search_request(self) -> None:
        """Test with all fields"""
        task_id = uuid4()
        request = SearchCapabilityRequest(
            task_template_id=task_id,
            keyword="machine learning",
            min_reputation_score=70,
            required_tags=["python", "pytorch"],
            required_tools=["jupyter", "gpu"],
            top_n=5,
        )

        assert request.task_template_id == task_id
        assert request.keyword == "machine learning"
        assert request.min_reputation_score == 70
        assert request.required_tags == ["python", "pytorch"]
        assert request.required_tools == ["jupyter", "gpu"]
        assert request.top_n == 5

    def test_invalid_reputation_score(self) -> None:
        """Test that negative reputation score is rejected"""
        with pytest.raises(ValidationError):
            SearchCapabilityRequest(
                task_template_id=uuid4(),
                min_reputation_score=-1,
            )

    def test_invalid_top_n(self) -> None:
        """Test that top_n fails validation"""
        with pytest.raises(ValidationError):
            SearchCapabilityRequest(
                task_template_id=uuid4(),
                top_n=0,
            )


class TestAgentCapabilityMatch:
    """Test AgentCapabilityMatch schema"""

    def test_agent_capability_match_creation(self) -> None:
        """Test creating an agent match"""
        agent_id = uuid4()
        package_id = uuid4()

        match = AgentCapabilityMatch(
            agent_id=agent_id,
            agent_name="TestAgent",
            agent_service_status="available",
            agent_subscription_status="subscribed",
            capacity_per_week=5,
            capability_package_id=package_id,
            package_title="Data Analysis Service",
            package_summary="Professional data analysis",
            price_min=Decimal("50.00"),
            price_max=Decimal("200.00"),
            reputation_score=85,
            average_rating=Decimal("4.8"),
            total_completed_tasks=42,
            match_score=92.5,
        )

        assert match.agent_id == agent_id
        assert match.agent_name == "TestAgent"
        assert match.match_score == 92.5
        assert match.reputation_score == 85
        assert match.total_completed_tasks == 42

    def test_agent_match_with_null_prices(self) -> None:
        """Test agent match with no pricing information"""
        match = AgentCapabilityMatch(
            agent_id=uuid4(),
            agent_name="TestAgent",
            agent_service_status="available",
            agent_subscription_status="subscribed",
            capacity_per_week=3,
            capability_package_id=uuid4(),
            package_title="Custom Service",
            package_summary="On request pricing",
            price_min=None,
            price_max=None,
            reputation_score=60,
            average_rating=Decimal("4.0"),
            total_completed_tasks=15,
            match_score=75.0,
        )

        assert match.price_min is None
        assert match.price_max is None
        assert match.match_score == 75.0

    def test_agent_match_score_range(self) -> None:
        """Test that match scores are properly normalized"""
        # Test minimum score
        match_min = AgentCapabilityMatch(
            agent_id=uuid4(),
            agent_name="LowScore",
            agent_service_status="available",
            agent_subscription_status="subscribed",
            capacity_per_week=1,
            capability_package_id=uuid4(),
            package_title="Service",
            package_summary="Summary",
            price_min=None,
            price_max=None,
            reputation_score=0,
            average_rating=Decimal("1.0"),
            total_completed_tasks=0,
            match_score=0.0,
        )
        assert match_min.match_score == 0.0

        # Test maximum score
        match_max = AgentCapabilityMatch(
            agent_id=uuid4(),
            agent_name="HighScore",
            agent_service_status="available",
            agent_subscription_status="subscribed",
            capacity_per_week=10,
            capability_package_id=uuid4(),
            package_title="Service",
            package_summary="Summary",
            price_min=Decimal("10"),
            price_max=Decimal("1000"),
            reputation_score=100,
            average_rating=Decimal("5.0"),
            total_completed_tasks=1000,
            match_score=100.0,
        )
        assert match_max.match_score == 100.0


class TestSearchCapabilityResult:
    """Test SearchCapabilityResult schema"""

    def test_empty_search_result(self) -> None:
        """Test search result with no matches"""
        result = SearchCapabilityResult(
            query="test",
            matched_agents=[],
            total_matches=0,
        )

        assert result.query == "test"
        assert result.matched_agents == []
        assert result.total_matches == 0

    def test_search_result_with_matches(self) -> None:
        """Test search result with agent matches"""
        match1 = AgentCapabilityMatch(
            agent_id=uuid4(),
            agent_name="Agent1",
            agent_service_status="available",
            agent_subscription_status="subscribed",
            capacity_per_week=5,
            capability_package_id=uuid4(),
            package_title="Service 1",
            package_summary="Summary 1",
            price_min=None,
            price_max=None,
            reputation_score=80,
            average_rating=Decimal("4.5"),
            total_completed_tasks=50,
            match_score=95.0,
        )

        match2 = AgentCapabilityMatch(
            agent_id=uuid4(),
            agent_name="Agent2",
            agent_service_status="available",
            agent_subscription_status="subscribed",
            capacity_per_week=3,
            capability_package_id=uuid4(),
            package_title="Service 2",
            package_summary="Summary 2",
            price_min=None,
            price_max=None,
            reputation_score=75,
            average_rating=Decimal("4.2"),
            total_completed_tasks=30,
            match_score=87.0,
        )

        result = SearchCapabilityResult(
            query="machine learning",
            matched_agents=[match1, match2],
            total_matches=2,
        )

        assert result.query == "machine learning"
        assert len(result.matched_agents) == 2
        assert result.matched_agents[0].match_score == 95.0
        assert result.matched_agents[1].match_score == 87.0
        assert result.total_matches == 2

    def test_top_3_result(self) -> None:
        """Test typical top 3 search result"""
        matches = [
            AgentCapabilityMatch(
                agent_id=uuid4(),
                agent_name=f"Agent{i}",
                agent_service_status="available",
                agent_subscription_status="subscribed",
                capacity_per_week=i + 1,
                capability_package_id=uuid4(),
                package_title=f"Service{i}",
                package_summary=f"Summary{i}",
                price_min=None,
                price_max=None,
                reputation_score=80 - i * 5,
                average_rating=Decimal("4.5"),
                total_completed_tasks=50 - i * 10,
                match_score=100.0 - i * 10,
            )
            for i in range(3)
        ]

        result = SearchCapabilityResult(
            query="data analysis",
            matched_agents=matches,
            total_matches=3,
        )

        assert len(result.matched_agents) == 3
        assert result.matched_agents[0].match_score == 100.0  # Highest match
        assert result.matched_agents[1].match_score == 90.0
        assert result.matched_agents[2].match_score == 80.0   # Lowest match


class TestSchemaSerializationDeserialization:
    """Test schema serialization and deserialization"""

    def test_request_to_dict(self) -> None:
        """Test converting request to dict"""
        task_id = uuid4()
        request = SearchCapabilityRequest(
            task_template_id=task_id,
            keyword="test",
            min_reputation_score=50,
            top_n=3,
        )

        request_dict = request.model_dump()

        assert request_dict["task_template_id"] == task_id
        assert request_dict["keyword"] == "test"
        assert request_dict["min_reputation_score"] == 50
        assert request_dict["top_n"] == 3

    def test_match_to_dict(self) -> None:
        """Test converting match to dict"""
        agent_id = uuid4()
        match = AgentCapabilityMatch(
            agent_id=agent_id,
            agent_name="TestAgent",
            agent_service_status="available",
            agent_subscription_status="subscribed",
            capacity_per_week=5,
            capability_package_id=uuid4(),
            package_title="Service",
            package_summary="Summary",
            price_min=Decimal("50"),
            price_max=Decimal("200"),
            reputation_score=85,
            average_rating=Decimal("4.8"),
            total_completed_tasks=42,
            match_score=92.5,
        )

        match_dict = match.model_dump()

        assert match_dict["agent_id"] == agent_id
        assert match_dict["agent_name"] == "TestAgent"
        assert match_dict["match_score"] == 92.5

    def test_result_to_dict(self) -> None:
        """Test converting result to dict"""
        match = AgentCapabilityMatch(
            agent_id=uuid4(),
            agent_name="Agent",
            agent_service_status="available",
            agent_subscription_status="subscribed",
            capacity_per_week=5,
            capability_package_id=uuid4(),
            package_title="Service",
            package_summary="Summary",
            price_min=None,
            price_max=None,
            reputation_score=80,
            average_rating=Decimal("4.5"),
            total_completed_tasks=50,
            match_score=90.0,
        )

        result = SearchCapabilityResult(
            query="test",
            matched_agents=[match],
            total_matches=1,
        )

        result_dict = result.model_dump()

        assert result_dict["query"] == "test"
        assert len(result_dict["matched_agents"]) == 1
        assert result_dict["total_matches"] == 1
