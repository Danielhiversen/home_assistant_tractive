Integration for [Tractive](https://tractive.com/r/SI54Wd)

[Buy me a coffee :)](http://paypal.me/dahoiv)

{%- if selected_tag == "master" %}
## This is a development version!
This is **only** intended for test by developers!
{% endif %}

{%- if prerelease %}
## This is a beta version
Please be careful and do NOT install this on production systems. Also make sure to take a backup/snapshot before installing.
{% endif %}

## Configuration 

In configuration.yaml:

```
device_tracker:
  - platform: tractive
    username: "email@mail.com"
    password: "YourPassword"
```
