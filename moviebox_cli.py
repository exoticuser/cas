#!/usr/bin/env python3
"""MovieBox CLI client (Python)."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import re
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qs, quote, urlparse

import requests

MAIN_URL = "https://api.inmoviebox.com"
USER_AGENT = (
    "com.community.mbox.in/50020042 (Linux; U; Android 16; en_IN; "
    "sdk_gphone64_x86_64; Build/BP22.250325.006; Cronet/133.0.6876.3)"
)
CLIENT_INFO = (
    "{\"package_name\":\"com.community.mbox.in\",\"version_name\":"
    "\"3.0.03.0529.03\",\"version_code\":50020042,\"os\":\"android\"," 
    "\"os_version\":\"16\",\"device_id\":\"da2b99c821e6ea023e4be55b54d5f7d8\"," 
    "\"install_store\":\"ps\",\"gaid\":\"d7578036d13336cc\",\"brand\":\"google\"," 
    "\"model\":\"sdk_gphone64_x86_64\",\"system_language\":\"en\",\"net\":\"NETWORK_WIFI\"," 
    "\"region\":\"IN\",\"timezone\":\"Asia/Calcutta\",\"sp_code\":\"\"}"
)

SECRET_KEY_DEFAULT = base64.b64decode(
    "NzZpUmwwN3MweFNOOWpxbUVXQXQ3OUVCSlp1bElRSXNWNjRGWnIyTw=="
).decode("utf-8")
SECRET_KEY_ALT = base64.b64decode(
    "WHFuMm5uTzQxL0w5Mm8xaXVYaFNMSFRiWHZZNFo1Wlo2Mm04bVNMQQ=="
).decode("utf-8")

MAIN_PAGE = {
    "4516404531735022304": "Trending",
    "5692654647815587592": "Trending in Cinema",
    "414907768299210008": "Bollywood",
    "3859721901924910512": "South Indian",
    "8019599703232971616": "Hollywood",
    "4741626294545400336": "Top Series This Week",
    "8434602210994128512": "Anime",
    "1255898847918934600": "Reality TV",
    "4903182713986896328": "Indian Drama",
    "7878715743607948784": "Korean Drama",
    "8788126208987989488": "Chinese Drama",
    "3910636007619709856": "Western TV",
    "5177200225164885656": "Turkish Drama",
    "1|1": "Movies",
    "1|2": "Series",
    "1|1006": "Anime",
    "1|1;country=India": "Indian (Movies)",
    "1|2;country=India": "Indian (Series)",
    "1|1;classify=Hindi dub;country=United States": "USA (Movies)",
    "1|2;classify=Hindi dub;country=United States": "USA (Series)",
    "1|1;country=Japan": "Japan (Movies)",
    "1|2;country=Japan": "Japan (Series)",
    "1|1;country=China": "China (Movies)",
    "1|2;country=China": "China (Series)",
    "1|1;country=Philippines": "Philippines (Movies)",
    "1|2;country=Philippines": "Philippines (Series)",
    "1|1;country=Thailand": "Thailand(Movies)",
    "1|2;country=Thailand": "Thailand(Series)",
    "1|1;country=Nigeria": "Nollywood (Movies)",
    "1|2;country=Nigeria": "Nollywood (Series)",
    "1|1;country=Korea": "South Korean (Movies)",
    "1|2;country=Korea": "South Korean (Series)",
    "1|1;classify=Hindi dub;genre=Action": "Action (Movies)",
    "1|1;classify=Hindi dub;genre=Crime": "Crime (Movies)",
    "1|1;classify=Hindi dub;genre=Comedy": "Comedy (Movies)",
    "1|1;classify=Hindi dub;genre=Romance": "Romance (Movies)",
    "1|2;classify=Hindi dub;genre=Crime": "Crime (Series)",
    "1|2;classify=Hindi dub;genre=Comedy": "Comedy (Series)",
    "1|2;classify=Hindi dub;genre=Romance": "Romance (Series)",
}

QUALITIES = [
    ("2160", 2160),
    ("1440", 1440),
    ("1080", 1080),
    ("720", 720),
    ("480", 480),
    ("360", 360),
    ("240", 240),
]


@dataclass
class MovieBoxClient:
    session: requests.Session

    def md5(self, input_bytes: bytes) -> str:
        return hashlib.md5(input_bytes).hexdigest()

    def reverse_string(self, input_str: str) -> str:
        return input_str[::-1]

    def generate_x_client_token(self, hardcoded_timestamp: Optional[int] = None) -> str:
        timestamp = str(hardcoded_timestamp or int(time.time() * 1000))
        reversed_ts = self.reverse_string(timestamp)
        hash_value = self.md5(reversed_ts.encode("utf-8"))
        return f"{timestamp},{hash_value}"

    def build_canonical_string(
        self,
        method: str,
        accept: Optional[str],
        content_type: Optional[str],
        url: str,
        body: Optional[str],
        timestamp: int,
    ) -> str:
        parsed = urlparse(url)
        path = parsed.path or ""

        query = ""
        if parsed.query:
            params = parse_qs(parsed.query, keep_blank_values=True)
            pairs: List[str] = []
            for key in sorted(params.keys()):
                values = params.get(key, [])
                pairs.extend([f"{key}={value}" for value in values])
            query = "&".join(pairs)

        canonical_url = f"{path}?{query}" if query else path

        body_bytes = body.encode("utf-8") if body is not None else None
        if body_bytes is not None:
            trimmed = body_bytes[:102400]
            body_hash = self.md5(trimmed)
        else:
            body_hash = ""

        body_length = str(len(body_bytes)) if body_bytes is not None else ""
        return (
            f"{method.upper()}\n"
            f"{accept or ''}\n"
            f"{content_type or ''}\n"
            f"{body_length}\n"
            f"{timestamp}\n"
            f"{body_hash}\n"
            f"{canonical_url}"
        )

    def generate_x_tr_signature(
        self,
        method: str,
        accept: Optional[str],
        content_type: Optional[str],
        url: str,
        body: Optional[str] = None,
        use_alt_key: bool = False,
        hardcoded_timestamp: Optional[int] = None,
    ) -> str:
        timestamp = hardcoded_timestamp or int(time.time() * 1000)
        canonical = self.build_canonical_string(
            method, accept, content_type, url, body, timestamp
        )
        secret = SECRET_KEY_ALT if use_alt_key else SECRET_KEY_DEFAULT
        secret_bytes = base64.b64decode(secret)
        mac = hmac.new(secret_bytes, canonical.encode("utf-8"), hashlib.md5)
        signature_b64 = base64.b64encode(mac.digest()).decode("utf-8")
        return f"{timestamp}|2|{signature_b64}"

    def _base_headers(self, x_client_token: str, x_tr_signature: str) -> Dict[str, str]:
        return {
            "user-agent": USER_AGENT,
            "accept": "application/json",
            "content-type": "application/json",
            "connection": "keep-alive",
            "x-client-token": x_client_token,
            "x-tr-signature": x_tr_signature,
            "x-client-info": CLIENT_INFO,
            "x-client-status": "0",
        }

    def get_main_page(self, data: str, page: int = 1) -> Dict[str, Any]:
        per_page = 15
        if "|" in data:
            url = f"{MAIN_URL}/wefeed-mobile-bff/subject-api/list"
        else:
            url = (
                f"{MAIN_URL}/wefeed-mobile-bff/tab/ranking-list?tabId=0&"
                f"categoryType={data}&page={page}&perPage={per_page}"
            )

        main_parts = data.split(";", 1)[0].split("|")
        pg = int(main_parts[0]) if main_parts[0].isdigit() else 1
        channel_id = main_parts[1] if len(main_parts) > 1 else None

        options: Dict[str, str] = {}
        if ";" in data:
            for part in data.split(";", 1)[1].split(";"):
                if "=" in part:
                    key, value = part.split("=", 1)
                    if key and value:
                        options[key] = value

        classify = options.get("classify", "All")
        country = options.get("country", "All")
        year = options.get("year", "All")
        genre = options.get("genre", "All")
        sort = options.get("sort", "ForYou")

        json_body = (
            "{" +
            f"\"page\":{pg},\"perPage\":{per_page},\"channelId\":\"{channel_id}\","
            f"\"classify\":\"{classify}\",\"country\":\"{country}\","
            f"\"year\":\"{year}\",\"genre\":\"{genre}\",\"sort\":\"{sort}\"" +
            "}"
        )

        x_client_token = self.generate_x_client_token()
        if "|" in data:
            x_tr_signature = self.generate_x_tr_signature(
                "POST", "application/json", "application/json; charset=utf-8", url, json_body
            )
            headers = self._base_headers(x_client_token, x_tr_signature)
            response = self.session.post(url, headers=headers, data=json_body, timeout=30)
        else:
            x_tr_signature = self.generate_x_tr_signature(
                "GET", "application/json", "application/json", url
            )
            headers = self._base_headers(x_client_token, x_tr_signature)
            response = self.session.get(url, headers=headers, timeout=30)

        response.raise_for_status()
        root = response.json()
        items = (
            root.get("data", {}).get("items")
            or root.get("data", {}).get("subjects")
            or []
        )
        results = []
        for item in items:
            title = (item.get("title") or "").split("[")[0]
            subject_id = item.get("subjectId")
            if not title or not subject_id:
                continue
            cover = item.get("cover", {})
            subject_type = item.get("subjectType", 1)
            results.append(
                {
                    "title": title,
                    "subjectId": subject_id,
                    "poster": cover.get("url"),
                    "type": "tv" if subject_type == 2 else "movie",
                    "imdbRatingValue": item.get("imdbRatingValue"),
                }
            )
        return {"name": MAIN_PAGE.get(data, data), "items": results}

    def search(self, query: str) -> List[Dict[str, Any]]:
        url = f"{MAIN_URL}/wefeed-mobile-bff/subject-api/search/v2"
        json_body = json.dumps({"page": 1, "perPage": 10, "keyword": query})
        x_client_token = self.generate_x_client_token()
        x_tr_signature = self.generate_x_tr_signature(
            "POST", "application/json", "application/json; charset=utf-8", url, json_body
        )
        headers = self._base_headers(x_client_token, x_tr_signature)
        response = self.session.post(url, headers=headers, data=json_body, timeout=30)
        response.raise_for_status()
        root = response.json()
        results = root.get("data", {}).get("results", [])
        search_list: List[Dict[str, Any]] = []
        for result in results:
            for subject in result.get("subjects", []) or []:
                title = subject.get("title")
                subject_id = subject.get("subjectId")
                if not title or not subject_id:
                    continue
                cover = subject.get("cover", {})
                subject_type = subject.get("subjectType", 1)
                search_list.append(
                    {
                        "title": title,
                        "subjectId": subject_id,
                        "poster": cover.get("url"),
                        "type": "tv" if subject_type == 2 else "movie",
                        "imdbRatingValue": subject.get("imdbRatingValue"),
                    }
                )
        return search_list

    def load(self, url_or_id: str) -> Dict[str, Any]:
        subject_id = extract_subject_id(url_or_id)
        url = f"{MAIN_URL}/wefeed-mobile-bff/subject-api/get?subjectId={subject_id}"
        x_client_token = self.generate_x_client_token()
        x_tr_signature = self.generate_x_tr_signature(
            "GET", "application/json", "application/json", url
        )
        headers = self._base_headers(x_client_token, x_tr_signature)
        headers["x-play-mode"] = "2"
        response = self.session.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json().get("data")
        if not data:
            raise RuntimeError("No data returned")

        title = (data.get("title") or "").split("[")[0]
        description = data.get("description")
        release_date = data.get("releaseDate")
        duration = data.get("duration")
        genre = data.get("genre")
        imdb_rating = data.get("imdbRatingValue")
        year = int(release_date[:4]) if release_date and release_date[:4].isdigit() else None
        cover_url = data.get("cover", {}).get("url")
        background_url = data.get("cover", {}).get("url")
        subject_type = data.get("subjectType", 1)

        actors = []
        for staff in data.get("staffList", []) or []:
            if staff.get("staffType") == 1:
                actors.append(
                    {
                        "name": staff.get("name"),
                        "character": staff.get("character"),
                        "avatar": staff.get("avatarUrl"),
                    }
                )
        unique_actors = []
        seen = set()
        for actor in actors:
            if actor["name"] and actor["name"] not in seen:
                unique_actors.append(actor)
                seen.add(actor["name"])
        tags = [tag.strip() for tag in (genre or "").split(",") if tag.strip()]
        duration_minutes = parse_duration(duration)
        type_name = "tv" if subject_type == 2 else "movie"

        tmdb_id, imdb_id = identify_id(
            title=title.split("(")[0].split("[")[0],
            year=year,
            imdb_rating_value=float(imdb_rating) if imdb_rating else None,
            session=self.session,
        )
        logo_url = fetch_tmdb_logo_url(
            tmdb_api="https://api.themoviedb.org/3",
            api_key="98ae14df2b8d8f8f8136499daf79f0e0",
            type_name=type_name,
            tmdb_id=tmdb_id,
            app_lang_code="en",
            session=self.session,
        )
        meta = fetch_meta_data(imdb_id, type_name, self.session)
        meta_videos = meta.get("videos", []) if meta else []

        poster = meta.get("poster") if meta else None
        background = meta.get("background") if meta else None
        description_meta = meta.get("description") if meta else None
        imdb_rating_meta = meta.get("imdbRating") if meta else None

        payload: Dict[str, Any] = {
            "subjectId": subject_id,
            "title": title,
            "type": type_name,
            "poster": cover_url or poster,
            "background": background or background_url,
            "logo": logo_url,
            "plot": description_meta or description,
            "year": year,
            "tags": tags,
            "actors": unique_actors,
            "score": imdb_rating_meta or imdb_rating,
            "durationMinutes": duration_minutes,
            "imdbId": imdb_id,
            "tmdbId": tmdb_id,
        }

        if type_name == "tv":
            season_url = f"{MAIN_URL}/wefeed-mobile-bff/subject-api/season-info?subjectId={subject_id}"
            season_sig = self.generate_x_tr_signature(
                "GET", "application/json", "application/json", season_url
            )
            season_headers = dict(headers)
            season_headers["x-tr-signature"] = season_sig
            season_response = self.session.get(season_url, headers=season_headers, timeout=30)
            episodes = []
            if season_response.ok:
                seasons = season_response.json().get("data", {}).get("seasons")
                for season in seasons or []:
                    season_number = season.get("se", 1)
                    max_ep = season.get("maxEp", 1)
                    for episode_number in range(1, max_ep + 1):
                        ep_meta = next(
                            (
                                item
                                for item in meta_videos
                                if item.get("season") == season_number
                                and item.get("episode") == episode_number
                            ),
                            None,
                        )
                        ep_name = (
                            (ep_meta.get("name") if ep_meta else None) or f"S{season_number}E{episode_number}"
                        )
                        ep_desc = (
                            (ep_meta.get("overview") if ep_meta else None)
                            or (ep_meta.get("description") if ep_meta else None)
                            or f"Season {season_number} Episode {episode_number}"
                        )
                        ep_thumb = (
                            (ep_meta.get("thumbnail") if ep_meta else None) or cover_url
                        )
                        aired = (ep_meta.get("firstAired") if ep_meta else "") or ""
                        episodes.append(
                            {
                                "id": f"{subject_id}|{season_number}|{episode_number}",
                                "name": ep_name,
                                "season": season_number,
                                "episode": episode_number,
                                "poster": ep_thumb,
                                "description": ep_desc,
                                "aired": aired,
                            }
                        )
            if not episodes:
                episodes.append(
                    {
                        "id": f"{subject_id}|1|1",
                        "name": "Episode 1",
                        "season": 1,
                        "episode": 1,
                        "poster": cover_url or poster,
                    }
                )
            payload["episodes"] = episodes

        return payload

    def load_links(self, data: str) -> Dict[str, Any]:
        parts = data.split("|")
        original_subject_id = extract_subject_id(parts[0])
        season = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        episode = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0

        subject_url = f"{MAIN_URL}/wefeed-mobile-bff/subject-api/get?subjectId={original_subject_id}"
        subject_token = self.generate_x_client_token()
        subject_sig = self.generate_x_tr_signature(
            "GET", "application/json", "application/json", subject_url
        )
        subject_headers = self._base_headers(subject_token, subject_sig)
        subject_response = self.session.get(subject_url, headers=subject_headers, timeout=30)
        subject_ids: List[Tuple[str, str]] = []
        original_language_name = "Original"
        if subject_response.ok:
            subject_data = subject_response.json().get("data", {})
            dubs = subject_data.get("dubs")
            if isinstance(dubs, list):
                for dub in dubs:
                    dub_subject_id = dub.get("subjectId")
                    lan_name = dub.get("lanName")
                    if dub_subject_id and lan_name:
                        if dub_subject_id == original_subject_id:
                            original_language_name = lan_name
                        else:
                            subject_ids.append((dub_subject_id, lan_name))
        subject_ids.insert(0, (original_subject_id, original_language_name))

        streams: List[Dict[str, Any]] = []
        subtitles: List[Dict[str, Any]] = []
        for subject_id, language in subject_ids:
            url = (
                f"{MAIN_URL}/wefeed-mobile-bff/subject-api/play-info?"
                f"subjectId={subject_id}&se={season}&ep={episode}"
            )
            x_client_token = self.generate_x_client_token()
            x_tr_signature = self.generate_x_tr_signature(
                "GET", "application/json", "application/json", url
            )
            headers = self._base_headers(x_client_token, x_tr_signature)
            response = self.session.get(url, headers=headers, timeout=30)
            if not response.ok:
                continue
            play_data = response.json().get("data", {})
            stream_list = play_data.get("streams")
            if not isinstance(stream_list, list):
                continue
            for stream in stream_list:
                stream_url = stream.get("url")
                if not stream_url:
                    continue
                format_name = stream.get("format", "")
                resolutions = stream.get("resolutions", "")
                sign_cookie = stream.get("signCookie") or None
                stream_id = stream.get("id") or f"{subject_id}|{season}|{episode}"
                quality = get_highest_quality(resolutions)

                stream_entry = {
                    "source": f"MovieBox {language}",
                    "name": f"MovieBox ({language})",
                    "url": stream_url,
                    "type": infer_link_type(stream_url, format_name),
                    "headers": {"Referer": MAIN_URL},
                    "quality": quality,
                }
                if sign_cookie:
                    stream_entry["headers"]["Cookie"] = sign_cookie
                streams.append(stream_entry)

                sub_link = (
                    f"{MAIN_URL}/wefeed-mobile-bff/subject-api/get-stream-captions?"
                    f"subjectId={subject_id}&streamId={stream_id}"
                )
                self._collect_subtitles(sub_link, language, subtitles)

                sub_link_alt = (
                    f"{MAIN_URL}/wefeed-mobile-bff/subject-api/get-ext-captions?"
                    f"subjectId={subject_id}&resourceId={stream_id}&episode=0"
                )
                self._collect_subtitles(sub_link_alt, language, subtitles)

        return {"streams": streams, "subtitles": subtitles}

    def _collect_subtitles(
        self, url: str, language: str, subtitles: List[Dict[str, Any]]
    ) -> None:
        x_client_token = self.generate_x_client_token()
        x_tr_signature = self.generate_x_tr_signature("GET", "", "", url)
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "",
            "X-Client-Info": CLIENT_INFO,
            "X-Client-Status": "0",
            "Content-Type": "",
            "X-Client-Token": x_client_token,
            "x-tr-signature": x_tr_signature,
        }
        response = self.session.get(url, headers=headers, timeout=30)
        if not response.ok:
            return
        data = response.json().get("data", {})
        ext_captions = data.get("extCaptions")
        if not isinstance(ext_captions, list):
            return
        for caption in ext_captions:
            caption_url = caption.get("url")
            if not caption_url:
                continue
            lang = (
                caption.get("language")
                or caption.get("lanName")
                or caption.get("lan")
                or "Unknown"
            )
            subtitles.append({"url": caption_url, "lang": f"{lang} ({language})"})


def extract_subject_id(text: str) -> str:
    match = re.search(r"subjectId=([^&]+)", text)
    if match:
        return match.group(1)
    if "/" in text:
        return text.rsplit("/", 1)[-1]
    return text


def get_highest_quality(input_text: str) -> Optional[int]:
    for label, value in QUALITIES:
        if label.lower() in input_text.lower():
            return value
    return None


def infer_link_type(url: str, format_name: str) -> str:
    if url.lower().startswith("magnet:"):
        return "magnet"
    if ".mpd" in url.lower():
        return "dash"
    if url.lower().endswith(".torrent"):
        return "torrent"
    if format_name.lower() == "hls" or url.lower().endswith(".m3u8"):
        return "hls"
    if any(ext in url.lower() for ext in [".mp4", ".mkv"]):
        return "video"
    return "infer"


def parse_duration(duration: Optional[str]) -> Optional[int]:
    if not duration:
        return None
    match = re.search(r"(\d+)h\s*(\d+)m", duration)
    if match:
        hours = int(match.group(1)) if match.group(1).isdigit() else 0
        minutes = int(match.group(2)) if match.group(2).isdigit() else 0
        return hours * 60 + minutes
    stripped = duration.replace("m", "").strip()
    return int(stripped) if stripped.isdigit() else None


def normalize(text: str) -> str:
    text = re.sub(r"\[.*?]", " ", text)
    text = re.sub(r"\(.*?\)", " ", text)
    text = re.sub(r"(?i)\b(dub|dubbed|hd|4k|hindi|tamil|telugu|dual audio)\b", " ", text)
    text = text.strip().lower()
    text = text.replace(":", " ")
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def token_equals(a: str, b: str) -> bool:
    sa = {part for part in re.split(r"\s+", a) if part}
    sb = {part for part in re.split(r"\s+", b) if part}
    if not sa or not sb:
        return False
    inter = len(sa & sb)
    return inter >= max(1, min(len(sa), len(sb)) * 3 // 4)


def identify_id(
    title: str,
    year: Optional[int],
    imdb_rating_value: Optional[float],
    session: requests.Session,
) -> Tuple[Optional[int], Optional[str]]:
    norm_title = normalize(title)

    for _ in ["multi", "tv", "movie"]:
        res = search_and_pick(norm_title, year, imdb_rating_value, session)
        if res[0] is not None:
            return res

    if year is not None:
        for _ in ["multi", "tv", "movie"]:
            res = search_and_pick(norm_title, None, imdb_rating_value, session)
            if res[0] is not None:
                return res

    stripped = re.sub(
        r"\b(hindi|tamil|telugu|dub|dubbed|dubbed audio|dual audio|dubbed version)\b",
        " ",
        norm_title,
        flags=re.IGNORECASE,
    )
    stripped = re.sub(r"\s+", " ", stripped).strip()
    if stripped and stripped != norm_title:
        for _ in ["multi", "tv", "movie"]:
            res = search_and_pick(stripped, year, imdb_rating_value, session)
            if res[0] is not None:
                return res
        if year is not None:
            for _ in ["multi", "tv", "movie"]:
                res = search_and_pick(stripped, None, imdb_rating_value, session)
                if res[0] is not None:
                    return res

    return None, None


def search_and_pick(
    norm_title: str,
    year: Optional[int],
    imdb_rating_value: Optional[float],
    session: requests.Session,
) -> Tuple[Optional[int], Optional[str]]:
    def do_search(endpoint: str, extra_params: str = "") -> Optional[List[Dict[str, Any]]]:
        url = (
            f"https://api.themoviedb.org/3/{endpoint}?api_key=1865f43a0549ca50d341dd9ab8b29f49"
            f"{extra_params}&include_adult=false&page=1"
        )
        response = session.get(url, timeout=30)
        response.raise_for_status()
        return response.json().get("results")

    query = quote(norm_title)
    multi_results = do_search(
        "search/multi",
        f"&query={query}" + (f"&year={year}" if year else ""),
    )
    search_queues = [
        ("multi", multi_results),
        (
            "tv",
            do_search(
                "search/tv",
                f"&query={query}" + (f"&first_air_date_year={year}" if year else ""),
            ),
        ),
        (
            "movie",
            do_search(
                "search/movie",
                f"&query={query}" + (f"&year={year}" if year else ""),
            ),
        ),
    ]

    best_id: Optional[int] = None
    best_score = -1.0
    best_is_tv = False

    for source_type, results in search_queues:
        if not results:
            continue
        for item in results:
            media_type = (
                item.get("media_type") if source_type == "multi" else "tv" if source_type == "tv" else "movie"
            )
            candidate_id = item.get("id")
            if not candidate_id:
                continue
            if media_type == "tv":
                cand_title = next(
                    (t for t in [item.get("name"), item.get("original_name")] if t),
                    "",
                ).lower()
            elif media_type == "movie":
                cand_title = next(
                    (t for t in [item.get("title"), item.get("original_title")] if t),
                    "",
                ).lower()
            else:
                cand_title = next(
                    (
                        t
                        for t in [
                            item.get("title"),
                            item.get("name"),
                            item.get("original_title"),
                            item.get("original_name"),
                        ]
                        if t
                    ),
                    "",
                ).lower()

            cand_date = item.get("first_air_date") if media_type == "tv" else item.get("release_date")
            cand_year = int(cand_date[:4]) if cand_date and cand_date[:4].isdigit() else None
            cand_rating = item.get("vote_average")

            score = 0.0
            if token_equals(cand_title, norm_title):
                score += 50.0
            elif cand_title in norm_title or norm_title in cand_title:
                score += 15.0

            if cand_year is not None and year is not None and cand_year == year:
                score += 35.0

            if imdb_rating_value is not None and cand_rating is not None:
                diff = abs(cand_rating - imdb_rating_value)
                if diff <= 0.5:
                    score += 10.0
                elif diff <= 1.0:
                    score += 5.0

            if item.get("popularity"):
                score += min(item.get("popularity", 0.0) / 100.0, 5.0)

            if score > best_score:
                best_score = score
                best_id = candidate_id
                best_is_tv = media_type == "tv"

        if best_score >= 45:
            break

    if best_id is None or best_score < 40.0:
        return None, None

    detail_kind = "tv" if best_is_tv else "movie"
    detail_url = (
        f"https://api.themoviedb.org/3/{detail_kind}/{best_id}?api_key=1865f43a0549ca50d341dd9ab8b29f49"
        "&append_to_response=external_ids"
    )
    detail_response = session.get(detail_url, timeout=30)
    detail_response.raise_for_status()
    detail_json = detail_response.json()
    imdb_id = detail_json.get("external_ids", {}).get("imdb_id")

    return best_id, imdb_id


def fetch_meta_data(
    imdb_id: Optional[str], type_name: str, session: requests.Session
) -> Optional[Dict[str, Any]]:
    if not imdb_id:
        return None
    meta_type = "series" if type_name == "tv" else "movie"
    url = f"https://v3-cinemeta.strem.io/meta/{meta_type}/{imdb_id}.json"
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        return response.json().get("meta")
    except requests.RequestException:
        return None


def fetch_tmdb_logo_url(
    tmdb_api: str,
    api_key: str,
    type_name: str,
    tmdb_id: Optional[int],
    app_lang_code: Optional[str],
    session: requests.Session,
) -> Optional[str]:
    if tmdb_id is None:
        return None

    app_lang = app_lang_code.split("-")[0].lower() if app_lang_code else None
    if type_name == "movie":
        url = f"{tmdb_api}/movie/{tmdb_id}/images?api_key={api_key}"
    else:
        url = f"{tmdb_api}/tv/{tmdb_id}/images?api_key={api_key}"

    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException:
        return None

    logos = response.json().get("logos") or []
    if not logos:
        return None

    def logo_url_at(index: int) -> str:
        return f"https://image.tmdb.org/t/p/w500{logos[index].get('file_path')}"

    if app_lang:
        for idx, logo in enumerate(logos):
            if logo.get("iso_639_1") == app_lang:
                return logo_url_at(idx)

    for idx, logo in enumerate(logos):
        if logo.get("iso_639_1") == "en":
            return logo_url_at(idx)

    return logo_url_at(0)


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def print_json(data: Any) -> None:
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="MovieBox CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-categories", help="List available main page categories")

    main_page_parser = subparsers.add_parser("main-page", help="Fetch main page category")
    main_page_parser.add_argument("category", help="Category key (see list-categories)")
    main_page_parser.add_argument("--page", type=int, default=1)

    search_parser = subparsers.add_parser("search", help="Search for titles")
    search_parser.add_argument("query")

    load_parser = subparsers.add_parser("load", help="Load subject details")
    load_parser.add_argument("subject")

    links_parser = subparsers.add_parser("links", help="Load streaming links")
    links_parser.add_argument("data")

    args = parser.parse_args()

    if args.command == "list-categories":
        print_json(MAIN_PAGE)
        return

    client = MovieBoxClient(build_session())

    if args.command == "main-page":
        print_json(client.get_main_page(args.category, args.page))
    elif args.command == "search":
        print_json(client.search(args.query))
    elif args.command == "load":
        print_json(client.load(args.subject))
    elif args.command == "links":
        print_json(client.load_links(args.data))


if __name__ == "__main__":
    main()
