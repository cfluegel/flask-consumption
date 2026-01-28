# Flask Consumption

This project is a for tracking the consumption and production of the four main sources (electricity, natrual gas, water). Currently this is done in an analog way by write down each measurement on every month switch. The value of the meter will be read once per month, but the exact date or even the interval can be vary. I might reduce the interval time if the system proves to be easy. The date and the value of the meter shall be written to a database. Initially it can be a sqlite database file, but I would like to use a postgresql database later down the road.

The website does not need to have a user management at first. I want to run this website on my local network, that is secured and only used by trusted people.

## Front End

### Technology

- https://chartscss.org/ For visualisation of the monthly and yearly consumption
- Maybe something like HTMX

### Color Theming

I would like to have a dark and a light color theme. The main color for the light theme is this #FFE6A2. Add corresponding colors that match this base color.

The dark them should use this color als main color #1432b8 Add corresponding colors to for this main color.

## Backend

As I want you to use HTMX I would like you to implement a HTMX api and a separate API for calling it from my mobile phone

### Technology

- Flask
- Flask-SQLAlchemy
- API
