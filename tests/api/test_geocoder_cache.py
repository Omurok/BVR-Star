from bvr_star.api.app import geocoder, service


def test_chart_and_location_endpoints_share_geocoder_cache() -> None:
    assert service.geocoder is geocoder
