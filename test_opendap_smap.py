import earthaccess, requests, re

auth = earthaccess.login(strategy='netrc')
session = earthaccess.get_requests_https_session()

base = 'https://opendap.earthdata.nasa.gov/collections/C2938664763-NSIDC_CPRD/granules/SMAP_L3_SM_P_E_20241102_R19240_002.h5'

# Let's inspect the DMR
dmr_resp = session.get(f'{base}.dmr')
print('DMR status:', dmr_resp.status_code)
if dmr_resp.status_code == 200:
    dmr = dmr_resp.text
    # find Group names
    groups = re.findall(r'<Group name="([^"]+)"', dmr)
    print('Groups:', groups[:10])
    vars = re.findall(r'<[A-Za-z0-9_]+ name="([^"]+)"', dmr)
    sm_vars = [v for v in vars if 'soil_moisture' in v]
    print('Soil moisture vars:', sm_vars)

# Try DAP4 request for a variable or slice
# In DAP4: /collections/C.../granules/GRANULE.dap?dap4.ce=/Soil_Moisture_Retrieval_Data_AM/soil_moisture
# Or .nc4 with Hyrax:
for ext in ['.nc4', '.dap.nc4', '.nc', '.dap']:
    url = f'{base}{ext}'
    r = session.get(url, stream=True)
    print(f'{ext} status: {r.status_code}, type: {r.headers.get("content-type")}, length: {r.headers.get("content-length")}')
    r.close()
