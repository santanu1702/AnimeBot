"""
anime_lookup.py
Wraps the two external APIs the bot depends on:

  * trace.moe  -> identifies the anime + episode/timestamp from a frame
  * AniList    -> fills in rich metadata (titles, episodes, seasons*,
                   score, dates, genres, cover image)

* AniList doesn't expose a "season count" field directly (most anime
  entries there are already split per-season), so total_seasons is
  derived heuristically from related "PREQUEL/SEQUEL" entries in the
  same franchise. It's labeled as an estimate in the output.
"""

import logging
import httpx

logger = logging.getLogger("guesstheanime.lookup")

TRACE_MOE_URL = "https://api.trace.moe/search"
ANILIST_URL = "https://graphql.anilist.co"

ANILIST_QUERY = """
query ($search: String) {
  Media(search: $search, type: ANIME) {
    id
    title { romaji english native }
    format
    episodes
    duration
    status
    startDate { year month day }
    averageScore
    meanScore
    coverImage { large }
    siteUrl
    relations {
      edges {
        relationType
        node {
          type
          format
        }
      }
    }
  }
}
"""


class LookupError(Exception):
    pass


async def identify_scene(image_bytes: bytes) -> dict:
    """
    Sends raw image bytes to trace.moe and returns the best match.
    Raises LookupError if nothing usable comes back.
    """
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            TRACE_MOE_URL,
            params={"anilistInfo": ""},
            content=image_bytes,
            headers={"Content-Type": "image/jpeg"},
        )

    if resp.status_code != 200:
        raise LookupError(f"trace.moe returned HTTP {resp.status_code}")

    data = resp.json()
    results = data.get("result") or []
    if not results:
        raise LookupError("No matching scene found for this image.")

    best = results[0]
    similarity = round(best.get("similarity", 0) * 100, 2)

    return {
        "anilist_id": (best.get("anilist") or {}).get("id") if isinstance(best.get("anilist"), dict) else best.get("anilist"),
        "filename": best.get("filename"),
        "episode": best.get("episode"),
        "from_time": best.get("from"),
        "to_time": best.get("to"),
        "similarity": similarity,
        "image_preview": best.get("image"),
        "video_preview": best.get("video"),
    }


async def fetch_anilist_details(search_term) -> dict | None:
    """
    search_term can be an AniList numeric ID or a title string.
    Returns a normalized dict of anime metadata, or None if not found.
    """
    variables = {"search": search_term}
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            ANILIST_URL,
            json={"query": ANILIST_QUERY, "variables": variables},
        )

    if resp.status_code != 200:
        logger.warning("AniList HTTP %s for %s", resp.status_code, search_term)
        return None

    payload = resp.json()
    media = (payload.get("data") or {}).get("Media")
    if not media:
        return None

    # Estimate season count from PREQUEL/SEQUEL anime relations
    related_seasons = 1
    for edge in (media.get("relations") or {}).get("edges", []):
        if edge.get("relationType") in ("PREQUEL", "SEQUEL") and edge.get("node", {}).get("type") == "ANIME":
            related_seasons += 1

    start = media.get("startDate") or {}
    release_date = "Unknown"
    if start.get("year"):
        release_date = "-".join(
            str(v).zfill(2) if i else str(v)
            for i, v in enumerate([start.get("year"), start.get("month"), start.get("day")])
            if v
        )

    score = media.get("averageScore") or media.get("meanScore")
    rating = f"{score / 10:.1f}/10 ⭐" if score else "N/A"

    titles = media.get("title") or {}

    return {
        "id": media.get("id"),
        "title_romaji": titles.get("romaji"),
        "title_english": titles.get("english"),
        "title_native": titles.get("native"),
        "format": media.get("format"),
        "episodes": media.get("episodes") or "Unknown",
        "estimated_seasons": related_seasons,
        "status": media.get("status"),
        "release_date": release_date,
        "rating": rating,
        "cover_image": (media.get("coverImage") or {}).get("large"),
        "site_url": media.get("siteUrl"),
    }
