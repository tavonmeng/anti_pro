# Offline IP region data

`ip2region_v4.xdb` is the bundled IPv4 database used by the admin-only website
visit geolocation action. It is read locally; visitor IPs are never sent to a
third-party lookup service.

Source: https://github.com/lionsoul2014/ip2region

To update it, replace `ip2region_v4.xdb` with a compatible official database
file, then deploy. Existing cache rows are intentionally not re-resolved.
