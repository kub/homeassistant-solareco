### Installation
- create a new dir named `solareco` under `/config/custom_components` on your home assistant server
- copy `manifest.json`, `sensor.py` and `__init__.py` to `/config/custom_components/solareco`
- include following in `/config/configuration.yaml`:
```yaml
sensor:
  - platform: solareco
    host: 127.0.0.1 # solareco IP
    port: 5000      # solareco port
    poll_interval_seconds: 5 # how often should the integration query data form solareco
```
