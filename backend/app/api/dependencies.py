"""Shared FastAPI dependency accessors for request handlers."""

from fastapi import Request

from app.services.feed_service import FeedService


def get_feed_service(request: Request) -> FeedService:
    return request.app.state.feed_service
