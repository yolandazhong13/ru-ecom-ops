#!/usr/bin/env python3
"""Concrete ActionHandler for listing media management on WB_CN.

Implements media preparation with:
1. Image quality and compliance validation
2. Video/thumbnail asset management
3. Media metadata enrichment
4. Listing readiness verification
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from unified_action_executor import ActionHandler

ROOT = Path(__file__).resolve().parents[1]


class ListingMediaError(Exception):
    """Raised when listing media operations fail."""
    pass


class ListingMediaActionHandler(ActionHandler):
    """Handles listing media management and preparation for WB_CN.

    Validates, organizes, and enriches media assets for product listings
    including images, videos, and metadata.
    """

    def __init__(
        self,
        client_id: str,
        media_data: dict[str, dict],
    ):
        """Initialize listing media handler.

        Args:
            client_id: WB_CN client identifier
            media_data: Dict mapping product_id to media info:
                {
                    "MD-700": {
                        "product_name": "Mesh Stereo Speaker",
                        "image_count": 8,
                        "primary_image_size_mb": 2.5,
                        "has_video": True,
                        "video_duration_seconds": 45,
                        "description_length": 1200,
                        "has_specifications": True,
                        "compliance_checked": True
                    }
                }
        """
        self.client_id = str(client_id)
        self.media_data = media_data
        self.validation_results = {}
        self.readiness_status = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Execute listing media validation and preparation.

        Args:
            content: Approval content with media criteria

        Returns:
            Dict with media validation and readiness status
        """
        # Validate media data
        validation_errors = []
        for product_id, product_info in self.media_data.items():
            errors = self._validate_media_input(product_id, product_info)
            validation_errors.extend(errors)

        if validation_errors:
            raise ListingMediaError(f"Media validation failed: {validation_errors}")

        # Assess each product's media readiness
        for product_id, product_info in self.media_data.items():
            assessment = self._assess_media_readiness(product_id, product_info)
            self.validation_results[product_id] = assessment

        # Generate readiness summary
        self.readiness_status = self._generate_readiness_status()

        return {
            "media_data": self.media_data,
            "validation_results": self.validation_results,
            "readiness_status": self.readiness_status,
            "product_count": len(self.media_data),
            "preparation_summary": self._summarize_preparation(),
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Post-execution verification of media preparation.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict with media checks
        """
        validation_checks = {
            "all_products_assessed": False,
            "quality_scores_valid": False,
            "readiness_status_provided": False,
            "compliance_verified": False,
            "metadata_complete": False,
        }

        error_details = []

        # Check 1: All products assessed
        validation_results = execution_result.get("validation_results", {})
        media_data = execution_result.get("media_data", {})
        if len(validation_results) == len(media_data) and len(media_data) > 0:
            validation_checks["all_products_assessed"] = True

        # Check 2: Quality scores in valid range (0-100)
        scores_valid = True
        for product_id, assessment in validation_results.items():
            quality_score = assessment.get("overall_quality_score", 0)
            if not (0 <= quality_score <= 100):
                scores_valid = False
                error_details.append(f"{product_id}: quality_score {quality_score} out of range")
        validation_checks["quality_scores_valid"] = scores_valid

        # Check 3: Readiness status provided
        readiness_status = execution_result.get("readiness_status", {})
        if readiness_status and len(readiness_status.get("ready_products", [])) >= 0:
            validation_checks["readiness_status_provided"] = True
        else:
            error_details.append("No readiness status generated")

        # Check 4: Compliance verified
        compliance_complete = True
        for product_id, assessment in validation_results.items():
            if assessment.get("compliance_status") != "compliant":
                compliance_complete = False
                error_details.append(f"{product_id}: compliance status {assessment.get('compliance_status')}")
        validation_checks["compliance_verified"] = compliance_complete

        # Check 5: Metadata complete
        metadata_complete = True
        for product_id, assessment in validation_results.items():
            required_fields = [
                "image_count_score", "image_quality_score", "video_score",
                "description_score", "specifications_score", "overall_quality_score"
            ]
            for field in required_fields:
                if field not in assessment or assessment[field] is None:
                    metadata_complete = False
                    error_details.append(f"{product_id}: missing metadata {field}")
        validation_checks["metadata_complete"] = metadata_complete

        # Overall status
        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_media_readiness" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "product_count": len(validation_results),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }

    def _validate_media_input(self, product_id: str, product_info: dict[str, Any]) -> list[str]:
        """Validate a single product's media input.

        Args:
            product_id: Product identifier
            product_info: Product info dict

        Returns:
            List of validation error messages
        """
        errors = []

        required_fields = {
            "product_name": str,
            "image_count": int,
            "primary_image_size_mb": (int, float),
            "has_video": bool,
            "video_duration_seconds": (int, float),
            "description_length": int,
            "has_specifications": bool,
            "compliance_checked": bool,
        }

        for field, field_type in required_fields.items():
            if field not in product_info:
                errors.append(f"{product_id}: missing required field {field}")
                continue

            value = product_info[field]
            if not isinstance(value, field_type):
                errors.append(f"{product_id}: {field} must be {field_type}")

        # Validate ranges
        if "image_count" in product_info:
            count = product_info["image_count"]
            if count < 1 or count > 50:
                errors.append(f"{product_id}: image_count must be between 1 and 50")

        if "primary_image_size_mb" in product_info:
            size = product_info["primary_image_size_mb"]
            if size <= 0:
                errors.append(f"{product_id}: primary_image_size_mb must be positive")

        if "description_length" in product_info:
            length = product_info["description_length"]
            if length < 50 or length > 10000:
                errors.append(f"{product_id}: description_length must be between 50 and 10000")

        return errors

    def _assess_media_readiness(self, product_id: str, product_info: dict[str, Any]) -> dict[str, Any]:
        """Assess media readiness for a single product.

        Args:
            product_id: Product identifier
            product_info: Product info dict

        Returns:
            Dict with media assessment results
        """
        # Image count score (0-100)
        image_count = product_info.get("image_count", 1)
        image_count_score = min(100, (image_count / 12) * 100)  # 12 images = max

        # Image quality score based on file size
        image_size_mb = product_info.get("primary_image_size_mb", 0)
        # Optimal: 2-4 MB per image
        if 2 <= image_size_mb <= 4:
            image_quality_score = 100
        elif image_size_mb < 2:
            image_quality_score = 50 + (image_size_mb / 2 * 50)
        else:
            image_quality_score = max(0, 100 - ((image_size_mb - 4) / 2 * 50))

        # Video score
        has_video = product_info.get("has_video", False)
        video_duration = product_info.get("video_duration_seconds", 0)
        if has_video and 15 <= video_duration <= 120:
            video_score = 100
        elif has_video and video_duration > 0:
            video_score = 50
        else:
            video_score = 0

        # Description score
        description_length = product_info.get("description_length", 0)
        # Optimal: 500-2000 characters
        if 500 <= description_length <= 2000:
            description_score = 100
        elif description_length < 500:
            description_score = (description_length / 500) * 100
        else:
            description_score = max(0, 100 - ((description_length - 2000) / 5000 * 50))

        # Specifications score
        has_specs = product_info.get("has_specifications", False)
        specifications_score = 100 if has_specs else 40

        # Compliance status
        compliance_checked = product_info.get("compliance_checked", False)
        compliance_status = "compliant" if compliance_checked else "not_verified"

        # Overall quality score
        overall_quality_score = (
            image_count_score * 0.25 +
            image_quality_score * 0.25 +
            video_score * 0.15 +
            description_score * 0.20 +
            specifications_score * 0.15
        )

        # Readiness determination
        readiness = self._determine_readiness(overall_quality_score, compliance_status)

        return {
            "product_id": product_id,
            "product_name": product_info.get("product_name", product_id),
            "image_count": image_count,
            "image_count_score": round(image_count_score, 1),
            "primary_image_size_mb": round(image_size_mb, 2),
            "image_quality_score": round(image_quality_score, 1),
            "has_video": has_video,
            "video_duration_seconds": video_duration,
            "video_score": round(video_score, 1),
            "description_length": description_length,
            "description_score": round(description_score, 1),
            "has_specifications": has_specs,
            "specifications_score": round(specifications_score, 1),
            "compliance_checked": compliance_checked,
            "compliance_status": compliance_status,
            "overall_quality_score": round(overall_quality_score, 1),
            "readiness": readiness,
            "recommendations": self._generate_recommendations(product_info, overall_quality_score),
        }

    def _determine_readiness(self, quality_score: float, compliance_status: str) -> str:
        """Determine readiness status based on scores.

        Args:
            quality_score: Overall quality score
            compliance_status: Compliance verification status

        Returns:
            Readiness status string
        """
        if compliance_status != "compliant":
            return "BLOCKED_COMPLIANCE"
        if quality_score >= 80:
            return "READY_FOR_PUBLISHING"
        elif quality_score >= 60:
            return "READY_WITH_IMPROVEMENTS"
        else:
            return "NEEDS_ENHANCEMENT"

    def _generate_recommendations(self, product_info: dict[str, Any], quality_score: float) -> list[str]:
        """Generate improvement recommendations.

        Args:
            product_info: Product info dict
            quality_score: Overall quality score

        Returns:
            List of recommendations
        """
        recommendations = []

        image_count = product_info.get("image_count", 0)
        if image_count < 6:
            recommendations.append("Add more images (target 8-12)")

        image_size = product_info.get("primary_image_size_mb", 0)
        if image_size < 2:
            recommendations.append("Increase primary image quality/file size (target 2-4 MB)")
        elif image_size > 5:
            recommendations.append("Optimize image file size (target 2-4 MB)")

        has_video = product_info.get("has_video", False)
        if not has_video:
            recommendations.append("Add product video (15-120 seconds)")

        description_length = product_info.get("description_length", 0)
        if description_length < 500:
            recommendations.append("Expand product description (target 500-2000 characters)")

        has_specs = product_info.get("has_specifications", False)
        if not has_specs:
            recommendations.append("Add detailed specifications")

        if quality_score < 60:
            recommendations.append("Priority: Address all quality issues before publishing")

        return recommendations

    def _generate_readiness_status(self) -> dict[str, Any]:
        """Generate overall media readiness status.

        Returns:
            Dict with readiness summary
        """
        ready_products = []
        conditional_products = []
        blocked_products = []

        for product_id, assessment in self.validation_results.items():
            readiness = assessment.get("readiness", "UNKNOWN")
            if readiness == "READY_FOR_PUBLISHING":
                ready_products.append(product_id)
            elif readiness == "READY_WITH_IMPROVEMENTS":
                conditional_products.append(product_id)
            else:
                blocked_products.append(product_id)

        return {
            "ready_products": ready_products,
            "ready_with_improvements": conditional_products,
            "blocked_products": blocked_products,
            "total_ready": len(ready_products),
            "total_conditional": len(conditional_products),
            "total_blocked": len(blocked_products),
            "readiness_timestamp": "2026-11-23T00:00:00+08:00",
        }

    def _summarize_preparation(self) -> dict[str, Any]:
        """Summarize media preparation insights.

        Returns:
            Summary dict with key metrics
        """
        if not self.validation_results:
            return {"total_products": 0}

        quality_scores = [a.get("overall_quality_score", 0) for a in self.validation_results.values()]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

        video_count = sum(1 for a in self.validation_results.values() if a.get("has_video"))
        spec_count = sum(1 for a in self.validation_results.values() if a.get("has_specifications"))

        return {
            "total_products": len(self.validation_results),
            "avg_quality_score": round(avg_quality, 1),
            "products_with_video": video_count,
            "products_with_specs": spec_count,
            "highest_quality_score": round(max(quality_scores), 1) if quality_scores else 0,
            "lowest_quality_score": round(min(quality_scores), 1) if quality_scores else 0,
        }
