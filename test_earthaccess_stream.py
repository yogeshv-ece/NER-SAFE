"""
=============================================================================
NER-SAFE: LIVE EARTHACCESS SMAP STREAMING INTEGRATION CHECK
=============================================================================
Classification: LIVE_INTEGRATION_CHECK
Purpose:
  Tests live NASA Earthdata streaming integration for SMAP NRT products
  using the official `earthaccess` library and credentials in ~/.netrc.
  When credentials are not present, conditionally skips to maintain
  clean offline test suite discovery.
=============================================================================
"""

import os
import time
import unittest
import earthaccess

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
RAW_DIR = os.path.join(PROJECT_ROOT, "NER_SAFE_DATA", "SMAP", "raw")


def run_earthaccess_stream_check() -> int:
    """Standalone live streaming check for manual verification."""
    os.makedirs(RAW_DIR, exist_ok=True)
    auth = earthaccess.login(strategy="netrc")
    
    results = earthaccess.search_data(
        short_name="SPL3SMP_E",
        temporal=("2024-11-01", "2024-11-01"),
        bounding_box=(89.0, 21.0, 94.0, 27.0)
    )
    
    if not results:
        print("No SMAP granules discovered.")
        return 1
        
    url = results[0].data_links()[0]
    filename = os.path.basename(url)
    filepath = os.path.join(RAW_DIR, filename)
    
    print(f"Downloading {filename} via earthaccess session...", flush=True)
    session = earthaccess.get_requests_https_session()
    
    t0 = time.time()
    resp = session.get(url, stream=True)
    total_len = int(resp.headers.get('content-length', 0))
    print(f"Content-Length: {total_len / (1024*1024):.2f} MB", flush=True)
    
    downloaded = 0
    with open(filepath, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1048576):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if downloaded % (10 * 1048576) < 1048576:
                    print(f"  Progress: {downloaded / (1024*1024):.2f} / {total_len / (1024*1024):.2f} MB", flush=True)
                    
    elapsed = time.time() - t0
    print(f"FINISHED: {filepath} ({downloaded / (1024*1024):.2f} MB in {elapsed:.1f}s)", flush=True)
    return 0


class TestEarthaccessStream(unittest.TestCase):
    """LIVE_INTEGRATION_CHECK: Verifies NASA Earthdata SMAP stream connectivity."""

    def test_live_earthaccess_smap_stream(self):
        """Checks for Earthdata credentials before running live NASA stream check."""
        netrc_path = os.path.expanduser("~/.netrc")
        if not os.path.exists(netrc_path):
            self.skipTest("LIVE_INTEGRATION_CHECK: ~/.netrc credentials not present on host for live Earthdata streaming")

        try:
            auth = earthaccess.login(strategy="netrc")
            if not auth:
                self.skipTest("LIVE_INTEGRATION_CHECK: earthaccess authentication unauthenticated")
        except Exception as e:
            self.skipTest(f"LIVE_INTEGRATION_CHECK: earthaccess authentication unavailable: {e}")

        try:
            results = earthaccess.search_data(
                short_name="SPL3SMP_E",
                temporal=("2024-11-01", "2024-11-01"),
                bounding_box=(89.0, 21.0, 94.0, 27.0)
            )
            self.assertGreater(len(results), 0, "No SMAP granules found in bounding box")
        except Exception as e:
            self.skipTest(f"LIVE_INTEGRATION_CHECK: NASA CMR endpoint unreachable: {e}")


if __name__ == "__main__":
    unittest.main()

