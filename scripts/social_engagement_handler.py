#!/usr/bin/env python3
"""Concrete ActionHandler for social media engagement and content management on WB_CN.

Implements social engagement workflow with:
1. Social media performance tracking
2. Content engagement analysis
3. Audience sentiment monitoring
4. Social strategy recommendations
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from unified_action_executor import ActionHandler

ROOT = Path(__file__).resolve().parents[1]


class SocialEngagementError(Exception):
    """Raised when social engagement operations fail."""
    pass


class SocialEngagementActionHandler(ActionHandler):
    """Handles social media engagement and content management for WB_CN.

    Tracks social performance, analyzes audience engagement, monitors sentiment,
    and recommends content strategies to improve brand presence and reach.
    """

    def __init__(
        self,
        client_id: str,
        social_data: dict[str, dict],
    ):
        """Initialize social engagement handler.

        Args:
            client_id: WB_CN client identifier
            social_data: Dict mapping post_id to social data:
                {
                    "post_001": {
                        "post_id": "post_001",
                        "platform": "vk",
                        "post_date": "2026-11-20",
                        "content_type": "product_showcase",
                        "impressions": 5000,
                        "engagement_count": 450,
                        "likes": 350,
                        "comments": 75,
                        "shares": 25,
                        "clicks": 100,
                        "conversions": 15,
                        "sentiment_score": 0.8,
                        "hashtag_count": 5,
                        "mentions": 3
                    }
                }
        """
        self.client_id = str(client_id)
        self.action_type = "social_engagement"
        self.platform = "WB_CN"
        self.social_data = social_data
        self.analysis_results = {}
        self.engagement_summary = {}

    def execute(self, content: dict[str, Any]) -> dict[str, Any]:
        """Execute social engagement analysis.

        Args:
            content: Approval content with engagement analysis criteria

        Returns:
            Dict with social engagement analysis and recommendations
        """
        # Validate social data
        validation_errors = []
        for post_id, post_info in self.social_data.items():
            errors = self._validate_social_data(post_id, post_info)
            validation_errors.extend(errors)

        if validation_errors:
            raise SocialEngagementError(f"Social data validation failed: {validation_errors}")

        # Analyze each post
        for post_id, post_info in self.social_data.items():
            analysis = self._analyze_post_engagement(post_id, post_info)
            self.analysis_results[post_id] = analysis

        # Generate engagement summary
        self.engagement_summary = self._generate_engagement_summary()

        return {
            "social_data": self.social_data,
            "analysis_results": self.analysis_results,
            "engagement_summary": self.engagement_summary,
            "post_count": len(self.social_data),
            "social_strategy": self._summarize_social_strategy(),
        }

    def verify(self, execution_result: dict[str, Any]) -> dict[str, Any]:
        """Post-execution verification of social engagement analysis.

        Args:
            execution_result: Results from execute()

        Returns:
            Verification dict with engagement checks
        """
        validation_checks = {
            "all_posts_analyzed": False,
            "engagement_metrics_valid": False,
            "sentiment_analysis_completed": False,
            "roi_calculations_verified": False,
            "content_recommendations_provided": False,
        }

        error_details = []

        # Check 1: All posts analyzed
        analysis_results = execution_result.get("analysis_results", {})
        social_data = execution_result.get("social_data", {})
        if len(analysis_results) == len(social_data) and len(social_data) > 0:
            validation_checks["all_posts_analyzed"] = True

        # Check 2: Engagement metrics valid
        metrics_valid = True
        for post_id, analysis in analysis_results.items():
            engagement_rate = analysis.get("engagement_rate_percent", 0)
            if not (0 <= engagement_rate <= 100):
                metrics_valid = False
                error_details.append(f"{post_id}: engagement_rate {engagement_rate}% out of range")
        validation_checks["engagement_metrics_valid"] = metrics_valid

        # Check 3: Sentiment analysis completed
        sentiment_valid = True
        for post_id, analysis in analysis_results.items():
            sentiment = analysis.get("sentiment_score", None)
            if sentiment is None or not (-1 <= sentiment <= 1):
                sentiment_valid = False
                error_details.append(f"{post_id}: sentiment_score invalid")
        validation_checks["sentiment_analysis_completed"] = sentiment_valid

        # Check 4: ROI calculations verified
        roi_valid = True
        for post_id, analysis in analysis_results.items():
            roi = analysis.get("engagement_to_conversion_ratio", None)
            if roi is None or not isinstance(roi, (int, float)):
                roi_valid = False
                error_details.append(f"{post_id}: engagement_to_conversion_ratio not calculated")
        validation_checks["roi_calculations_verified"] = roi_valid

        # Check 5: Content recommendations provided
        summary = execution_result.get("social_strategy", {})
        if summary and summary.get("content_recommendations"):
            validation_checks["content_recommendations_provided"] = True
        else:
            error_details.append("No content recommendations provided")

        # Overall status
        all_checks_pass = all(validation_checks.values())
        overall_status = "verified_social_engagement" if all_checks_pass else "partial_or_validation_failed"

        return {
            "validation_checks": validation_checks,
            "error_details": error_details,
            "post_count": len(analysis_results),
            "overall_status": overall_status,
            "all_valid": all_checks_pass,
        }

    def _validate_social_data(self, post_id: str, post_info: dict[str, Any]) -> list[str]:
        """Validate social media data.

        Args:
            post_id: Post identifier
            post_info: Post info dict

        Returns:
            List of validation error messages
        """
        errors = []

        required_fields = {
            "post_id": str,
            "platform": str,
            "post_date": str,
            "content_type": str,
            "impressions": int,
            "engagement_count": int,
            "likes": int,
            "comments": int,
            "shares": int,
            "clicks": int,
            "conversions": int,
            "sentiment_score": (int, float),
            "hashtag_count": int,
            "mentions": int,
        }

        for field, field_type in required_fields.items():
            if field not in post_info:
                errors.append(f"{post_id}: missing required field {field}")
                continue

            value = post_info[field]
            if not isinstance(value, field_type):
                errors.append(f"{post_id}: {field} must be {field_type}")

        # Validate ranges
        if "impressions" in post_info and post_info["impressions"] < 0:
            errors.append(f"{post_id}: impressions must be non-negative")

        if "sentiment_score" in post_info:
            score = post_info["sentiment_score"]
            if not (-1 <= score <= 1):
                errors.append(f"{post_id}: sentiment_score must be -1 to 1")

        # Validate logical consistency
        impressions = post_info.get("impressions", 0)
        engagement = post_info.get("engagement_count", 0)
        clicks = post_info.get("clicks", 0)
        conversions = post_info.get("conversions", 0)

        if engagement > impressions:
            errors.append(f"{post_id}: engagement_count cannot exceed impressions")
        if clicks > impressions:
            errors.append(f"{post_id}: clicks cannot exceed impressions")
        if conversions > clicks:
            errors.append(f"{post_id}: conversions cannot exceed clicks")

        return errors

    def _analyze_post_engagement(self, post_id: str, post_info: dict[str, Any]) -> dict[str, Any]:
        """Analyze post engagement metrics.

        Args:
            post_id: Post identifier
            post_info: Post info dict

        Returns:
            Dict with post engagement analysis
        """
        platform = post_info.get("platform", "unknown")
        post_date = post_info.get("post_date", "2026-11-23")
        content_type = post_info.get("content_type", "general")
        impressions = post_info.get("impressions", 1)
        engagement_count = post_info.get("engagement_count", 0)
        likes = post_info.get("likes", 0)
        comments = post_info.get("comments", 0)
        shares = post_info.get("shares", 0)
        clicks = post_info.get("clicks", 0)
        conversions = post_info.get("conversions", 0)
        sentiment = post_info.get("sentiment_score", 0)
        hashtag_count = post_info.get("hashtag_count", 0)
        mentions = post_info.get("mentions", 0)

        # Calculate engagement metrics
        engagement_rate = (engagement_count / impressions * 100) if impressions > 0 else 0
        ctr = (clicks / impressions * 100) if impressions > 0 else 0
        conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0
        engagement_to_conversion = (engagement_count / conversions) if conversions > 0 else 0

        # Calculate interaction breakdown
        likes_percent = (likes / engagement_count * 100) if engagement_count > 0 else 0
        comments_percent = (comments / engagement_count * 100) if engagement_count > 0 else 0
        shares_percent = (shares / engagement_count * 100) if engagement_count > 0 else 0

        # Engagement quality score (0-100)
        # Optimal: 10% engagement rate, positive sentiment, 30%+ comments
        engagement_quality = min(100, (engagement_rate / 10) * 100)
        sentiment_quality = ((sentiment + 1) / 2) * 100  # -1 to 1 -> 0 to 100
        comment_quality = min(100, (comments_percent / 30) * 100)
        quality_score = engagement_quality * 0.4 + sentiment_quality * 0.4 + comment_quality * 0.2

        # Determine content performance rating
        if quality_score >= 80:
            performance_rating = "EXCEPTIONAL"
        elif quality_score >= 60:
            performance_rating = "STRONG"
        elif quality_score >= 40:
            performance_rating = "MODERATE"
        else:
            performance_rating = "WEAK"

        # Sentiment category
        if sentiment > 0.5:
            sentiment_category = "VERY_POSITIVE"
        elif sentiment > 0.2:
            sentiment_category = "POSITIVE"
        elif sentiment > -0.2:
            sentiment_category = "NEUTRAL"
        elif sentiment > -0.5:
            sentiment_category = "NEGATIVE"
        else:
            sentiment_category = "VERY_NEGATIVE"

        # Content effectiveness insights
        insights = self._generate_engagement_insights(
            engagement_rate, sentiment, likes_percent, comments_percent, shares_percent,
            conversion_rate, content_type, hashtag_count
        )

        # Optimization suggestions
        optimization_suggestions = self._suggest_optimizations(
            engagement_rate, sentiment, conversion_rate, comments_percent,
            hashtag_count, platform, content_type
        )

        return {
            "post_id": post_id,
            "platform": platform,
            "post_date": post_date,
            "content_type": content_type,
            "impressions": impressions,
            "engagement_count": engagement_count,
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "clicks": clicks,
            "conversions": conversions,
            "engagement_rate_percent": round(engagement_rate, 2),
            "ctr_percent": round(ctr, 2),
            "conversion_rate_percent": round(conversion_rate, 2),
            "engagement_to_conversion_ratio": round(engagement_to_conversion, 1),
            "likes_percent_of_engagement": round(likes_percent, 1),
            "comments_percent_of_engagement": round(comments_percent, 1),
            "shares_percent_of_engagement": round(shares_percent, 1),
            "sentiment_score": round(sentiment, 2),
            "sentiment_category": sentiment_category,
            "hashtag_count": hashtag_count,
            "mentions": mentions,
            "engagement_quality_score": round(quality_score, 1),
            "performance_rating": performance_rating,
            "insights": insights,
            "optimization_suggestions": optimization_suggestions,
        }

    def _generate_engagement_insights(self, engagement_rate: float, sentiment: float,
                                     likes_pct: float, comments_pct: float, shares_pct: float,
                                     conversion_rate: float, content_type: str,
                                     hashtag_count: int) -> list[str]:
        """Generate insights about post engagement.

        Args:
            engagement_rate: Engagement rate percentage
            sentiment: Sentiment score
            likes_pct: Likes as % of engagement
            comments_pct: Comments as % of engagement
            shares_pct: Shares as % of engagement
            conversion_rate: Conversion rate percentage
            content_type: Type of content
            hashtag_count: Number of hashtags

        Returns:
            List of insight strings
        """
        insights = []

        if engagement_rate > 10:
            insights.append("High engagement rate - content resonates well with audience")
        elif engagement_rate < 2:
            insights.append("Low engagement - consider content refresh or timing adjustment")

        if sentiment > 0.5:
            insights.append("Very positive sentiment - audience highly receptive")
        elif sentiment < -0.3:
            insights.append("Negative sentiment detected - review content messaging")

        if comments_pct > 40:
            insights.append("Strong discussion - audience actively commenting")
        elif comments_pct < 10:
            insights.append("Low comments - consider questions or CTAs to boost interaction")

        if shares_pct > 15:
            insights.append("High share rate - content viral potential present")

        if conversion_rate > 2:
            insights.append("Strong conversion performance - content drives action")

        if hashtag_count > 10:
            insights.append("Many hashtags used - may help discovery")
        elif hashtag_count < 3 and content_type == "product_showcase":
            insights.append("Few hashtags - increase hashtag usage for product content")

        if not insights:
            insights.append("Post performing at baseline - maintain current strategy")

        return insights

    def _suggest_optimizations(self, engagement_rate: float, sentiment: float,
                              conversion_rate: float, comments_pct: float,
                              hashtag_count: int, platform: str, content_type: str) -> list[str]:
        """Suggest content optimizations.

        Args:
            engagement_rate: Engagement rate percentage
            sentiment: Sentiment score
            conversion_rate: Conversion rate percentage
            comments_pct: Comments as percentage
            hashtag_count: Number of hashtags
            platform: Social media platform
            content_type: Type of content

        Returns:
            List of optimization suggestions
        """
        suggestions = []

        # Engagement optimization
        if engagement_rate < 5:
            suggestions.append("Test different posting times to reach more users")
            suggestions.append("Vary content format - try video or carousel")

        # Sentiment optimization
        if sentiment < 0:
            suggestions.append("Review messaging - address any negative feedback")
            suggestions.append("Consider positive/inspirational content angle")

        # Conversion optimization
        if conversion_rate < 1:
            suggestions.append("Add clearer call-to-action (CTA)")
            suggestions.append("Include product link/button in post or caption")

        # Comment engagement
        if comments_pct < 15:
            suggestions.append("Ask questions to stimulate comments")
            suggestions.append("Respond to existing comments to boost discussion")

        # Hashtag optimization
        if hashtag_count < 5 and platform == "vk":
            suggestions.append("Increase hashtags to 5-10 for better discoverability")
        elif hashtag_count > 20:
            suggestions.append("Reduce hashtags - focus on most relevant ones")

        # Platform-specific
        if platform == "vk" and engagement_rate > 5:
            suggestions.append("Repurpose this content across other platforms")

        # Content type optimization
        if content_type == "product_showcase" and conversion_rate < 2:
            suggestions.append("Add customer testimonials or reviews to product posts")
            suggestions.append("Highlight unique selling points in product description")

        if not suggestions:
            suggestions.append("Content performing well - continue current strategy")

        return suggestions

    def _generate_engagement_summary(self) -> dict[str, Any]:
        """Generate engagement analysis summary.

        Returns:
            Dict with engagement summary
        """
        exceptional_posts = []
        strong_posts = []
        moderate_posts = []
        weak_posts = []

        total_impressions = 0
        total_engagement = 0
        total_conversions = 0
        avg_sentiment = 0
        platform_distribution = {}

        for post_id, analysis in self.analysis_results.items():
            rating = analysis.get("performance_rating", "UNKNOWN")
            if rating == "EXCEPTIONAL":
                exceptional_posts.append(post_id)
            elif rating == "STRONG":
                strong_posts.append(post_id)
            elif rating == "MODERATE":
                moderate_posts.append(post_id)
            else:
                weak_posts.append(post_id)

            total_impressions += analysis.get("impressions", 0)
            total_engagement += analysis.get("engagement_count", 0)
            total_conversions += analysis.get("conversions", 0)
            avg_sentiment += analysis.get("sentiment_score", 0)

            platform = analysis.get("platform", "unknown")
            platform_distribution[platform] = platform_distribution.get(platform, 0) + 1

        post_count = len(self.analysis_results)
        avg_sentiment = avg_sentiment / post_count if post_count > 0 else 0
        overall_engagement_rate = (total_engagement / total_impressions * 100) if total_impressions > 0 else 0
        overall_conversion_rate = (total_conversions / total_engagement * 100) if total_engagement > 0 else 0

        return {
            "exceptional_posts": exceptional_posts,
            "strong_posts": strong_posts,
            "moderate_posts": moderate_posts,
            "weak_posts": weak_posts,
            "performance_distribution": {
                "EXCEPTIONAL": len(exceptional_posts),
                "STRONG": len(strong_posts),
                "MODERATE": len(moderate_posts),
                "WEAK": len(weak_posts),
            },
            "total_posts_analyzed": post_count,
            "total_impressions": total_impressions,
            "total_engagement_count": total_engagement,
            "total_conversions": total_conversions,
            "overall_engagement_rate_percent": round(overall_engagement_rate, 2),
            "overall_conversion_rate_percent": round(overall_conversion_rate, 2),
            "average_sentiment_score": round(avg_sentiment, 2),
            "platform_distribution": platform_distribution,
            "analysis_timestamp": "2026-11-23T00:00:00+08:00",
        }

    def _summarize_social_strategy(self) -> dict[str, Any]:
        """Summarize social strategy insights.

        Returns:
            Summary dict with key metrics
        """
        if not self.analysis_results:
            return {"total_posts": 0}

        quality_scores = [a.get("engagement_quality_score", 0) for a in self.analysis_results.values()]
        sentiment_scores = [a.get("sentiment_score", 0) for a in self.analysis_results.values()]
        engagement_rates = [a.get("engagement_rate_percent", 0) for a in self.analysis_results.values()]

        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        avg_engagement = sum(engagement_rates) / len(engagement_rates) if engagement_rates else 0

        # Identify content types
        content_types = {}
        for analysis in self.analysis_results.values():
            ctype = analysis.get("content_type", "unknown")
            content_types[ctype] = content_types.get(ctype, 0) + 1

        # Content recommendations
        content_recommendations = []
        if avg_quality < 50:
            content_recommendations.append("Overall quality needs improvement - review content strategy")
        if avg_engagement < 5:
            content_recommendations.append("Engagement below target - increase posting frequency or vary content")
        if len(self.engagement_summary.get("weak_posts", [])) > len(self.engagement_summary.get("exceptional_posts", [])):
            content_recommendations.append("More weak than exceptional posts - shift to higher-performing content types")

        if not content_recommendations:
            content_recommendations.append("Social strategy performing well - continue current approach")

        return {
            "total_posts_analyzed": len(self.analysis_results),
            "avg_quality_score": round(avg_quality, 1),
            "avg_engagement_rate_percent": round(avg_engagement, 2),
            "avg_sentiment_score": round(sum(sentiment_scores) / len(sentiment_scores), 2) if sentiment_scores else 0,
            "best_performing_post": max(self.analysis_results.items(), key=lambda x: x[1].get("engagement_quality_score", 0))[0] if self.analysis_results else "N/A",
            "content_type_distribution": content_types,
            "portfolio_health": "STRONG" if avg_quality > 60 else "GOOD" if avg_quality > 45 else "NEEDS_REVIEW",
            "content_recommendations": content_recommendations,
            "strategic_focus": "Balance reach (impressions) with quality (sentiment + engagement)",
        }
