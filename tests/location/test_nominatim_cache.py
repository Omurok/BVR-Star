import json
from types import SimpleNamespace

from bvr_star.location.nominatim import NominatimGeocoder
from bvr_star.models.location import LocationCandidate


class FakeRedis:
    def __init__(self, value: str | None = None) -> None:
        self.value = value
        self.get_keys: list[str] = []
        self.set_calls: list[tuple[str, int, str]] = []

    def get(self, key: str) -> str | None:
        self.get_keys.append(key)
        return self.value

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.set_calls.append((key, ttl, value))


def _candidate() -> LocationCandidate:
    return LocationCandidate(
        display_name="Taipei, Taiwan",
        latitude=25.033,
        longitude=121.5654,
        rank=0.9,
        provider_id="123",
        address={"city": "Taipei"},
    )


def test_remote_cache_hit_skips_nominatim_request() -> None:
    candidate = _candidate()
    cache = FakeRedis(json.dumps([candidate.model_dump(mode="json")]))
    geocoder = NominatimGeocoder(cache_client=cache)

    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("Nominatim should not be called on a remote cache hit")

    geocoder._search = fail_if_called

    assert geocoder.search(" 台北 ") == [candidate]
    assert len(cache.get_keys) == 1
    assert cache.set_calls == []


def test_successful_result_is_written_to_remote_cache_with_ttl() -> None:
    candidate = _candidate()
    cache = FakeRedis()
    geocoder = NominatimGeocoder(cache_client=cache, cache_ttl_seconds=60)
    geocoder._search = lambda *args, **kwargs: [
        SimpleNamespace(
            address=candidate.display_name,
            latitude=candidate.latitude,
            longitude=candidate.longitude,
            raw={
                "importance": candidate.rank,
                "place_id": candidate.provider_id,
                "address": candidate.address,
            },
        )
    ]

    assert geocoder.search("台北") == [candidate]
    assert len(cache.set_calls) == 1
    _, ttl, payload = cache.set_calls[0]
    assert ttl == 60
    assert json.loads(payload) == [candidate.model_dump(mode="json")]
