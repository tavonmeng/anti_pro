"""Offline IP-to-region lookups backed by the bundled ip2region database."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
from pathlib import Path

from app.config import settings


IP2REGION_PROVIDER = "ip2region"
_UNKNOWN_VALUES = {"", "0", "未知", "unknown"}


@dataclass(frozen=True)
class IpGeoResult:
    country: str | None
    province: str | None
    city: str | None
    status: str
    provider: str = IP2REGION_PROVIDER

    @property
    def has_region(self) -> bool:
        return bool(self.country or self.province or self.city)


class OfflineIpGeolocationService:
    """Resolve public IPv4 addresses locally without sending them to a provider."""

    def __init__(self, database_path: str | Path | None = None):
        configured_path = database_path or settings.IP_GEO_DATABASE_PATH
        self.database_path = Path(configured_path)
        self._vector_index = None

    def lookup(self, ip_address: str) -> IpGeoResult:
        normalized_ip = (ip_address or "").strip()
        try:
            parsed_ip = ipaddress.ip_address(normalized_ip)
        except ValueError:
            return IpGeoResult(None, None, None, "unavailable")

        if not parsed_ip.is_global:
            return IpGeoResult(None, None, None, "unavailable")
        if parsed_ip.version != 4:
            return IpGeoResult(None, None, None, "unavailable")
        if not self.database_path.is_file():
            raise RuntimeError(f"IP region database is unavailable: {self.database_path}")

        try:
            from ip2region import searcher, util

            raw_region = self._search(searcher, util, normalized_ip)
        except RuntimeError:
            raise
        except Exception as exc:  # pragma: no cover - binding errors are environment-specific
            raise RuntimeError(f"IP region lookup failed: {exc}") from exc

        parts = [self._normalize_part(part) for part in str(raw_region or "").split("|")]
        country, province, city = (parts + [None, None, None])[:3]
        if not any((country, province, city)):
            return IpGeoResult(None, None, None, "unavailable")
        return IpGeoResult(country, province, city, "done")

    def _search(self, searcher, util, ip_address: str) -> str:
        version = util.IPv4
        try:
            if self._vector_index is None:
                self._vector_index = util.load_vector_index_from_file(str(self.database_path))
            client = searcher.new_with_vector_index(
                version,
                str(self.database_path),
                self._vector_index,
            )
        except Exception as exc:
            raise RuntimeError(f"Unable to load IP region database: {exc}") from exc
        try:
            return str(client.search(ip_address) or "")
        finally:
            client.close()

    @staticmethod
    def _normalize_part(value: str | None) -> str | None:
        normalized = (value or "").strip()
        return None if normalized.lower() in _UNKNOWN_VALUES else normalized
