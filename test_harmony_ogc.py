import earthaccess, requests, json

auth = earthaccess.login(strategy='netrc')
session = earthaccess.get_requests_https_session()

concept_id = 'C2938664763-NSIDC_CPRD'
# Harmony WCS / Coverages URL
# Test 1: Using harmony-py or standard OGC API
# Endpoint: https://harmony.earthdata.nasa.gov/{concept_id}/ogc-api-coverages/1.0.0/collections/all/coverage/rangeset?subset=lat(21:27)&subset=lon(89:94)&granuleId=...
results = earthaccess.search_data(short_name='SPL3SMP_E', version='006', temporal=('2024-11-02', '2024-11-02'))
granule_concept_id = results[0]['meta']['concept-id']
print('Granule Concept ID:', granule_concept_id)

# Try OGC API Coverage
urls_to_test = [
    # 1. Harmony OGC API with bbox
    f"https://harmony.earthdata.nasa.gov/{concept_id}/ogc-api-coverages/1.0.0/collections/all/coverage/rangeset?granuleId={granule_concept_id}&subset=lat(21:27)&subset=lon(89:94)",
    # 2. With variable
    f"https://harmony.earthdata.nasa.gov/{concept_id}/ogc-api-coverages/1.0.0/collections/Soil_Moisture_Retrieval_Data_AM%2Fsoil_moisture/coverage/rangeset?granuleId={granule_concept_id}&subset=lat(21:27)&subset=lon(89:94)",
    # 3. Simple Harmony job submission
    f"https://harmony.earthdata.nasa.gov/jobs"
]

for url in urls_to_test[:2]:
    print('Testing:', url)
    try:
        r = session.get(url, timeout=15)
        print('Status:', r.status_code)
        print('Text:', r.text[:300])
    except Exception as e:
        print('Exception:', e)
