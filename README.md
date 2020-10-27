# Tractive
![Validate with hassfest](https://github.com/Danielhiversen/home_assistant_tractive/workflows/Validate%20with%20hassfest/badge.svg)
[![GitHub Release][releases-shield]][releases]
[![hacs_badge][hacs-shield]][hacs]

Custom component for using [Tractive](https://tractive.com/r/SI54Wd) gps in Home Assistant.

[Support the developer](http://paypal.me/dahoiv)


## Install
Use [hacs](https://hacs.xyz/) or copy the files to the custom_components folder in Home Assistant config.

## Configuration 

In configuration.yaml:

```
device_tracker:
  - platform: tractive
    username: "email@mail.com"
    password: "YourPassword"
```


[releases]: https://github.com/Danielhiversen/home_assistant_tractive/releases
[releases-shield]: https://img.shields.io/github/release/Danielhiversen/home_assistant_tractive.svg?style=popout
[downloads-total-shield]: https://img.shields.io/github/downloads/Danielhiversen/home_assistant_tractive/total
[hacs-shield]: https://img.shields.io/badge/HACS-Default-orange.svg
[hacs]: https://hacs.xyz/docs/default_repositories
