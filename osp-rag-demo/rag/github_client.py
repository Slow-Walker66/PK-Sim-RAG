from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import requests


GRAPHQL_URL = "https://api.github.com/graphql"


DISCUSSIONS_QUERY = """
query Discussions($owner: String!, $repo: String!, $first: Int!, $after: String, $commentsFirst: Int!) {
  repository(owner: $owner, name: $repo) {
    discussions(first: $first, after: $after, orderBy: {field: UPDATED_AT, direction: DESC}) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        id
        number
        title
        url
        bodyText
        createdAt
        updatedAt
        category {
          name
        }
        author {
          login
          url
        }
        answer {
          id
          url
          bodyText
          createdAt
          updatedAt
          upvoteCount
          author {
            login
            url
          }
        }
        comments(first: $commentsFirst) {
          pageInfo {
            hasNextPage
            endCursor
          }
          nodes {
            id
            url
            bodyText
            createdAt
            updatedAt
            upvoteCount
            isAnswer
            author {
              login
              url
            }
          }
        }
      }
    }
  }
}
"""


COMMENTS_QUERY = """
query DiscussionComments($owner: String!, $repo: String!, $number: Int!, $first: Int!, $after: String) {
  repository(owner: $owner, name: $repo) {
    discussion(number: $number) {
      comments(first: $first, after: $after) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          id
          url
          bodyText
          createdAt
          updatedAt
          upvoteCount
          isAnswer
          author {
            login
            url
          }
        }
      }
    }
  }
}
"""


@dataclass
class GitHubDiscussionClient:
    token: str
    owner: str
    repo: str
    endpoint: str = GRAPHQL_URL
    timeout: int = 45

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _graphql(self, query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        if not self.token:
            raise ValueError("GITHUB_TOKEN is required to call GitHub GraphQL API.")
        response = requests.post(
            self.endpoint,
            json={"query": query, "variables": variables},
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("errors"):
            raise RuntimeError(f"GitHub GraphQL errors: {payload['errors']}")
        return payload["data"]

    def fetch_discussions(
        self,
        *,
        limit: Optional[int] = 100,
        page_size: int = 25,
        comments_first: int = 100,
    ) -> Iterable[dict]:
        fetched = 0
        after = None

        while True:
            remaining = page_size if limit is None else max(0, min(page_size, limit - fetched))
            if remaining == 0:
                break

            data = self._graphql(
                DISCUSSIONS_QUERY,
                {
                    "owner": self.owner,
                    "repo": self.repo,
                    "first": remaining,
                    "after": after,
                    "commentsFirst": comments_first,
                },
            )
            discussions = data["repository"]["discussions"]
            for node in discussions["nodes"]:
                discussion = self._normalize_discussion(node)
                comments_page = node.get("comments", {}).get("pageInfo") or {}
                if comments_page.get("hasNextPage"):
                    extra_comments = self._fetch_more_comments(
                        node["number"],
                        comments_page.get("endCursor"),
                        comments_first,
                    )
                    discussion["comments"].extend(extra_comments)
                yield discussion
                fetched += 1

            page_info = discussions["pageInfo"]
            if not page_info.get("hasNextPage"):
                break
            after = page_info.get("endCursor")

    def _fetch_more_comments(self, number: int, after: Optional[str], page_size: int) -> List[dict]:
        comments: List[dict] = []
        cursor = after
        while True:
            data = self._graphql(
                COMMENTS_QUERY,
                {
                    "owner": self.owner,
                    "repo": self.repo,
                    "number": number,
                    "first": page_size,
                    "after": cursor,
                },
            )
            discussion = data["repository"]["discussion"]
            if not discussion:
                break
            comments_page = discussion["comments"]
            comments.extend(self._normalize_comment(node) for node in comments_page["nodes"])
            page_info = comments_page["pageInfo"]
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")
        return comments

    def _normalize_discussion(self, node: Dict[str, Any]) -> dict:
        return {
            "id": node.get("id"),
            "number": node.get("number"),
            "title": node.get("title") or "",
            "url": node.get("url") or "",
            "body_text": node.get("bodyText") or "",
            "created_at": node.get("createdAt"),
            "updated_at": node.get("updatedAt"),
            "category": (node.get("category") or {}).get("name", ""),
            "author": self._normalize_author(node.get("author")),
            "answer": self._normalize_comment(node.get("answer")) if node.get("answer") else None,
            "comments": [
                self._normalize_comment(comment)
                for comment in (node.get("comments", {}) or {}).get("nodes", [])
            ],
        }

    def _normalize_comment(self, node: Optional[Dict[str, Any]]) -> dict:
        if not node:
            return {}
        return {
            "id": node.get("id"),
            "url": node.get("url") or "",
            "body_text": node.get("bodyText") or "",
            "created_at": node.get("createdAt"),
            "updated_at": node.get("updatedAt"),
            "upvote_count": node.get("upvoteCount", 0),
            "is_answer": bool(node.get("isAnswer", False)),
            "author": self._normalize_author(node.get("author")),
        }

    @staticmethod
    def _normalize_author(author: Optional[Dict[str, Any]]) -> dict:
        return {
            "login": (author or {}).get("login", ""),
            "url": (author or {}).get("url", ""),
        }

